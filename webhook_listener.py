"""
Webhook listener for form submissions.
Can be used with Zapier, Make.com, or as a standalone Flask server.
"""
from flask import Flask, request, jsonify
from main import PortfolioOnboardingAutomation
from image_processor import ImageProcessor
from canva_integration import CanvaIntegration
from html_slide_generator import HTMLSlideGenerator
from google_drive_integration import GoogleDriveIntegration
from docsend_integration import DocSendIntegration
from notion_integration import NotionIntegration
from config import Config
import os
import tempfile
import base64
import io
import requests
from urllib.parse import urlparse

app = Flask(__name__)


def download_file_from_url(url: str, output_path: str):
    """
    Download file from URL (handles Notion file URLs).
    
    Args:
        url: URL to download from
        output_path: Path to save file
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def handle_image_input(image_data, temp_dir: str, filename: str) -> str:
    """
    Handle image input - can be base64 string or URL.
    
    Args:
        image_data: Base64 string or URL
        temp_dir: Temporary directory path
        filename: Output filename
        
    Returns:
        Path to saved image file
    """
    file_path = os.path.join(temp_dir, filename)
    
    # Check if it's a URL
    if isinstance(image_data, str) and (image_data.startswith('http://') or image_data.startswith('https://')):
        # It's a URL - download it
        download_file_from_url(image_data, file_path)
    else:
        # Assume it's base64 encoded
        image_bytes = base64.b64decode(image_data)
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
    
    return file_path


@app.route('/webhook/onboarding', methods=['POST'])
def handle_onboarding():
    """
    Handle onboarding form submission webhook.
    
    Expected JSON payload (supports multiple formats):
    
    Format 1 - Base64 images:
    {
        "company_data": {
            "name": "...",
            "website": "...",
            ...
        },
        "headshot": "base64_encoded_image",
        "logo": "base64_encoded_image"
    }
    
    Format 2 - File URLs (from Notion):
    {
        "company_data": { ... },
        "headshot_url": "https://notion.so/file/...",
        "logo_url": "https://notion.so/file/..."
    }
    
    Format 3 - Mixed:
    {
        "company_data": { ... },
        "headshot": "base64_or_url",
        "logo": "base64_or_url"
    }
    
    Format 4 - Zapier with Notion metadata:
    {
        "company_data": { ... },
        "headshot_url": "...",
        "logo_url": "...",
        "notion_page_id": "...",
        "notion_created_time": "...",
        "notion_last_edited": "..."
    }
    """
    try:
        data = request.json
        
        # Log incoming request for debugging
        print(f"\n{'='*60}")
        print(f"Received webhook request: {request.method} {request.path}")
        print(f"Payload keys: {list(data.keys()) if data else 'None'}")
        print(f"{'='*60}\n")
        
        if not data:
            return jsonify({"error": "Missing data"}), 400
        
        # Handle both nested and flat formats
        # Format 1: Nested: {"company_data": {"name": "...", ...}}
        # Format 2: Flat: {"company_data__name": "...", "company_data__description": "...", ...}
        company_data = {}
        
        if "company_data" in data and isinstance(data["company_data"], dict):
            # Nested format
            company_data = data["company_data"]
        else:
            # Flat format (company_data__field_name)
            # Extract all fields that start with "company_data__"
            for key, value in data.items():
                if key.startswith("company_data__"):
                    # Remove "company_data__" prefix
                    field_name = key.replace("company_data__", "")
                    company_data[field_name] = value
                elif key not in ["headshot_url", "logo_url", "notion_page_id", "notion_created_time", "notion_last_edited", "status"]:
                    # Also include other fields that might be company data
                    company_data[key] = value
        
        # If still no company data, try to build from available fields
        if not company_data:
            # Try to extract from flat structure
            company_data = {
                "name": data.get("company_data__name") or data.get("name", ""),
                "description": data.get("company_data__description") or data.get("description", ""),
                "address": data.get("company_data__address") or data.get("address") or data.get("location", ""),
                "location": data.get("company_data__address") or data.get("address") or data.get("location", ""),
                "investment_date": data.get("company_data__investment_date") or data.get("investment_date", ""),
                "investment_round": data.get("company_data__investment_round") or data.get("investment_round", ""),
                "founders": data.get("company_data__founders") or data.get("founders", ""),
                "co_investors": data.get("company_data__co_investors") or data.get("co_investors", ""),
                "background": data.get("company_data__background") or data.get("background", ""),
            }
        
        # Normalize founders and co_investors - convert comma-separated strings to lists if needed
        if "founders" in company_data and isinstance(company_data["founders"], str):
            # Split by comma if it's a string
            founders_str = company_data["founders"].strip()
            if founders_str:
                company_data["founders"] = [f.strip() for f in founders_str.split(",") if f.strip()]
            else:
                company_data["founders"] = []
        
        if "co_investors" in company_data and isinstance(company_data["co_investors"], str):
            # Split by comma if it's a string
            co_investors_str = company_data["co_investors"].strip()
            if co_investors_str:
                company_data["co_investors"] = [c.strip() for c in co_investors_str.split(",") if c.strip()]
            else:
                company_data["co_investors"] = []
        
        print(f"Company data extracted: {list(company_data.keys())}")
        print(f"Company name: {company_data.get('name', 'N/A')}")
        print(f"Founders: {company_data.get('founders', [])}")
        print(f"Co-investors: {company_data.get('co_investors', [])}")
        
        # Store Notion metadata if provided (for reference)
        notion_metadata = {
            "page_id": data.get("notion_page_id"),
            "created_time": data.get("notion_created_time"),
            "last_edited": data.get("notion_last_edited")
        }
        
        # Create temporary files for images
        with tempfile.TemporaryDirectory() as temp_dir:
            headshot_path = None
            logo_path = None
            
            # Handle headshot - check multiple possible field names
            if "headshot" in data:
                headshot_path = handle_image_input(
                    data["headshot"],
                    temp_dir,
                    "headshot.jpg"
                )
            elif "headshot_url" in data:
                headshot_path = handle_image_input(
                    data["headshot_url"],
                    temp_dir,
                    "headshot.jpg"
                )
            
            # Handle logo - check multiple possible field names
            if "logo" in data:
                logo_path = handle_image_input(
                    data["logo"],
                    temp_dir,
                    "logo.png"
                )
            elif "logo_url" in data:
                logo_path = handle_image_input(
                    data["logo_url"],
                    temp_dir,
                    "logo.png"
                )
            
            # Headshot and logo are optional - check if they exist in company_data
            if not headshot_path:
                # Try to get from company_data
                if "headshot" in company_data:
                    headshot_path = handle_image_input(
                        company_data["headshot"],
                        temp_dir,
                        "headshot.jpg"
                    )
                elif "headshot_url" in company_data:
                    headshot_path = handle_image_input(
                        company_data["headshot_url"],
                        temp_dir,
                        "headshot.jpg"
                    )
            
            if not logo_path:
                # Try to get from company_data
                if "logo" in company_data:
                    logo_path = handle_image_input(
                        company_data["logo"],
                        temp_dir,
                        "logo.png"
                    )
                elif "logo_url" in company_data:
                    logo_path = handle_image_input(
                        company_data["logo_url"],
                        temp_dir,
                        "logo.png"
                    )
            
            # If still missing, create placeholder files or skip image processing
            if not headshot_path:
                print("Warning: No headshot provided - creating placeholder")
                headshot_path = os.path.join(temp_dir, "headshot_placeholder.jpg")
                # Create a small placeholder image
                from PIL import Image
                placeholder = Image.new('RGB', (200, 200), color='gray')
                placeholder.save(headshot_path)
            
            if not logo_path:
                print("Warning: No logo provided - creating placeholder")
                logo_path = os.path.join(temp_dir, "logo_placeholder.png")
                # Create a small placeholder image
                from PIL import Image
                placeholder = Image.new('RGB', (200, 200), color='lightgray')
                placeholder.save(logo_path)
            
            # NEW WORKFLOW: Process headshots, generate map, create slide, upload, update Notion
            
            results = {
                "success": False,
                "google_drive_link": None,
                "docsend_link": None,
                "notion_page_id": notion_metadata.get("page_id"),
                "errors": []
            }
            
            try:
                # Step 1: Process headshots with Gemini (background removal, greyscale, combine)
                print("Processing headshots with Gemini...")
                headshot_paths = []
                
                # Collect all headshot paths (could be multiple founders)
                if headshot_path:
                    headshot_paths.append(headshot_path)
                
                # Check if there are multiple headshots in company_data
                if "headshots" in company_data and isinstance(company_data["headshots"], list):
                    for hs_data in company_data["headshots"]:
                        if isinstance(hs_data, str):
                            # It's a URL or path
                            hs_path = handle_image_input(hs_data, temp_dir, f"headshot_{len(headshot_paths)}.jpg")
                            headshot_paths.append(hs_path)
                
                # Process headshots with Gemini
                if headshot_paths:
                    try:
                        combined_headshot_path = os.path.join(temp_dir, "combined_headshots.png")
                        combined_headshot_bytes = ImageProcessor.process_headshots_with_gemini(
                            headshot_paths,
                            combined_headshot_path
                        )
                        print("✓ Headshots processed and combined")
                    except Exception as e:
                        print(f"Warning: Gemini headshot processing failed: {e}")
                        results["errors"].append(f"Headshot processing: {str(e)}")
                        # Use first headshot as fallback
                        if headshot_paths:
                            with open(headshot_paths[0], 'rb') as f:
                                combined_headshot_bytes = f.read()
                else:
                    # Create placeholder
                    from PIL import Image
                    placeholder = Image.new('RGB', (400, 400), color='gray')
                    placeholder_bytes = io.BytesIO()
                    placeholder.save(placeholder_bytes, format='PNG')
                    combined_headshot_bytes = placeholder_bytes.getvalue()
                
                # Step 2: Generate map with Gemini
                print("Generating map with Gemini...")
                location = company_data.get("address", company_data.get("location", ""))
                # Extract city name if address is full address
                if "," in location:
                    location = location.split(",")[0].strip()
                
                map_path = os.path.join(temp_dir, "map.png")
                try:
                    map_bytes = ImageProcessor.generate_map_with_gemini(location, map_path)
                    print(f"✓ Map generated for {location}")
                except Exception as e:
                    print(f"Warning: Gemini map generation failed: {e}")
                    results["errors"].append(f"Map generation: {str(e)}")
                    # Create placeholder map
                    from PIL import Image, ImageDraw, ImageFont
                    img = Image.new('RGB', (800, 600), color=(40, 40, 40))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([100, 100, 700, 500], outline=(255, 140, 0), width=3)
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
                    except:
                        font = ImageFont.load_default()
                    draw.text((400, 300), location, fill=(255, 255, 0), font=font, anchor="mm")
                    placeholder_bytes = io.BytesIO()
                    img.save(placeholder_bytes, format='PNG')
                    map_bytes = placeholder_bytes.getvalue()
                
                # Step 3: Prepare company data for Canva
                # Add map image to company_data for Canva
                company_data["map_image"] = map_bytes
                
                # Step 4: Create slide (HTML → PDF preferred, then Canva, then Gemini fallback)
                print("Creating slide...")
                slide_pdf_path = os.path.join(temp_dir, "slide.pdf")
                
                try:
                    # Save combined headshot temporarily
                    temp_headshot_path = os.path.join(temp_dir, "headshot_combined.png")
                    with open(temp_headshot_path, 'wb') as f:
                        f.write(combined_headshot_bytes)
                    
                    # Get map path if available
                    map_path = os.path.join(temp_dir, "map.png") if os.path.exists(os.path.join(temp_dir, "map.png")) else None
                    
                    slide_pdf_bytes = None
                    
                    # Try HTML → PDF first (simplest, full control)
                    try:
                        print("📄 Using HTML → PDF method...")
                        html_gen = HTMLSlideGenerator()
                        slide_pdf_bytes = html_gen.create_slide(
                            company_data,
                            temp_headshot_path,
                            logo_path,
                            map_path=map_path
                        )
                        print("✓ Slide created with HTML → PDF")
                    except Exception as html_error:
                        print(f"⚠️  HTML → PDF failed: {html_error}")
                        print("   Trying Canva...")
                        
                        # Try Canva only if credentials are available
                        canva_error = None
                        from config import Config
                        has_canva_creds = (
                            (Config.CANVA_API_KEY or (Config.CANVA_CLIENT_ID and Config.CANVA_CLIENT_SECRET)) 
                            and Config.CANVA_TEMPLATE_ID
                        )
                        
                        if has_canva_creds:
                            try:
                                print("🎨 Using Canva template...")
                                canva = CanvaIntegration()
                                slide_pdf_bytes = canva.create_slide_alternative(
                                    company_data,
                                    temp_headshot_path,
                                    logo_path,
                                    map_path=map_path
                                )
                                print("✓ Slide created with Canva")
                            except Exception as e:
                                canva_error = e
                                print(f"⚠️  Canva failed: {canva_error}")
                        
                        if not slide_pdf_bytes:
                            error_msg = f"HTML → PDF error: {html_error}"
                            if canva_error:
                                error_msg += f". Canva error: {canva_error}"
                            else:
                                if not has_canva_creds:
                                    error_msg += ". Canva skipped (credentials not configured)"
                            raise Exception(error_msg)
                    
                except Exception as e:
                    print(f"Error creating slide: {e}")
                    results["errors"].append(f"Slide creation: {str(e)}")
                    raise
                
                # Step 5: Upload PDF to Google Drive
                print("Uploading PDF to Google Drive...")
                google_drive_link = None
                try:
                    drive = GoogleDriveIntegration()
                    filename = f"{company_data.get('name', 'slide').replace(' ', '_')}_slide.pdf"
                    google_drive_link = drive.upload_pdf(
                        slide_pdf_bytes,
                        filename,
                        folder_id=Config.GOOGLE_DRIVE_FOLDER_ID
                    )
                    results["google_drive_link"] = google_drive_link
                    print(f"✓ Uploaded to Google Drive: {google_drive_link}")
                except Exception as e:
                    print(f"Warning: Google Drive upload failed: {e}")
                    results["errors"].append(f"Google Drive: {str(e)}")
                
                # Step 6: DocSend (optional - uses Google Drive sync)
                print("DocSend integration via Google Drive...")
                docsend_link = None
                
                # Since DocSend syncs from Google Drive automatically,
                # we can either:
                # 1. Skip DocSend API upload (relies on Google Drive sync)
                # 2. Or try to get DocSend link if API is available
                
                if Config.DOCSEND_API_KEY and Config.DOCSEND_API_KEY != "your_docsend_api_key_here":
                    # Try DocSend API upload if API key is configured
                    try:
                        docsend = DocSendIntegration()
                        docsend_link = docsend.upload_individual_slide(
                            slide_pdf_bytes,
                            company_data.get("name", "Company")
                        )
                        results["docsend_link"] = docsend_link
                        print(f"✓ Uploaded to DocSend via API: {docsend_link}")
                    except Exception as e:
                        print(f"Warning: DocSend API upload failed: {e}")
                        results["errors"].append(f"DocSend API: {str(e)}")
                        # Fall through to Google Drive sync method
                else:
                    # DocSend will auto-sync from Google Drive
                    print("✓ DocSend will auto-sync from Google Drive")
                    print("  Note: DocSend link will need to be retrieved manually or via DocSend API")
                    # You can manually get the DocSend link from the Google Drive file
                    # Or set up DocSend API later to get the link programmatically
                
                # Step 7: Update Notion record
                print("Updating Notion record...")
                notion_page_id = notion_metadata.get("page_id")
                if notion_page_id and Config.NOTION_API_KEY:
                    try:
                        notion = NotionIntegration()
                        notion.update_company_record(
                            notion_page_id,
                            google_drive_link=google_drive_link,
                            docsend_link=docsend_link,
                            status="completed"
                        )
                        print("✓ Notion record updated")
                    except Exception as e:
                        print(f"Warning: Notion update failed: {e}")
                        results["errors"].append(f"Notion update: {str(e)}")
                else:
                    print("Skipping Notion update (no page ID or API key)")
                
                # Step 8: Mark as successful
                results["success"] = True
                print("\n" + "="*60)
                print("✓ Processing complete!")
                print(f"  Google Drive: {google_drive_link or 'N/A'}")
                print(f"  DocSend: {docsend_link or 'N/A'}")
                print("="*60 + "\n")
                
            except Exception as e:
                import traceback
                print(f"\n❌ ERROR IN WORKFLOW:")
                print(f"Error: {str(e)}")
                print(f"Traceback:\n{traceback.format_exc()}\n")
                results["errors"].append(str(e))
                results["success"] = False
            
            # Return JSON response to Zapier
            return jsonify(results), 200 if results["success"] else 500
            
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        # Print to console for debugging
        print(f"\n❌ ERROR PROCESSING WEBHOOK:")
        print(f"Error: {str(e)}")
        print(f"Type: {type(e).__name__}")
        print(f"Traceback:\n{traceback.format_exc()}\n")
        return jsonify(error_details), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))  # Changed default to 5001
    # Disable debug mode in production
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

