"""
Canva API integration for portfolio slide generation.
Now with Gemini AI-powered design!
"""
import requests
import os
from typing import Dict, Optional, BinaryIO
from config import Config
import base64
import io


class CanvaIntegration:
    """Handle Canva API operations for slide generation."""
    
    def __init__(self):
        """Initialize Canva client."""
        self.api_key = Config.CANVA_API_KEY
        # Client ID is the same as API key (per Canva docs)
        # Use CANVA_CLIENT_ID if set, otherwise fall back to CANVA_API_KEY
        self.client_id = Config.CANVA_CLIENT_ID if hasattr(Config, 'CANVA_CLIENT_ID') and Config.CANVA_CLIENT_ID else Config.CANVA_API_KEY
        self.client_secret = Config.CANVA_CLIENT_SECRET if hasattr(Config, 'CANVA_CLIENT_SECRET') else None
        self.base_url = "https://api.canva.com/rest/v1"
        self.template_id = Config.CANVA_TEMPLATE_ID
        self.gemini_api_key = Config.GEMINI_API_KEY if hasattr(Config, 'GEMINI_API_KEY') else None
        self._access_token = None
        self._refresh_token = None
        self.token_file = "canva_tokens.json"
        self._load_tokens()
    
    def create_portfolio_slide(
        self,
        company_data: Dict,
        headshot_image: bytes,
        logo_image: bytes,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Create a portfolio slide using Canva template.
        
        Args:
            company_data: Dictionary with company information
            headshot_image: Processed headshot image bytes
            logo_image: Company logo image bytes
            output_path: Optional path to save the slide
            
        Returns:
            PDF bytes of the generated slide
        """
        # Check if we have either API key or OAuth credentials
        if not self.api_key and (not self.client_id or not self.client_secret):
            raise ValueError(
                "CANVA_API_KEY or both CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be configured. "
                "Use create_slide_alternative() for manual processing."
            )
        
        if not self.template_id:
            raise ValueError("CANVA_TEMPLATE_ID not configured")
        
        try:
            # Try to upload images to Canva, but if upload fails, we'll pass image bytes directly
            headshot_upload_id = None
            logo_upload_id = None
            map_upload_id = None
            
            try:
                headshot_upload_id = self._upload_image(headshot_image, "headshot")
            except Exception as e:
                print(f"   ⚠️  Image upload failed, will try passing image data directly: {e}")
                headshot_upload_id = None
            
            try:
                logo_upload_id = self._upload_image(logo_image, "logo")
            except Exception as e:
                print(f"   ⚠️  Image upload failed, will try passing image data directly: {e}")
                logo_upload_id = None
            
            # Upload map if provided in company_data
            if "map_image" in company_data:
                try:
                    map_upload_id = self._upload_image(company_data["map_image"], "map")
                except Exception as e:
                    print(f"   ⚠️  Map upload failed, will try passing image data directly: {e}")
                    map_upload_id = None
            
            # Create design from template
            design_id = self._duplicate_template()
            
            # Use Autofill to populate template
            # Pass image bytes if upload failed
            map_image_bytes = company_data.get("map_image") if "map_image" in company_data else None
            self._autofill_design(
                design_id, 
                company_data, 
                headshot_upload_id=headshot_upload_id,
                logo_upload_id=logo_upload_id,
                map_upload_id=map_upload_id,
                headshot_image_bytes=headshot_image if not headshot_upload_id else None,
                logo_image_bytes=logo_image if not logo_upload_id else None,
                map_image_bytes=map_image_bytes if not map_upload_id else None
            )
            
            # Export as PDF
            pdf_bytes = self._export_as_pdf(design_id)
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
            
            return pdf_bytes
        except Exception as e:
            error_str = str(e).lower()
            # If it's an authentication error, provide helpful message
            if any(keyword in error_str for keyword in ["401", "403", "invalid_access_token", "invalid token", "unauthorized", "access_denied"]):
                print(f"❌ Canva API authentication failed: {e}")
                print("   💡 Run: python setup_canva_oauth.py to refresh OAuth tokens")
            
            # Always raise - no fallback to Gemini
            raise Exception(f"Canva API failed: {e}. Cannot use Gemini fallback - Canva template is required.")
    
    def _upload_image(self, image_bytes: bytes, image_type: str) -> str:
        """
        Upload image to Canva and get upload ID.
        
        Args:
            image_bytes: Image bytes to upload
            image_type: Type of image (headshot, logo, map)
            
        Returns:
            Upload ID from Canva
        """
        print(f"   Uploading {image_type} to Canva...")
        
        # Try different upload endpoints
        # Note: Canva API might use different endpoints for OAuth vs API key
        # Based on Canva API docs, try these endpoints in order:
        upload_endpoints = [
            f"{self.base_url}/assets/upload",  # Try assets/upload endpoint (for OAuth)
            f"{self.base_url}/assets",  # Try assets endpoint (for OAuth)
            f"https://api.canva.com/rest/v1/assets/upload",  # REST API assets/upload endpoint
            f"https://api.canva.com/rest/v1/assets",  # REST API assets endpoint
            f"{self.base_url}/uploads",  # Original uploads endpoint
            f"https://api.canva.com/rest/v1/uploads",  # REST API uploads endpoint
        ]
        
        # Try base64 JSON format first
        import base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        for endpoint in upload_endpoints:
            try:
                # Try JSON format with base64
                payload = {
                    "image": {
                        "data": image_base64,
                        "mime_type": "image/png"  # Default to PNG, adjust if needed
                    }
                }
                
                response = self._make_authenticated_request(
                    "post",
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in [200, 201]:
                    try:
                        result = response.json()
                        upload_id = result.get("id") or result.get("upload_id") or result.get("uploadId") or result.get("upload_id")
                        if upload_id:
                            print(f"   ✓ Uploaded {image_type} to Canva: {upload_id}")
                            return upload_id
                    except Exception as e:
                        print(f"   Failed to parse upload response: {e}")
                        print(f"   Response: {response.text[:200]}")
                
                # Try multipart/form-data if JSON fails (400 or other non-success)
                if response.status_code not in [200, 201]:
                    files = {'file': (f"{image_type}.png", image_bytes, 'image/png')}
                    response = self._make_authenticated_request(
                        "post",
                        endpoint,
                        files=files
                    )
                    
                    if response.status_code in [200, 201]:
                        try:
                            result = response.json()
                            upload_id = result.get("id") or result.get("upload_id") or result.get("uploadId") or result.get("upload_id")
                            if upload_id:
                                print(f"   ✓ Uploaded {image_type} to Canva: {upload_id}")
                                return upload_id
                        except Exception as e:
                            print(f"   Failed to parse multipart upload response: {e}")
                            print(f"   Response: {response.text[:200]}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"   Upload failed with {endpoint}: {error_msg}")
                # If it's an auth error, don't try other endpoints
                if "401" in error_msg or "403" in error_msg or "authentication" in error_msg.lower():
                    raise
                continue
        
        # If all endpoints failed, raise error (no fallback)
        raise Exception(f"Failed to upload {image_type} to Canva from all endpoints. Cannot proceed without Canva template.")

    def upload_pdf_asset(self, pdf_bytes: bytes, filename: str = "slide.pdf") -> str:
        """
        Upload a PDF to Canva using the Design Import API.
        This imports the PDF as a design in Canva.
        
        Returns:
            Design/import ID from Canva
        """
        print(f"   Uploading PDF to Canva via Design Import API ({filename})...")
        
        import base64
        import json
        
        # Canva Design Import API endpoint
        import_endpoint = f"{self.base_url}/imports"
        
        # Prepare metadata - title should be base64 encoded
        title = filename.replace('.pdf', '').replace('_', ' ')
        title_base64 = base64.b64encode(title.encode('utf-8')).decode('utf-8')
        
        import_metadata = {
            "title_base64": title_base64,
            "mime_type": "application/pdf"
        }
        
        try:
            # Use Design Import API - send PDF as binary with metadata header
            response = self._make_authenticated_request(
                "post",
                import_endpoint,
                data=pdf_bytes,  # Send PDF as binary data
                headers={
                    "Content-Type": "application/octet-stream",
                    "Import-Metadata": json.dumps(import_metadata)
                }
            )
            
            if response.status_code in [200, 201, 202]:
                try:
                    result = response.json()
                    # The response should contain an import_id or design_id
                    import_id = result.get("import_id") or result.get("id") or result.get("design_id")
                    if import_id:
                        print(f"   ✓ PDF imported to Canva (import_id: {import_id})")
                        return import_id
                    else:
                        print(f"   Response keys: {list(result.keys())}")
                        print(f"   Full response: {result}")
                        # If it's async, might need to poll for status
                        if "job_id" in result or "status" in result:
                            print(f"   Import job created, status: {result.get('status', 'unknown')}")
                            return result.get("job_id") or result.get("id")
                except Exception as e:
                    print(f"   Failed to parse import response: {e}")
                    print(f"   Response: {response.text[:500]}")
            else:
                print(f"   Import failed ({response.status_code}): {response.text[:500]}")
        
        except Exception as e:
            error_msg = str(e)
            print(f"   PDF import failed with exception: {error_msg}")
            # Log response details if available
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"   Response details: {e.response.text[:500]}")
            response = None  # Set to None so fallback runs
        
        # Fallback: Try old endpoints if import API doesn't work
        if not response or response.status_code not in [200, 201, 202]:
            if response:
                print(f"   ⚠️  Design Import API returned {response.status_code}, trying legacy endpoints...")
            else:
                print(f"   ⚠️  Design Import API failed, trying legacy asset upload endpoints...")
        upload_endpoints = [
            f"{self.base_url}/assets/upload",
            f"{self.base_url}/assets",
        ]

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        for endpoint in upload_endpoints:
            try:
                # Try JSON base64 first
                payload = {
                    "file": {
                        "data": pdf_base64,
                        "mime_type": "application/pdf",
                        "filename": filename,
                    }
                }
                response = self._make_authenticated_request(
                    "post",
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                print(f"   JSON upload attempt - Status: {response.status_code}")
                if response.status_code in [200, 201]:
                    try:
                        result = response.json()
                        print(f"   Response keys: {list(result.keys())}")
                        upload_id = result.get("id") or result.get("upload_id") or result.get("uploadId") or result.get("asset_id")
                        if upload_id:
                            print(f"   ✓ Uploaded PDF asset to Canva: {upload_id}")
                            return upload_id
                    except Exception as e:
                        print(f"   Failed to parse PDF upload response: {e}")
                        print(f"   Response: {response.text[:500]}")

                # If JSON fails, try multipart/form-data
                if response.status_code not in [200, 201]:
                    print(f"   JSON upload failed ({response.status_code}), trying multipart...")
                    print(f"   Error response: {response.text[:500]}")
                    files = {"file": (filename, pdf_bytes, "application/pdf")}
                    response = self._make_authenticated_request("post", endpoint, files=files)
                    print(f"   Multipart upload attempt - Status: {response.status_code}")
                    if response.status_code in [200, 201]:
                        try:
                            result = response.json()
                            print(f"   Response keys: {list(result.keys())}")
                            upload_id = result.get("id") or result.get("upload_id") or result.get("uploadId") or result.get("asset_id")
                            if upload_id:
                                print(f"   ✓ Uploaded PDF asset to Canva: {upload_id}")
                                return upload_id
                        except Exception as e:
                            print(f"   Failed to parse multipart PDF upload response: {e}")
                            print(f"   Response: {response.text[:500]}")
                    else:
                        print(f"   Multipart upload failed ({response.status_code}): {response.text[:500]}")

            except Exception as e:
                error_msg = str(e)
                print(f"   PDF upload failed with {endpoint}: {error_msg}")
                # Log response details if available
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    print(f"   Response details: {e.response.text[:500]}")
                elif hasattr(e, 'args') and len(e.args) > 0:
                    error_detail = str(e.args[0])
                    if 'response' in error_detail.lower() or 'status' in error_detail.lower():
                        print(f"   Error detail: {error_detail[:500]}")
                if "401" in error_msg or "403" in error_msg or "authentication" in error_msg.lower():
                    raise
                continue

        # If all endpoints failed, try converting PDF to image and uploading as image
        print(f"   ⚠️  All PDF upload endpoints failed. Trying to convert PDF to image and upload...")
        try:
            from pdf2image import convert_from_bytes
            from PIL import Image
            import io
            
            # Convert first page of PDF to image
            images = convert_from_bytes(pdf_bytes, dpi=300, first_page=1, last_page=1)
            if images:
                img = images[0]
                # Convert to PNG bytes
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                img_data = img_bytes.read()
                
                # Upload as image instead
                print(f"   Converting PDF to image and uploading as PNG...")
                image_upload_id = self._upload_image(img_data, "slide_image")
                print(f"   ✓ Uploaded PDF (as image) to Canva: {image_upload_id}")
                return image_upload_id
        except Exception as e:
            print(f"   PDF to image conversion failed: {e}")
        
        # If everything failed
        raise Exception(f"Failed to upload PDF asset to Canva from all endpoints. Last attempt: PDF to image conversion also failed.")
    
    def _load_tokens(self):
        """Load stored OAuth tokens from file."""
        if os.path.exists(self.token_file):
            try:
                import json
                with open(self.token_file, 'r') as f:
                    tokens = json.load(f)
                    self._access_token = tokens.get("access_token")
                    self._refresh_token = tokens.get("refresh_token")
                    if self._access_token:
                        print("✓ Loaded stored Canva OAuth tokens")
            except Exception as e:
                print(f"Warning: Could not load tokens from {self.token_file}: {e}")
    
    def _save_tokens(self, tokens: dict):
        """Save OAuth tokens to file."""
        try:
            import json
            with open(self.token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            self._access_token = tokens.get("access_token")
            self._refresh_token = tokens.get("refresh_token")
        except Exception as e:
            print(f"Warning: Could not save tokens: {e}")
    
    def _refresh_access_token(self) -> str:
        """Refresh access token using refresh token."""
        if not self._refresh_token:
            raise ValueError(
                "No refresh token available. Please run setup_canva_oauth.py to set up OAuth."
            )
        
        if not self.client_id or not self.client_secret:
            raise ValueError("CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be configured.")
        
        print(f"   Attempting to refresh access token...")
        print(f"   Client ID: {self.client_id[:10]}...")
        print(f"   Refresh token exists: {bool(self._refresh_token)}")
        
        # Try different token endpoints (same as in setup script)
        token_endpoints = [
            "https://api.canva.com/rest/v1/oauth/token",  # REST API endpoint (this one worked!)
            "https://www.canva.com/api/oauth/token",      # Alternative endpoint
            "https://api.canva.com/v1/oauth2/token",       # Original (doesn't work)
        ]
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
        }
        
        last_error = None
        for token_url in token_endpoints:
            try:
                print(f"   Trying refresh endpoint: {token_url}")
                # REST API endpoint expects JSON, others use form-urlencoded
                if "rest/v1" in token_url:
                    # REST API endpoint - use JSON
                    response = requests.post(
                        token_url, 
                        json=data, 
                        headers={"Content-Type": "application/json"}
                    )
                else:
                    # Other endpoints - use form-urlencoded
                    response = requests.post(token_url, data=data)
                
                if response.status_code == 200:
                    tokens = response.json()
                    
                    if "access_token" not in tokens:
                        print(f"   ⚠️  No access_token in response: {list(tokens.keys())}")
                        last_error = f"No access_token in response"
                        continue
                    
                    # Save updated tokens
                    self._save_tokens(tokens)
                    print(f"   ✓ Successfully refreshed access token!")
                    return tokens["access_token"]
                elif response.status_code == 401:
                    # Refresh token is invalid/expired
                    error_text = response.text[:200]
                    print(f"   ❌ Refresh token is invalid/expired (401): {error_text}")
                    raise ValueError(
                        f"Refresh token is invalid or expired. Please run: python setup_canva_oauth.py to re-authenticate."
                    )
                elif response.status_code == 429:
                    # Rate limited - wait a bit and return error
                    error_text = response.text[:200]
                    print(f"   ⚠️  Rate limited (429). Please wait before retrying.")
                    last_error = f"429: Rate limited"
                    # Don't try other endpoints if rate limited
                    break
                else:
                    error_text = response.text[:200]
                    print(f"   Refresh failed ({response.status_code}): {error_text}")
                    last_error = f"{response.status_code}: {error_text}"
                    continue
                    
            except ValueError:
                # Re-raise ValueError (refresh token invalid)
                raise
            except Exception as e:
                print(f"   Error with {token_url}: {e}")
                last_error = str(e)
                continue
        
        # If all endpoints failed
        raise ValueError(
            f"Failed to refresh access token from any endpoint. Last error: {last_error}. "
            f"Please run setup_canva_oauth.py to re-authenticate."
        )
    
    def _get_access_token(self) -> str:
        """
        Get OAuth access token using client credentials flow or stored tokens.
        
        Priority:
        1. Client credentials flow (if client_id and client_secret are available)
        2. Stored OAuth access token (if available and not expired)
        3. API key (if no OAuth setup)
        
        Returns:
            Access token string
        """
        # Try client credentials flow first (simplest, no user interaction needed)
        if self.client_id and self.client_secret:
            # Check if we have a cached token that's still valid
            if self._access_token:
                # For now, try using cached token, will refresh if it fails
                return self._access_token
            
            # Get new token using client credentials flow
            try:
                print("   Getting access token using client credentials flow...")
                # REST API endpoint expects JSON payload
                response = requests.post(
                    "https://api.canva.com/rest/v1/oauth/token",
                    json={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "design:read design:write asset:read asset:write"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    if access_token:
                        # Cache the token
                        self._access_token = access_token
                        self._save_tokens()
                        print("   ✓ Access token obtained via client credentials")
                        return access_token
                    else:
                        print(f"   ⚠️  No access_token in response: {response.json()}")
                else:
                    print(f"   ⚠️  Client credentials flow failed ({response.status_code}): {response.text[:200]}")
            except Exception as e:
                print(f"   ⚠️  Client credentials flow error: {e}")
        
        # Fallback: Use stored OAuth token if available
        if self._access_token:
            return self._access_token
        
        # Fallback: Use API key directly (if client_id is actually the API key)
        if self.api_key:
            return self.api_key
        
        # If client_id is set but no token, try client credentials one more time
        if self.client_id and self.client_secret:
            raise ValueError(
                "Failed to obtain access token using client credentials flow. "
                "Please check your CANVA_CLIENT_ID and CANVA_CLIENT_SECRET in .env"
            )
        
        raise ValueError(
            "Either CANVA_API_KEY or both CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be configured.\n"
            "Note: CANVA_CLIENT_ID should be your Canva API key."
        )
    
    def _make_authenticated_request(self, method: str, url: str, **kwargs):
        """
        Make an authenticated request with automatic token refresh.
        
        Args:
            method: HTTP method (get, post, put, etc.)
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
        """
        access_token = self._get_access_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        kwargs["headers"] = headers
        
        # Make request
        response = requests.request(method, url, **kwargs)
        
        # If 401 or 403, try refreshing token and retry once
        if response.status_code in [401, 403]:
            # Try client credentials flow first (simplest, no refresh token needed)
            if self.client_id and self.client_secret:
                print(f"⚠️  Access token expired ({response.status_code}), getting new token via client credentials...")
                try:
                    # Clear cached token and get a new one
                    self._access_token = None
                    access_token = self._get_access_token()
                    print(f"   ✓ New token obtained, retrying request...")
                    headers["Authorization"] = f"Bearer {access_token}"
                    kwargs["headers"] = headers
                    response = requests.request(method, url, **kwargs)
                    
                    # If still failing, check if it's HTML (wrong endpoint) or JSON (auth issue)
                    if response.status_code in [401, 403]:
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type or response.text.strip().startswith('<!DOCTYPE'):
                            raise Exception(
                                f"Endpoint returned HTML error page ({response.status_code}). "
                                f"This may indicate the endpoint URL is incorrect or the token doesn't have the required scopes. "
                                f"Endpoint: {url}. Please check Canva API documentation."
                            )
                        else:
                            raise Exception(
                                f"Authentication failed after token refresh ({response.status_code}): {response.text[:200]}. "
                                f"Please check your CANVA_CLIENT_ID and CANVA_CLIENT_SECRET in .env"
                            )
                    else:
                        print(f"   ✓ Request succeeded after token refresh!")
                except Exception as e:
                    error_str = str(e)
                    if "client credentials" in error_str.lower() or "token" in error_str.lower():
                        raise Exception(
                            f"Failed to get new token: {e}. "
                            f"Please check your CANVA_CLIENT_ID and CANVA_CLIENT_SECRET in .env"
                        )
                    raise
            # Fallback: Try OAuth refresh token flow (if refresh token exists)
            elif self._refresh_token and self.client_id and self.client_secret:
                print(f"⚠️  Access token expired ({response.status_code}), attempting OAuth refresh...")
                try:
                    access_token = self._refresh_access_token()
                    print(f"   ✓ Token refreshed, retrying request...")
                    headers["Authorization"] = f"Bearer {access_token}"
                    kwargs["headers"] = headers
                    response = requests.request(method, url, **kwargs)
                    
                    if response.status_code in [401, 403]:
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type or response.text.strip().startswith('<!DOCTYPE'):
                            raise Exception(
                                f"Endpoint returned HTML error page ({response.status_code}). "
                                f"This may indicate the endpoint URL is incorrect or the OAuth token doesn't have the required scopes. "
                                f"Endpoint: {url}. Please check Canva API documentation or run: python setup_canva_oauth.py to re-authenticate with correct scopes."
                            )
                        else:
                            raise Exception(
                                f"Authentication failed after token refresh ({response.status_code}): {response.text[:200]}. "
                                f"Refresh token may be expired or missing required scopes. Please run: python setup_canva_oauth.py to re-authenticate."
                            )
                    else:
                        print(f"   ✓ Request succeeded after token refresh!")
                except ValueError as e:
                    raise Exception(
                        f"Token refresh failed: {e}. "
                        f"Please run: python setup_canva_oauth.py to re-authenticate."
                    )
                except Exception as e:
                    error_str = str(e)
                    if "refresh" in error_str.lower() or "token" in error_str.lower():
                        raise Exception(
                            f"Token refresh error: {e}. "
                            f"Please run: python setup_canva_oauth.py to re-authenticate."
                        )
                    raise
            else:
                # No refresh token available or missing OAuth credentials
                if not self._refresh_token:
                    if self.client_id and self.client_secret:
                        raise Exception(
                            f"Canva API authentication failed ({response.status_code}): {response.text[:200]}. "
                            f"No refresh token available. Please run: python setup_canva_oauth.py to set up OAuth."
                        )
                    else:
                        # Using API key - can't refresh
                        raise Exception(
                            f"Canva API authentication failed ({response.status_code}): {response.text[:200]}. "
                            f"Using API key - token refresh not available. "
                            f"Please check your CANVA_API_KEY or set up OAuth (run: python setup_canva_oauth.py)"
                        )
                elif not self.client_id or not self.client_secret:
                    raise Exception(
                        f"Canva API authentication failed ({response.status_code}): {response.text[:200]}. "
                        f"Refresh token exists but CANVA_CLIENT_ID or CANVA_CLIENT_SECRET missing. "
                        f"Please configure them in .env or run: python setup_canva_oauth.py"
                    )
                else:
                    # Should not reach here, but just in case
                    raise Exception(
                        f"Canva API authentication failed ({response.status_code}): {response.text[:200]}. "
                        f"Token refresh not available. Please run: python setup_canva_oauth.py to re-authenticate."
                    )
        
        return response
    
    def _duplicate_template(self) -> str:
        """
        Duplicate the template design.
        
        Returns:
            Design ID of duplicated template
        """
        # Try different duplication endpoints and methods
        # Note: www.canva.com endpoints return HTML error pages, so we avoid them
        duplicate_endpoints = [
            # Try duplicate endpoint first (most common) - design ID in URL path
            (f"{self.base_url}/designs/{self.template_id}/duplicate", "post", {}),
            # Try copy endpoint
            (f"{self.base_url}/designs/{self.template_id}/copy", "post", {}),
            # Try creating new design from existing design (template_id is a design, not asset)
            # The 'type' field is required according to the error message
            (f"{self.base_url}/designs", "post", {"source_design_id": self.template_id, "type": "DESIGN"}),
            (f"{self.base_url}/designs", "post", {"source_design_id": self.template_id, "type": "STANDARD"}),
            # Try without type (might work if source_design_id is enough)
            (f"{self.base_url}/designs", "post", {"source_design_id": self.template_id}),
        ]
        
        last_error = None
        for endpoint, method, payload in duplicate_endpoints:
            try:
                response = self._make_authenticated_request(
                    method,
                    endpoint,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    try:
                        design_data = response.json()
                        design_id = design_data.get("id") or design_data.get("design_id") or design_data.get("designId") or design_data.get("data", {}).get("id")
                        if design_id:
                            print(f"✓ Duplicated template: {design_id}")
                            return design_id
                    except Exception as e:
                        print(f"   Failed to parse duplicate response: {e}")
                        print(f"   Response: {response.text[:200]}")
                
                # Check if response is HTML (wrong endpoint)
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type or response.text.strip().startswith('<!DOCTYPE'):
                    print(f"   Endpoint returned HTML (wrong endpoint): {endpoint}")
                    last_error = f"Endpoint {endpoint} returned HTML error page"
                    continue
                
                if response.status_code != 404:
                    print(f"   Duplicate failed ({response.status_code}): {response.text[:200]}")
                    last_error = f"{response.status_code}: {response.text[:200]}"
                    
            except Exception as e:
                error_msg = str(e)
                print(f"   Duplicate error with {endpoint}: {error_msg}")
                # Don't continue if it's an auth error - that's a real problem
                if "401" in error_msg or "403" in error_msg or "authentication" in error_msg.lower():
                    last_error = error_msg
                    break
                last_error = error_msg
                continue
        
        # If all endpoints failed
        raise Exception(f"Template duplication failed from all endpoints. Last error: {last_error}")
    
    def _get_design_elements(self, design_id: str) -> list:
        """
        Get all elements from a Canva design.
        
        Args:
            design_id: Canva design ID
            
        Returns:
            List of design elements
        """
        try:
            response = self._make_authenticated_request(
                "get",
                f"{self.base_url}/designs/{design_id}/elements"
            )
            response.raise_for_status()
            return response.json().get("elements", [])
        except Exception as e:
            print(f"Warning: Could not get design elements: {e}")
            return []
    
    def _identify_images_with_gemini(self, design_id: str) -> Dict[str, str]:
        """
        Use Gemini Vision to identify image placeholders by position.
        Gets a preview of the design and uses Gemini to identify placeholder positions.
        
        Args:
            design_id: Canva design ID
            
        Returns:
            Dictionary mapping positions to element IDs: {"top_right": "element_id", ...}
        """
        if not self.gemini_api_key:
            return {}
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            
            # Try to get design preview
            try:
                preview_response = self._make_authenticated_request(
                    "get",
                    f"{self.base_url}/designs/{design_id}/preview",
                    params={"format": "png", "width": 1920, "height": 1080}
                )
                if preview_response.status_code == 200:
                    preview_image = preview_response.content
                    
                    # Use Gemini to identify placeholder positions
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    prompt = """Look at this Canva design template. Identify the image placeholders and their positions:
                    
1. Find the image placeholder in the TOP RIGHT corner - return its position as "top_right"
2. Find the image placeholder in the MIDDLE RIGHT area (above center, below top) - return as "middle_right"  
3. Find the image placeholder in the BOTTOM RIGHT corner - return as "bottom_right"

Return a JSON object with the positions and approximate coordinates, like:
{
  "top_right": {"x": 1600, "y": 100},
  "middle_right": {"x": 1500, "y": 400},
  "bottom_right": {"x": 1400, "y": 800}
}

If a placeholder doesn't exist, omit it from the response."""
                    
                    response = model.generate_content([prompt, preview_image])
                    # Parse response to get positions
                    # For now, return empty dict and use coordinate-based approach
                    return {}
            except Exception as e:
                print(f"Warning: Could not get design preview for Gemini: {e}")
                return {}
        except ImportError:
            return {}
        except Exception as e:
            print(f"Warning: Gemini image identification failed: {e}")
            return {}
    
    def _replace_image_by_position(
        self,
        design_id: str,
        image_upload_id: str,
        position: str
    ) -> bool:
        """
        Replace an image element by its position in the design.
        
        Args:
            design_id: Canva design ID
            image_upload_id: Upload ID of the image to use
            position: Position identifier ("top_right", "middle_right", "bottom_right")
            
        Returns:
            True if successful
        """
        # Get all elements
        elements = self._get_design_elements(design_id)
        
        # Filter for image elements
        image_elements = [e for e in elements if e.get("type") == "image" or "image" in e.get("type", "").lower()]
        
        if not image_elements:
            print(f"Warning: No image elements found in design")
            return False
        
        # Calculate positions (assuming 1920x1080 design)
        design_width = 1920
        design_height = 1080
        
        # Define position zones (more lenient zones)
        right_zone_x = design_width * 0.5  # Right 50% of design (more lenient)
        top_zone_y = design_height * 0.4   # Top 40%
        middle_zone_y_start = design_height * 0.4
        middle_zone_y_end = design_height * 0.7  # Middle 30%
        bottom_zone_y = design_height * 0.6  # Bottom 40%
        
        # Find element by position
        target_element = None
        for element in image_elements:
            # Get element position (varies by Canva API structure)
            bounds = element.get("bounds") or element.get("position") or {}
            # Try different possible position formats
            x = bounds.get("x") or bounds.get("left") or element.get("x") or element.get("left") or 0
            y = bounds.get("y") or bounds.get("top") or element.get("y") or element.get("top") or 0
            
            # Check if element is in right zone
            if x >= right_zone_x:
                if position == "top_right" and y <= top_zone_y:
                    target_element = element
                    break
                elif position == "middle_right" and middle_zone_y_start < y <= middle_zone_y_end:
                    target_element = element
                    break
                elif position == "bottom_right" and y > bottom_zone_y:
                    target_element = element
                    break
        
        if not target_element:
            print(f"Warning: Could not find image element at {position}")
            print(f"Available image elements at positions: {[(e.get('x', 0), e.get('y', 0)) for e in image_elements]}")
            return False
        
        # Replace the image
        element_id = target_element.get("id") or target_element.get("element_id") or target_element.get("elementId")
        if not element_id:
            print(f"Warning: Element has no ID")
            return False
        
        try:
            # Try different API endpoints for replacing images
            endpoints_to_try = [
                (f"{self.base_url}/designs/{design_id}/elements/{element_id}", "PUT", {"image_id": image_upload_id, "type": "image"}),
                (f"{self.base_url}/designs/{design_id}/elements/{element_id}", "PATCH", {"image": image_upload_id}),
                (f"{self.base_url}/designs/{design_id}/elements/{element_id}/image", "PUT", {"upload_id": image_upload_id}),
            ]
            
            for endpoint, method, payload in endpoints_to_try:
                try:
                    response = self._make_authenticated_request(
                        method.lower(),
                        endpoint,
                        json=payload
                    )
                    
                    if response.status_code in [200, 201, 204]:
                        print(f"✓ Successfully replaced image at {position}")
                        return True
                except Exception as e:
                    continue
            
            print(f"Warning: All replace methods failed for {position}")
            return False
        except Exception as e:
            print(f"Warning: Could not replace image at {position}: {e}")
            return False
    
    def _autofill_design(self, design_id: str, company_data: Dict, headshot_upload_id: str = None, logo_upload_id: str = None, map_upload_id: Optional[str] = None, headshot_image_bytes: bytes = None, logo_image_bytes: bytes = None, map_image_bytes: bytes = None) -> str:
        """
        Use Canva Autofill API to populate template with company data.
        Falls back to position-based replacement if Autofill fails.
        
        Args:
            design_id: Canva design ID
            company_data: Company information dictionary
            headshot_upload_id: Upload ID for headshot image
            logo_upload_id: Upload ID for logo image
            map_upload_id: Optional upload ID for map image
            
        Returns:
            Updated design ID
        """
        # Prepare autofill data based on template structure
        # Adjust field names to match your Canva template placeholders
        # Support both investment_stage (combined) and separate investment_round/quarter/year
        
        # Build investment_stage if not provided (combine round, quarter, year)
        investment_stage = company_data.get("investment_stage")
        if not investment_stage:
            # Build from separate fields
            round_val = company_data.get("investment_round", "PRE-SEED")
            quarter_val = company_data.get("quarter", "Q2")
            year_val = company_data.get("year", "2024")
            investment_stage = f"{round_val} • {quarter_val} {year_val}"
        
        # Prepare autofill data
        autofill_data = {
            "data": {
                "company_name": company_data.get("name", ""),
                "description": company_data.get("description", ""),
                "location": company_data.get("address", company_data.get("location", "")),
                "investment_date": company_data.get("investment_date", ""),
                "investment_stage": investment_stage,  # Combined format: "PRE-SEED • Q2 2024"
                # Also include separate fields if template uses them
                "investment_round": company_data.get("investment_round", ""),
                "quarter": company_data.get("quarter", ""),
                "year": company_data.get("year", ""),
                "founders": ", ".join(company_data.get("founders", [])) if isinstance(company_data.get("founders"), list) else company_data.get("founders", ""),
                "co_investors": ", ".join(company_data.get("co_investors", [])) if isinstance(company_data.get("co_investors"), list) else company_data.get("co_investors", ""),
                "background": company_data.get("background", company_data.get("description", "")),
            },
            "images": {}
        }
        
        # Try to use upload IDs if available, otherwise try base64 data
        import base64
        if headshot_upload_id:
            autofill_data["images"]["headshot"] = headshot_upload_id
        elif headshot_image_bytes:
            # Try passing base64 data directly
            headshot_base64 = base64.b64encode(headshot_image_bytes).decode('utf-8')
            autofill_data["images"]["headshot"] = {
                "data": headshot_base64,
                "mime_type": "image/png"
            }
        
        if logo_upload_id:
            autofill_data["images"]["logo"] = logo_upload_id
        elif logo_image_bytes:
            # Try passing base64 data directly
            logo_base64 = base64.b64encode(logo_image_bytes).decode('utf-8')
            autofill_data["images"]["logo"] = {
                "data": logo_base64,
                "mime_type": "image/png"
            }
        
        if map_upload_id:
            autofill_data["images"]["map"] = map_upload_id
        elif map_image_bytes:
            # Try passing base64 data directly
            map_base64 = base64.b64encode(map_image_bytes).decode('utf-8')
            autofill_data["images"]["map"] = {
                "data": map_base64,
                "mime_type": "image/png"
            }
        
        try:
            # Try Autofill first (if you have named placeholders)
            print(f"   Attempting Autofill for design {design_id}...")
            response = self._make_authenticated_request(
                "post",
                f"{self.base_url}/designs/{design_id}/autofill",
                json=autofill_data
            )
            
            if response.status_code in [200, 201, 204]:
                print(f"   ✓ Autofill successful!")
                return design_id
            else:
                error_text = response.text[:300]
                print(f"   Autofill returned {response.status_code}: {error_text}")
                raise Exception(f"Autofill failed with status {response.status_code}: {error_text}")
                
        except Exception as e:
            error_str = str(e).lower()
            # If it's an auth error, don't try fallback - just raise
            if "401" in error_str or "403" in error_str or "authentication" in error_str:
                raise Exception(f"Autofill authentication failed: {e}. Cannot proceed without Canva template.")
            
            print(f"   Autofill failed (may not have named placeholders): {e}")
            print("   Trying position-based image replacement...")
            
            # Fallback: Use position-based replacement for images
            # Replace images by position
            logo_success = self._replace_image_by_position(design_id, logo_upload_id, "top_right")
            
            map_success = False
            if map_upload_id:
                map_success = self._replace_image_by_position(design_id, map_upload_id, "middle_right")
            
            headshot_success = self._replace_image_by_position(design_id, headshot_upload_id, "bottom_right")
            
            # If position-based replacement also fails, raise error
            if not (logo_success and headshot_success):
                raise Exception(
                    f"Failed to replace images by position. Logo: {logo_success}, Headshot: {headshot_success}. "
                    f"Cannot proceed without Canva template. Original autofill error: {e}"
                )
            
            # For text, we still need Autofill or manual replacement
            # Try text replacement via API
            try:
                # Update text elements if possible
                self._update_text_elements(design_id, company_data)
            except Exception as e2:
                print(f"   Warning: Text update failed: {e2}")
                # Don't raise - images are more critical
            
            return design_id
    
    def _update_text_elements(self, design_id: str, company_data: Dict):
        """
        Update text elements in the design with company data.
        This is a fallback if Autofill doesn't work.
        """
        # This would need to find text elements and update them
        # Implementation depends on Canva API structure
        # For now, we'll rely on Autofill for text
        pass
    
    def _export_as_pdf(self, design_id: str) -> bytes:
        """
        Export design as PDF.
        
        Args:
            design_id: Canva design ID
            
        Returns:
            PDF bytes
        """
        # Request PDF export
        export_data = {
            "format": "pdf",
            "quality": "high"
        }
        
        try:
            # Start export job
            print(f"   Requesting PDF export for design {design_id}...")
            response = self._make_authenticated_request(
                "post",
                f"{self.base_url}/designs/{design_id}/exports",
                json=export_data
            )
            
            if response.status_code not in [200, 201, 202]:
                error_text = response.text[:300]
                raise Exception(f"Export request failed ({response.status_code}): {error_text}")
            
            export_job = response.json()
            export_id = export_job.get("id") or export_job.get("export_id") or export_job.get("exportId")
            
            if not export_id:
                raise Exception(f"Export job created but no export ID returned. Response: {export_job}")
            
            print(f"   ✓ Export job created: {export_id}")
            
            # Poll for export completion
            import time
            max_attempts = 60  # Increased timeout to 2 minutes
            print(f"   Polling for export completion (max {max_attempts * 2} seconds)...")
            
            for attempt in range(max_attempts):
                time.sleep(2)  # Wait 2 seconds between polls
                status_response = self._make_authenticated_request(
                    "get",
                    f"{self.base_url}/exports/{export_id}"
                )
                
                if status_response.status_code not in [200, 201]:
                    error_text = status_response.text[:300]
                    raise Exception(f"Failed to check export status ({status_response.status_code}): {error_text}")
                
                status_data = status_response.json()
                status = status_data.get("status") or status_data.get("state")
                
                if status == "completed" or status == "done":
                    # Download PDF
                    pdf_url = status_data.get("url") or status_data.get("download_url") or status_data.get("downloadUrl")
                    if pdf_url:
                        print(f"   ✓ Export completed! Downloading PDF...")
                        pdf_response = requests.get(pdf_url)
                        if pdf_response.status_code == 200:
                            print(f"   ✓ PDF downloaded ({len(pdf_response.content)} bytes)")
                            return pdf_response.content
                        else:
                            raise Exception(f"Failed to download PDF ({pdf_response.status_code}): {pdf_response.text[:200]}")
                    else:
                        raise Exception(f"Export completed but no download URL provided. Status data: {status_data}")
                elif status == "failed" or status == "error":
                    error_msg = status_data.get("error") or status_data.get("message") or "Unknown error"
                    raise Exception(f"Export failed: {error_msg}")
                elif status in ["processing", "pending", "in_progress"]:
                    if attempt % 10 == 0:  # Print every 20 seconds
                        print(f"   Export still processing... (attempt {attempt + 1}/{max_attempts})")
                    continue
                else:
                    # Unknown status
                    print(f"   Warning: Unknown export status: {status}")
                    if attempt >= max_attempts - 1:
                        raise Exception(f"Export timed out with status: {status}")
            
            raise Exception(f"Export timed out after {max_attempts * 2} seconds")
            
        except Exception as e:
            print(f"Warning: Canva PDF export failed: {e}")
            raise
    
    def create_slide_alternative(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        template_path: Optional[str] = None,
        map_path: Optional[str] = None
    ) -> bytes:
        """
        Create slide using Canva API with the template.
        NO FALLBACK - Only uses Canva template.
        
        Args:
            company_data: Company information
            headshot_path: Path to processed headshot
            logo_path: Path to logo
            template_path: Path to template image/PDF (unused - only Canva template)
            map_path: Path to map image (optional)
            
        Returns:
            PDF bytes of generated slide
        """
        # Check for Canva API credentials (API key OR OAuth)
        has_canva_auth = (self.api_key or (self.client_id and self.client_secret)) and self.template_id
        if not has_canva_auth:
            raise ValueError(
                "Canva API credentials required. Set CANVA_API_KEY or CANVA_CLIENT_ID/CANVA_CLIENT_SECRET, "
                "and CANVA_TEMPLATE_ID. No Gemini fallback available."
            )
        
        print("🎨 Using Canva template (no fallback)...")
        
        # Read images as bytes for Canva
        with open(headshot_path, 'rb') as f:
            headshot_bytes = f.read()
        with open(logo_path, 'rb') as f:
            logo_bytes = f.read()
        
        # Add map if provided
        if map_path and os.path.exists(map_path):
            with open(map_path, 'rb') as f:
                map_bytes = f.read()
            company_data["map_image"] = map_bytes
        
        # Use Canva API to create slide - no fallback
        return self.create_portfolio_slide(
            company_data,
            headshot_bytes,
            logo_bytes
        )
    
    def _create_slide_with_gemini(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        template_slide_path: Optional[str] = None,
        map_path: Optional[str] = None
    ) -> bytes:
        """
        Create slide using Gemini Vision to analyze template and generate new slide.
        
        Args:
            company_data: Company information
            headshot_path: Path to processed headshot
            logo_path: Path to logo
            template_slide_path: Optional path to template slide image (the design to match)
            map_path: Optional path to map image
            
        Returns:
            PDF bytes of generated slide
        """
        try:
            import google.generativeai as genai
            from PIL import Image as PILImage
            import io
            import base64
            
            # Configure Gemini
            genai.configure(api_key=self.gemini_api_key)
            
            # Use Gemini's best model - prioritize best performance (nano banana = best/fastest)
            import time
            models_to_try = [
                'gemini-2.0-flash-exp',  # Best model - Tier 1+ (nano banana equivalent - fastest + best)
                'gemini-1.5-pro',        # Excellent performance
                'gemini-1.5-flash',      # Fast and capable
                'gemini-pro',            # Fallback
            ]
            
            model = None
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    print(f"✓ Using Gemini model: {model_name}")
                    break
                except Exception as e:
                    error_str = str(e)
                    # If it's a quota error, try next model
                    if "429" in error_str or "quota" in error_str.lower():
                        print(f"Model {model_name} quota exceeded, trying next model...")
                        continue
                    # If model doesn't exist, try next
                    print(f"Model {model_name} not available, trying next...")
                    continue
            
            if not model:
                raise Exception("No Gemini model available. Check your API key and quota.")
            
            # Load images
            headshot_img = PILImage.open(headshot_path)
            logo_img = PILImage.open(logo_path)
            
            # Prepare company data for prompt
            company_name = company_data.get('name', 'Company Name')
            description = company_data.get('description', '')
            location = company_data.get('address', company_data.get('location', ''))
            investment_date = company_data.get('investment_date', '')
            
            # Build investment stage
            investment_stage = company_data.get('investment_stage', '')
            if not investment_stage:
                round_val = company_data.get('investment_round', 'PRE-SEED')
                quarter_val = company_data.get('quarter', 'Q2')
                year_val = company_data.get('year', '2024')
                investment_stage = f"{round_val} {quarter_val}, {year_val}"
            
            # Format founders
            founders = company_data.get('founders', '')
            if isinstance(founders, list):
                founders = '\n'.join(founders)
            elif isinstance(founders, str) and ',' in founders:
                founders = '\n'.join([f.strip() for f in founders.split(',')])
            
            # Format co-investors
            co_investors = company_data.get('co_investors', '')
            if isinstance(co_investors, list):
                co_investors = '\n'.join(co_investors)
            elif isinstance(co_investors, str) and ',' in co_investors:
                co_investors = '\n'.join([c.strip() for c in co_investors.split(',')])
            
            background = company_data.get('background', company_data.get('description', ''))
            
            # Create comprehensive prompt for Gemini
            prompt = f"""Create a professional portfolio company slide that matches the exact design and layout of the template slide I'm showing you.

REPLACE THE TEXT CONTENT with this company information:

COMPANY NAME: {company_name}

INVESTMENT STAGE (top of orange sidebar): {investment_stage}

FOUNDERS (below yellow "Founders" box):
{founders}

CO-INVESTORS (below yellow "Co-Investors" box):
{co_investors}

BACKGROUND (below yellow "Background" box):
{background}

LOCATION: {location}

INVESTMENT DATE: {investment_date}

REQUIREMENTS:
1. Keep the EXACT same design, layout, colors, and styling as the template
2. Dark grey background (#2a2a2a)
3. Orange vertical sidebar on the left (200px wide)
4. Investment stage text at TOP of sidebar (white, horizontal)
5. "SLAUSON&CO." text at BOTTOM of sidebar (white, rotated 90 degrees clockwise)
6. Large bold orange company name at top left (after sidebar)
7. Logo in top right corner (use the logo image provided)
8. Yellow highlight boxes for "Founders", "Co-Investors", and "Background" labels (black text in boxes)
9. White text below each yellow box for the actual content
10. Map image in upper right area (if map provided)
11. Headshot images in bottom right (use the headshot image provided, grayscale, background removed, overlapping if multiple)

Generate a 1920x1080 pixel slide image that exactly matches the template design but with the new company information."""

            # Prepare images for Gemini
            images_for_gemini = []
            
            # Add headshot
            headshot_bytes = io.BytesIO()
            headshot_img.save(headshot_bytes, format='PNG')
            headshot_bytes.seek(0)
            images_for_gemini.append(headshot_img)
            
            # Add logo
            logo_bytes = io.BytesIO()
            logo_img.save(logo_bytes, format='PNG')
            logo_bytes.seek(0)
            images_for_gemini.append(logo_img)
            
            # Add map if provided
            if map_path:
                try:
                    map_img = PILImage.open(map_path)
                    images_for_gemini.append(map_img)
                except:
                    pass
            
            # Add template slide if provided (for reference)
            if template_slide_path and os.path.exists(template_slide_path):
                try:
                    template_img = PILImage.open(template_slide_path)
                    images_for_gemini.insert(0, template_img)  # Put template first
                except:
                    pass
            
            print("Using Gemini Vision to generate slide from template...")
            
            # Call Gemini with images and prompt - with retry logic for quota errors
            max_retries = 3
            retry_delay = 2  # Start with 2 seconds
            
            for attempt in range(max_retries):
                try:
                    if images_for_gemini:
                        response = model.generate_content([prompt] + images_for_gemini)
                    else:
                        response = model.generate_content(prompt)
                    
                    # Success - break out of retry loop
                    break
                    
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a quota/rate limit error
                    if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            # Extract retry delay from error if available
                            if "retry in" in error_str.lower():
                                try:
                                    import re
                                    delay_match = re.search(r'retry in ([\d.]+)s', error_str.lower())
                                    if delay_match:
                                        retry_delay = float(delay_match.group(1)) + 1
                                except:
                                    pass
                            
                            print(f"Quota/rate limit hit. Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            # Last attempt failed - raise the error
                            raise Exception(
                                f"Gemini API quota exceeded after {max_retries} attempts. "
                                f"Please check your quota at: https://ai.dev/usage?tab=rate-limit\n"
                                f"Or upgrade your plan at: https://ai.google.dev/pricing\n"
                                f"Error: {error_str}"
                            )
                    else:
                        # Not a quota error - raise immediately
                        raise
            
            # Check if we have a template image - if so, use it as base and overlay content
            if template_slide_path and os.path.exists(template_slide_path):
                print("Using template image as base and overlaying new content...")
                return self._create_slide_from_template(
                    template_slide_path,
                    company_data,
                    headshot_path,
                    logo_path,
                    map_path=map_path
                )
            
            # If no template, use Gemini's analysis to guide PIL rendering
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            print("Gemini analyzed the template. Using Gemini's understanding to render slide with PIL...")
            print(f"Gemini response preview: {response_text[:200]}...")
            
            # Use Gemini's analysis to render the slide
            # Gemini provided the design understanding, now render it exactly
            return self._create_slide_standard(company_data, headshot_path, logo_path, map_path=map_path)
            
        except ImportError:
            raise ImportError(
                "google-generativeai package is required. Install it with: pip install google-generativeai"
            )
        except Exception as e:
            import traceback
            error_msg = f"Gemini Vision slide generation failed: {e}\n{traceback.format_exc()}"
            print(error_msg)
            raise Exception(f"Failed to generate slide with Gemini: {e}")
    
    def _create_slide_from_template(
        self,
        template_path: str,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        map_path: Optional[str] = None
    ) -> bytes:
        """
        Create slide using Gemini 2.5 Flash Image model to replace template content.
        Uses gemini-2.5-flash-image to generate an exact replica of the template with new content.
        """
        try:
            # Use the older google.generativeai instead of google.genai to avoid Python 3.14 recursion issues
            import google.generativeai as genai
            from PIL import Image as PILImage
            import io
            import time
            import os
            import tempfile
            
            # Configure Gemini with older API (more stable)
            genai.configure(api_key=self.gemini_api_key)
            
            # Use gemini-2.0-flash-exp or fallback to 1.5-pro
            models_to_try = ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']
            model = None
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    print(f"✓ Using Gemini model: {model_name}")
                    break
                except:
                    continue
            
            if not model:
                raise ValueError("No Gemini model available")
            
            # Load template and images
            template_img = PILImage.open(template_path)
            if template_img.size != (1920, 1080):
                template_img = template_img.resize((1920, 1080), PILImage.Resampling.LANCZOS)
            
            headshot_img = PILImage.open(headshot_path)
            logo_img = PILImage.open(logo_path)
            
            # Prepare company data
            company_name = company_data.get('name', 'Company Name')
            investment_stage = company_data.get('investment_stage', '')
            if not investment_stage:
                round_val = company_data.get('investment_round', 'PRE-SEED')
                quarter_val = company_data.get('quarter', 'Q2')
                year_val = company_data.get('year', '2024')
                investment_stage = f"{round_val} {quarter_val}, {year_val}"
            
            founders = company_data.get('founders', '')
            if isinstance(founders, list):
                founders = '\n'.join(founders)
            elif isinstance(founders, str) and ',' in founders:
                founders = '\n'.join([f.strip() for f in founders.split(',')])
            
            co_investors = company_data.get('co_investors', '')
            if isinstance(co_investors, list):
                co_investors = '\n'.join(co_investors)
            elif isinstance(co_investors, str) and ',' in co_investors:
                co_investors = '\n'.join([c.strip() for c in co_investors.split(',')])
            
            background = company_data.get('background', company_data.get('description', ''))
            location = company_data.get('address', company_data.get('location', ''))
            
            # Create prompt for Gemini 2.5 Flash Image
            prompt = f"""You are an expert at editing presentation slides. I'm showing you a template slide and I need you to create a NEW slide that is an EXACT structural replica, but with updated content.

TEMPLATE STRUCTURE TO MAINTAIN:
- Dark grey background (#2a2a2a) with subtle city map overlay
- Orange vertical sidebar on the left (200px wide)
- Investment stage text at TOP of orange sidebar (white, horizontal), the same direction as the "SLAUSON&CO." text, just on the top left. 
- "SLAUSON&CO." text at BOTTOM of sidebar (white, rotated 90 degrees clockwise)
- Large bold orange company name at top left (after sidebar)
- Logo in top right corner. Make sure to first erase the existing image. Make the logo circular on the top right corner where the original logo was.
- Map in upper right area with yellow pin and location label. With the new location label, make sure to first erase the existing text and make a new map with the pin pointing at the general location in the US. Similar to the template. For example, if the location is "San Francisco, CA", the map should point to the general location on the USA map similar to the template please (same image and mark).
- Yellow highlight boxes for "Founders", "Co-Investors", and "Background" labels (black text in boxes)
- White text below each yellow box for the actual content
- For the two, big, grey people in the bottom right, make sure to erase their faces and replace them with the new headshots. Make sure to first erase the existing images. Grayscale headshots in bottom right (circular, background removed, overlapping). Make sure the background is transparent.

REPLACE WITH THIS COMPANY DATA:

COMPANY NAME: {company_name}
(Use large, bold, orange condensed font at top left after sidebar. Make sure to first erase the existing text.)

INVESTMENT STAGE: {investment_stage}
(White text at top of orange sidebar, horizontal. Make sure to first erase the existing text.)

FOUNDERS:
{founders}
(White text below yellow "Founders" box, one name per line. Make sure to first erase the existing text.)

CO-INVESTORS:
{co_investors}
(White text below yellow "Co-Investors" box, one name per line. Make sure to first erase the existing text.)

BACKGROUND:
{background}
(White body text below yellow "Background" box, wrapped to 2-3 sentences. Make sure to first erase the existing text and update the text to the new background.)

LOCATION: {location}
(Update the yellow pin label on the map to show this location. Make sure to first erase the existing text. Make sure to first erase the existing text.)

IMAGES TO USE:
- Use the logo image provided (top right corner)
- Use the headshot image provided (bottom right, convert to grayscale, make circular, background removed)
- Use the map image provided (upper right area, with yellow pin showing the location)

CRITICAL REQUIREMENTS (AGAIN MAKE SURE THAT IT FOLLOWS THE SAME STYLE AND FORMAT AS THE TEMPLATE):
1. DO NOT draw any blocks or rectangles - only replace text and images intelligently
2. Maintain EXACT same design, layout, colors, and styling as template
3. Keep all yellow boxes exactly as they are
4. Only replace the text content, not the design elements
5. Preserve the dark grey background and orange sidebar exactly
6. Make headshots grayscale, circular, and overlapping in bottom right
7. Update map location label to show: {location}
8. Fix any of the grammatical errors in the text please and fix it accordingly. For example, for the background text, make sure to fix the grammatical errors and update the text to the new background to make it sound like english.
9. For the map, make sure you update the location label to show the new location. 
10. For the investment stage text, make sure you update the text to the new investment stage. For example, if the investment stage is "SEED Q2, 2015", the text should be "SEED • Q2 2015". Double check the grammatical errors and fix it accordingly.

Generate a 1920x1080 pixel slide image that is an exact replica of the template structure with the new company information."""
            
            # Prepare contents list: prompt + images
            contents = [prompt, template_img, headshot_img, logo_img]
            
            # Add map if provided
            if map_path and os.path.exists(map_path):
                try:
                    map_img = PILImage.open(map_path)
                    contents.append(map_img)
                except Exception as e:
                    print(f"Warning: Could not load map image: {e}")
            
            print("Using Gemini to replace template content...")
            
            # Convert PIL images to bytes for older API
            def pil_to_bytes(img):
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                return buf.getvalue()
            
            # Prepare images for older API
            template_bytes = pil_to_bytes(template_img)
            headshot_bytes = pil_to_bytes(headshot_img)
            logo_bytes = pil_to_bytes(logo_img)
            
            # Call Gemini with retry logic (using older API)
            max_retries = 3
            retry_delay = 2
            response = None
            
            for attempt in range(max_retries):
                try:
                    # Use older API format
                    response = model.generate_content(
                        [prompt, 
                         {"mime_type": "image/png", "data": template_bytes},
                         {"mime_type": "image/png", "data": headshot_bytes},
                         {"mime_type": "image/png", "data": logo_bytes}]
                    )
                    break
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            if "retry in" in error_str.lower():
                                try:
                                    import re
                                    delay_match = re.search(r'retry in ([\d.]+)s', error_str.lower())
                                    if delay_match:
                                        retry_delay = float(delay_match.group(1)) + 1
                                except:
                                    pass
                            print(f"Quota/rate limit hit. Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            raise Exception(
                                f"Gemini API quota exceeded after {max_retries} attempts. "
                                f"Please check your quota at: https://ai.dev/usage?tab=rate-limit"
                            )
                    else:
                        raise
            
            if not response:
                raise Exception("Failed to get response from Gemini")
            
            # Extract generated image from response
            slide_img = None
            
            # Process response parts (older API format)
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    # Check for text (might be description)
                    if hasattr(part, 'text') and part.text:
                        print(f"Gemini response text: {part.text[:200]}...")
                    
                    # Check for inline image data
                    if hasattr(part, 'inline_data') and part.inline_data:
                        try:
                            image_bytes = part.inline_data.data
                            slide_img = PILImage.open(io.BytesIO(image_bytes))
                            print("✓ Gemini generated slide image")
                            break
                        except Exception as e:
                            print(f"Warning: Could not extract image from response: {e}")
                            continue
            
            # If no image was generated, fall back to template overlay method
            if not slide_img:
                print("Warning: Gemini didn't return image, using template overlay method...")
                raise Exception("Gemini didn't return image")
            
            if slide_img:
                # Convert generated image to PDF
                slide_rgb = slide_img.convert('RGB')
                if slide_rgb.size != (1920, 1080):
                    slide_rgb = slide_rgb.resize((1920, 1080), PILImage.Resampling.LANCZOS)
                
                pdf_bytes = io.BytesIO()
                slide_rgb.save(pdf_bytes, format='PDF', resolution=100.0)
                pdf_bytes.seek(0)
                
                print("✓ Slide created by Gemini 2.5 Flash Image - exact template replica with new content")
                return pdf_bytes.read()
            else:
                # Fallback: Use precise template overlay method
                print("⚠ Gemini 2.5 Flash Image did not return image, using precise template overlay method...")
                return self._create_slide_with_template_overlay(
                    template_path, company_data, headshot_path, logo_path, map_path
                )
            
        except ImportError as e:
            if "google.genai" in str(e) or "google import genai" in str(e):
                raise ImportError(
                    "google-genai package is required for gemini-2.5-flash-image. "
                    "Install it with: pip install google-genai"
                )
            else:
                raise ImportError(
                    f"Required package not found: {e}. "
                    "Install dependencies with: pip install google-genai Pillow"
                )
        except RecursionError as e:
            print(f"⚠️  Recursion error (Python 3.14 compatibility issue): {e}")
            print("   Falling back to template overlay method...")
            # Fall back to template overlay method
            return self._create_slide_with_template_overlay(
                template_path,
                company_data,
                headshot_path,
                logo_path,
                map_path=map_path
            )
        except Exception as e:
            error_str = str(e).lower()
            if "recursion" in error_str or "maximum recursion" in error_str:
                print(f"⚠️  Recursion error (Python 3.14 compatibility issue): {e}")
                print("   Falling back to template overlay method...")
                # Fall back to template overlay method
                return self._create_slide_with_template_overlay(
                    template_path,
                    company_data,
                    headshot_path,
                    logo_path,
                    map_path=map_path
                )
            import traceback
            print(f"Error creating slide with Gemini: {e}\n{traceback.format_exc()}")
            # Fallback to template overlay method
            return self._create_slide_with_template_overlay(
                template_path, company_data, headshot_path, logo_path, map_path
            )
            
            # Use Gemini's best model to get text regions and erase intelligently
            try:
                # Use the model we already selected (best available)
                analysis_response = model.generate_content([erase_prompt, template])
                analysis_text = analysis_response.text
                print(f"✓ Gemini identified text regions for erasure")
            except Exception as e:
                print(f"Warning: Gemini analysis failed: {e}, using intelligent sampling")
                analysis_text = None
            
            # Prepare images for Gemini
            images_for_gemini = [template]
            
            # Add headshot (will be processed by Gemini)
            images_for_gemini.append(headshot_img)
            
            # Add logo
            images_for_gemini.append(logo_img)
            
            # Add map if provided
            if map_path and os.path.exists(map_path):
                try:
                    map_img = PILImage.open(map_path).convert('RGBA')
                    images_for_gemini.append(map_img)
                except:
                    pass
            
            print("Using Gemini's best model to replace template content...")
            
            # Call Gemini with retry logic for quota errors
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content([prompt] + images_for_gemini)
                    break
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            if "retry in" in error_str.lower():
                                try:
                                    import re
                                    delay_match = re.search(r'retry in ([\d.]+)s', error_str.lower())
                                    if delay_match:
                                        retry_delay = float(delay_match.group(1)) + 1
                                except:
                                    pass
                            print(f"Quota/rate limit hit. Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            raise Exception(
                                f"Gemini API quota exceeded after {max_retries} attempts. "
                                f"Please check your quota at: https://ai.dev/usage?tab=rate-limit"
                            )
                    else:
                        raise
            
            # Check if Gemini returned an image
            slide_img = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    # Check for inline image data
                    if hasattr(part, 'inline_data') and part.inline_data:
                        try:
                            image_data = base64.b64decode(part.inline_data.data)
                            slide_img = PILImage.open(io.BytesIO(image_data))
                            print("✓ Gemini generated slide image directly (inline_data)")
                            break
                        except Exception as e:
                            print(f"Warning: Could not decode inline_data: {e}")
                    
                    # Check for image in data attribute
                    if hasattr(part, 'data') and part.data:
                        try:
                            image_data = base64.b64decode(part.data)
                            slide_img = PILImage.open(io.BytesIO(image_data))
                            print("✓ Gemini generated slide image (data attribute)")
                            break
                        except Exception as e:
                            print(f"Warning: Could not decode data: {e}")
                    
                    # Check for image mime type
                    if hasattr(part, 'mime_type') and part.mime_type and part.mime_type.startswith('image/'):
                        if hasattr(part, 'data'):
                            try:
                                image_data = base64.b64decode(part.data)
                                slide_img = PILImage.open(io.BytesIO(image_data))
                                print("✓ Gemini generated slide image (mime_type)")
                                break
                            except Exception as e:
                                print(f"Warning: Could not decode mime_type data: {e}")
                    
                    # Check for text response (might contain base64 image)
                    if hasattr(part, 'text') and part.text:
                        response_text = part.text
                        # Look for base64 image data in text
                        import re
                        base64_pattern = r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)'
                        match = re.search(base64_pattern, response_text)
                        if match:
                            try:
                                image_data = base64.b64decode(match.group(1))
                                slide_img = PILImage.open(io.BytesIO(image_data))
                                print("✓ Gemini generated slide image (base64 in text)")
                                break
                            except Exception as e:
                                print(f"Warning: Could not decode base64 from text: {e}")
                        else:
                            print(f"Gemini response (text only): {response_text[:300]}...")
            
            if not slide_img:
                # Fallback if Gemini doesn't return image - use precise overlay method
                print("⚠ Gemini did not return image directly, using precise template overlay method...")
                print("   (This will create an exact replica by precisely replacing text/images)")
                return self._create_slide_with_template_overlay(
                    template_path, company_data, headshot_path, logo_path, map_path
                )
                
                # Convert generated image to PDF
                slide_rgb = slide_img.convert('RGB')
                if slide_rgb.size != (1920, 1080):
                    slide_rgb = slide_rgb.resize((1920, 1080), PILImage.Resampling.LANCZOS)
                
                pdf_bytes = io.BytesIO()
                slide_rgb.save(pdf_bytes, format='PDF', resolution=100.0)
                pdf_bytes.seek(0)
                
                print("✓ Slide created by Gemini - exact template replica with new content")
                return pdf_bytes.read()
            else:
                # Fallback if Gemini doesn't return image
                print("Gemini did not return image, using template overlay method...")
                return self._create_slide_with_template_overlay(
                    template_path, company_data, headshot_path, logo_path, map_path
                )
            
        except ImportError:
            raise ImportError(
                "google-generativeai package is required. Install it with: pip install google-generativeai"
            )
        except Exception as e:
            import traceback
            print(f"Error creating slide with Gemini: {e}\n{traceback.format_exc()}")
            # Fallback to template overlay method
            return self._create_slide_with_template_overlay(
                template_path, company_data, headshot_path, logo_path, map_path
            )
    
    def _create_slide_with_template_overlay(
        self,
        template_path: str,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        map_path: Optional[str] = None
    ) -> bytes:
        """
        Fallback method: Overlay content on template using PIL (no large blocks).
        Only erases text areas precisely, not entire regions.
        """
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        try:
            # Load template
            template = Image.open(template_path).convert('RGBA')
            if template.size != (1920, 1080):
                template = template.resize((1920, 1080), Image.Resampling.LANCZOS)
            
            slide = template.copy()
            draw = ImageDraw.Draw(slide)
            
            # Prepare company data
            company_name = company_data.get('name', 'Company Name')
            investment_stage = company_data.get('investment_stage', '')
            if not investment_stage:
                round_val = company_data.get('investment_round', 'PRE-SEED')
                quarter_val = company_data.get('quarter', 'Q2')
                year_val = company_data.get('year', '2024')
                investment_stage = f"{round_val} {quarter_val}, {year_val}"
            
            founders = company_data.get('founders', '')
            if isinstance(founders, list):
                founders = '\n'.join(founders)
            elif isinstance(founders, str) and ',' in founders:
                founders = '\n'.join([f.strip() for f in founders.split(',')])
            
            co_investors = company_data.get('co_investors', '')
            if isinstance(co_investors, list):
                co_investors = '\n'.join(co_investors)
            elif isinstance(co_investors, str) and ',' in co_investors:
                co_investors = '\n'.join([c.strip() for c in co_investors.split(',')])
            
            background = company_data.get('background', company_data.get('description', ''))
            
            # Load fonts
            try:
                company_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 140)
                stage_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
                body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            except:
                try:
                    company_font = ImageFont.truetype("arial.ttf", 140)
                    stage_font = ImageFont.truetype("arial.ttf", 32)
                    body_font = ImageFont.truetype("arial.ttf", 32)
                except:
                    company_font = ImageFont.load_default()
                    stage_font = ImageFont.load_default()
                    body_font = ImageFont.load_default()
            
            # Sample background colors precisely (no large blocks)
            def sample_bg(x, y):
                colors = []
                for dx in [-3, -2, -1, 1, 2, 3]:
                    for dy in [-3, -2, -1, 1, 2, 3]:
                        try:
                            px = template.getpixel((x+dx, y+dy))
                            if isinstance(px, tuple) and len(px) >= 3:
                                colors.append(px[:3])
                        except:
                            pass
                if colors:
                    return tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))
                return (42, 42, 42)
            
            # Erase ONLY text areas (precise, no blocks)
            # Investment stage - small area
            stage_bg = sample_bg(50, 65)
            draw.rectangle([(15, 45), (180, 85)], fill=stage_bg)
            
            # Company name - precise area
            name_bg = sample_bg(500, 100)
            draw.rectangle([(210, 55), (1000, 185)], fill=name_bg)
            
            # Founders - precise area below yellow box
            founders_bg = sample_bg(400, 430)
            text_height = len(founders.split('\n')) * 50
            draw.rectangle([(235, 340), (540, 340 + text_height)], fill=founders_bg)
            
            # Co-investors - precise area below yellow box
            investors_bg = sample_bg(800, 430)
            investors_height = len(co_investors.split('\n')) * 50
            draw.rectangle([(615, 340), (920, 340 + investors_height)], fill=investors_bg)
            
            # Background - precise area below yellow box
            bg_bg = sample_bg(800, 800)
            estimated_lines = min(len(background.split()) // 8 + 1, 8)
            bg_height = estimated_lines * 40
            draw.rectangle([(235, 600), (1200, 600 + bg_height)], fill=bg_bg)
            
            # Draw new text
            orange = (255, 140, 0)
            white = (255, 255, 255)
            
            draw.text((25, 50), investment_stage, fill=white, font=stage_font)
            draw.text((220, 60), company_name, fill=orange, font=company_font)
            
            founders_y = 340
            for i, line in enumerate(founders.split('\n')[:4]):
                if line.strip():
                    draw.text((240, founders_y + (i * 50)), line.strip(), fill=white, font=body_font)
            
            investors_y = 340
            for i, line in enumerate(co_investors.split('\n')[:4]):
                if line.strip():
                    draw.text((620, investors_y + (i * 50)), line.strip(), fill=white, font=body_font)
            
            # Background text (wrapped)
            bg_y = 600
            words = background.split()
            lines = []
            current = ""
            for word in words:
                test = current + " " + word if current else word
                bbox = draw.textbbox((0, 0), test, font=body_font)
                if bbox[2] - bbox[0] < 1000:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            
            for i, line in enumerate(lines[:8]):
                draw.text((240, bg_y + (i * 40)), line, fill=white, font=body_font)
            
            # Replace images (precise erasure)
            try:
                logo_bg = sample_bg(1700, 100)
                draw.rectangle([(1680, 30), (1900, 190)], fill=logo_bg)
                logo = Image.open(logo_path).convert('RGBA')
                logo = logo.resize((140, 140), Image.Resampling.LANCZOS)
                slide.paste(logo, (1700, 40), logo if logo.mode == 'RGBA' else None)
            except:
                pass
            
            try:
                headshot_bg = sample_bg(1600, 900)
                draw.rectangle([(1400, 700), (1910, 1080)], fill=headshot_bg)
                headshot = Image.open(headshot_path).convert('RGBA')
                headshot_grey = headshot.convert('L').convert('RGBA')
                for size, x, y in [(300, 1500, 750), (280, 1520, 770), (260, 1540, 790)]:
                    hs = headshot_grey.resize((size, size), Image.Resampling.LANCZOS)
                    mask = Image.new('L', (size, size), 0)
                    ImageDraw.Draw(mask).ellipse([(0, 0), (size, size)], fill=255)
                    hs.putalpha(mask)
                    slide.paste(hs, (x, y), hs)
            except:
                pass
            
            if map_path and os.path.exists(map_path):
                try:
                    map_bg = sample_bg(1500, 300)
                    draw.rectangle([(1200, 150), (1850, 650)], fill=map_bg)
                    map_img = Image.open(map_path).convert('RGBA')
                    map_img = map_img.resize((550, 450), Image.Resampling.LANCZOS)
                    slide.paste(map_img, (1300, 180), map_img if map_img.mode == 'RGBA' else None)
                except:
                    pass
            
            # Convert to PDF
            slide_rgb = slide.convert('RGB')
            pdf_bytes = io.BytesIO()
            slide_rgb.save(pdf_bytes, format='PDF', resolution=100.0)
            pdf_bytes.seek(0)
            
            print("✓ Slide created with precise text replacement (no large blocks)")
            return pdf_bytes.read()
            
        except Exception as e:
            import traceback
            print(f"Error in template overlay: {e}\n{traceback.format_exc()}")
            raise
    
    def _create_slide_standard(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        gemini_enhanced: bool = False,
        map_path: Optional[str] = None
    ) -> bytes:
        """Create slide using PIL/Pillow with standard or Gemini-enhanced design."""
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create a slide-sized image (1920x1080 for standard presentation)
        slide_width = 1920
        slide_height = 1080
        
        # Match your template design: dark grey background with orange sidebar
        dark_grey_bg = (42, 42, 42)  # Dark grey #2a2a2a
        orange_sidebar = (255, 140, 0)  # Bright orange #FF8C00
        yellow_highlight = (255, 215, 0)  # Yellow #FFD700
        white_text = (255, 255, 255)
        orange_text = (255, 140, 0)
        
        slide = Image.new('RGB', (slide_width, slide_height), color=dark_grey_bg)
        draw = ImageDraw.Draw(slide)
        
        # Draw orange vertical sidebar on the left
        sidebar_width = 200
        draw.rectangle([(0, 0), (sidebar_width, slide_height)], fill=orange_sidebar)
        
        # Enhanced design with better colors and spacing
        if gemini_enhanced:
            primary_color = orange_text  # Orange for company name
            accent_color = yellow_highlight  # Yellow for highlights
        else:
            primary_color = orange_text
            accent_color = yellow_highlight
        
        # Try to load fonts (fallback to default if not available)
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except:
            try:
                title_font = ImageFont.truetype("arial.ttf", 72)
                subtitle_font = ImageFont.truetype("arial.ttf", 48)
                text_font = ImageFont.truetype("arial.ttf", 36)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
        
        # Add sidebar text (matching exact design)
        try:
            # Investment stage text at TOP of sidebar (horizontal, white text)
            investment_stage = company_data.get('investment_stage', '')
            if not investment_stage:
                # Build from separate fields - format: "PRE-SEED Q2, 2024"
                round_val = company_data.get('investment_round', 'PRE-SEED')
                quarter_val = company_data.get('quarter', 'Q2')
                year_val = company_data.get('year', '2024')
                investment_stage = f"{round_val} {quarter_val}, {year_val}"
            
            # Top of sidebar - horizontal text, white
            draw.text((20, 50), investment_stage, fill=white_text, font=subtitle_font)
            
            # "SLAUSON&CO." at BOTTOM of sidebar - rotated 90 degrees clockwise (vertical)
            # Create rotated text
            from PIL import ImageFont
            try:
                brand_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            except:
                try:
                    brand_font = ImageFont.truetype("arial.ttf", 36)
                except:
                    brand_font = ImageFont.load_default()
            
            # Create a temporary image for rotated text
            temp_img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            temp_draw.text((0, 0), "SLAUSON&CO.", fill=white_text, font=brand_font)
            # Rotate 90 degrees clockwise
            rotated_text = temp_img.rotate(-90, expand=True)
            # Paste at bottom of sidebar
            slide.paste(rotated_text, (20, slide_height - 250), rotated_text)
        except Exception as e:
            print(f"Warning: Could not add sidebar text: {e}")
        
        # Load and resize logo (top right corner, small circular)
        try:
            logo = Image.open(logo_path).convert('RGBA')
            # Resize to small size for top right
            logo = logo.resize((120, 120), Image.Resampling.LANCZOS)
            # Paste logo at top right (1700, 50)
            slide.paste(logo, (1700, 50), logo if logo.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
        
        # Add company name (title) - LARGE bold orange text at top left (after sidebar)
        company_name = company_data.get('name', 'Company Name')
        # Use larger font for company name
        try:
            company_name_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 96)
        except:
            try:
                company_name_font = ImageFont.truetype("arial.ttf", 96)
            except:
                company_name_font = title_font
        draw.text((250, 80), company_name, fill=orange_text, font=company_name_font)
        
        # Add sections with yellow highlight boxes (matching exact design)
        # Yellow boxes contain ONLY the label (bold black), content is BELOW in white
        
        y_start = 220  # Start below company name
        
        # Founders section
        founders = company_data.get('founders', '')
        if isinstance(founders, list):
            founders = '\n'.join(founders)  # Each founder on new line
        elif isinstance(founders, str) and ',' in founders:
            # Split by comma and put each on new line
            founders = '\n'.join([f.strip() for f in founders.split(',')])
        
        if founders:
            # Yellow highlight box - ONLY for label
            label_box_height = 50
            draw.rectangle([(250, y_start), (450, y_start + label_box_height)], fill=yellow_highlight, outline=None)
            draw.text((260, y_start + 10), "Founders", fill=(0, 0, 0), font=subtitle_font)
            
            # Founder names BELOW the yellow box in WHITE
            founder_lines = founders.split('\n')
            text_y = y_start + label_box_height + 20
            for founder in founder_lines[:5]:  # Max 5 founders
                draw.text((260, text_y), founder.strip(), fill=white_text, font=text_font)
                text_y += 45
            y_start = text_y + 30
        
        # Co-Investors section
        co_investors = company_data.get('co_investors', '')
        if isinstance(co_investors, list):
            co_investors = '\n'.join(co_investors)
        elif isinstance(co_investors, str) and ',' in co_investors:
            co_investors = '\n'.join([c.strip() for c in co_investors.split(',')])
        
        if co_investors:
            # Yellow highlight box - ONLY for label
            label_box_height = 50
            draw.rectangle([(250, y_start), (500, y_start + label_box_height)], fill=yellow_highlight, outline=None)
            draw.text((260, y_start + 10), "Co-Investors", fill=(0, 0, 0), font=subtitle_font)
            
            # Investor names BELOW the yellow box in WHITE
            investor_lines = co_investors.split('\n')
            text_y = y_start + label_box_height + 20
            for investor in investor_lines[:5]:  # Max 5 investors
                draw.text((260, text_y), investor.strip(), fill=white_text, font=text_font)
                text_y += 45
            y_start = text_y + 30
        
        # Background section
        background = company_data.get('background', company_data.get('description', ''))
        if background:
            # Yellow highlight box - ONLY for label
            label_box_height = 50
            bg_y = y_start
            draw.rectangle([(250, bg_y), (450, bg_y + label_box_height)], fill=yellow_highlight, outline=None)
            draw.text((260, bg_y + 10), "Background", fill=(0, 0, 0), font=subtitle_font)
            
            # Background text BELOW the yellow box in WHITE (wrapped)
            words = background.split()
            lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=text_font)
                if bbox[2] - bbox[0] < 900:  # Max width
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            text_y = bg_y + label_box_height + 20
            for line in lines[:8]:  # Max 8 lines for background
                draw.text((260, text_y), line, fill=white_text, font=text_font)
                text_y += 40
        
        # Add map image if provided (upper right area, above headshots)
        if map_path and os.path.exists(map_path):
            try:
                map_img = Image.open(map_path).convert('RGBA')
                map_img = map_img.resize((600, 400), Image.Resampling.LANCZOS)
                # Paste map in upper right area (above headshots)
                slide.paste(map_img, (1250, 250), map_img if map_img.mode == 'RGBA' else None)
            except Exception as e:
                print(f"Warning: Could not load map: {e}")
        
        # Load and resize headshot (bottom right - matching your template)
        try:
            headshot = Image.open(headshot_path).convert('RGBA')
            # Resize to appropriate size for bottom right
            headshot = headshot.resize((400, 300), Image.Resampling.LANCZOS)
            # Paste headshot at bottom right (overlapping style if multiple)
            slide.paste(headshot, (1400, 700), headshot if headshot.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Warning: Could not load headshot: {e}")
        
        # Add location if provided (for map generation reference)
        location = company_data.get('location', company_data.get('address', ''))
        if location:
            # Small text in corner
            draw.text((250, slide_height - 50), f"📍 {location}", fill=(150, 150, 150), font=text_font)
        
        # Convert to PDF bytes using img2pdf for reliable PDF generation
        try:
            import img2pdf
            # Save image to bytes buffer first
            img_bytes = io.BytesIO()
            slide.save(img_bytes, format='PNG', quality=95)
            img_bytes.seek(0)
            img_data = img_bytes.getvalue()
            
            # Convert PNG to PDF with proper page size
            pdf_bytes = img2pdf.convert(
                img_data,
                pagesize=(img2pdf.in_to_pt(20), img2pdf.in_to_pt(11.25))  # 1920x1080 at 96 DPI
            )
            print(f"Successfully converted slide to PDF using img2pdf, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except ImportError:
            # Fallback: Use reportlab or fpdf if available
            print("Warning: img2pdf not available, trying alternative methods...")
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.utils import ImageReader
                
                pdf_bytes = io.BytesIO()
                c = canvas.Canvas(pdf_bytes, pagesize=(1920, 1080))
                # Draw image on canvas
                img_bytes = io.BytesIO()
                slide.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                c.drawImage(ImageReader(img_bytes), 0, 0, width=1920, height=1080)
                c.save()
                pdf_bytes.seek(0)
                print("Successfully converted slide to PDF using reportlab")
                return pdf_bytes.read()
            except ImportError:
                print("Warning: reportlab not available, using PIL PDF (may have issues)")
                pdf_bytes = io.BytesIO()
                slide.save(pdf_bytes, format='PDF', resolution=100.0)
                pdf_bytes.seek(0)
                return pdf_bytes.read()
        except Exception as e:
            print(f"Error converting to PDF with img2pdf: {e}")
            import traceback
            print(traceback.format_exc())
            # Try reportlab as fallback
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.utils import ImageReader
                
                pdf_bytes = io.BytesIO()
                c = canvas.Canvas(pdf_bytes, pagesize=(1920, 1080))
                img_bytes = io.BytesIO()
                slide.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                c.drawImage(ImageReader(img_bytes), 0, 0, width=1920, height=1080)
                c.save()
                pdf_bytes.seek(0)
                print("Successfully converted slide to PDF using reportlab (fallback)")
                return pdf_bytes.read()
            except Exception as e2:
                print(f"Error with reportlab fallback: {e2}")
                # Last resort: return PNG as bytes (not ideal but better than broken PDF)
                img_bytes = io.BytesIO()
                slide.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                print("Warning: Returning PNG instead of PDF due to conversion errors")
                return img_bytes.read()
