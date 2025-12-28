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
from PyPDF2 import PdfWriter, PdfReader
import os
import tempfile
import base64
import io
import requests
from urllib.parse import urlparse

app = Flask(__name__)


def download_file_from_url(url: str, output_path: str):
    """
    Download file from URL (handles Notion file URLs and Google Drive URLs).
    
    Args:
        url: URL to download from
        output_path: Path to save file
    """
    # Handle Google Drive URLs in different formats
    if 'drive.google.com' in url:
        # Extract file ID from various Google Drive URL formats
        import re
        file_id = None
        
        # Format 1: https://drive.google.com/open?id=FILE_ID
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
        # Format 2: https://drive.google.com/file/d/FILE_ID/view
        else:
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
        
        if file_id:
            # Convert to direct download URL
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            print(f"  Converting Google Drive URL to direct download: {file_id}")
    
    # Try to download with authentication headers if it's a Google Drive file
    headers = {}
    if 'drive.google.com' in url:
        # Add headers to handle Google Drive's virus scan warning
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    response = requests.get(url, stream=True, headers=headers, allow_redirects=True)
    response.raise_for_status()
    
    # Handle Google Drive's virus scan warning page
    if 'text/html' in response.headers.get('Content-Type', ''):
        # Try to extract the actual download link from the warning page
        content = response.text
        if 'virus scan warning' in content.lower() or 'download anyway' in content.lower():
            # Extract the actual download link
            import re
            match = re.search(r'href="(/uc\?export=download[^"]+)"', content)
            if match:
                download_url = 'https://drive.google.com' + match.group(1)
                print(f"  Found download link after virus scan warning, retrying...")
                response = requests.get(download_url, stream=True, headers=headers, allow_redirects=True)
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
        if data:
            print(f"Payload sample (first 500 chars): {str(data)[:500]}")
        print(f"{'='*60}\n")
        
        if not data:
            error_msg = "Missing data in request body"
            print(f"❌ ERROR: {error_msg}")
            return jsonify({"error": error_msg, "success": False}), 400
        
        # Handle both nested and flat formats
        # Format 1: Nested: {"company_data": {"name": "...", ...}}
        # Format 2: Flat: {"company_data__name": "...", "company_data__description": "...", ...}
        company_data = {}
        
        if "company_data" in data and isinstance(data["company_data"], dict):
            # Nested format
            company_data = data["company_data"]
            print("✓ Found nested company_data format")
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
            print("⚠️  No nested company_data found, trying flat format extraction...")
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
        print(f"Company name: '{company_data.get('name', '')}'")
        print(f"Description: '{company_data.get('description', '')[:50]}...' (first 50 chars)")
        print(f"Address: '{company_data.get('address', '')}'")
        print(f"Founders: {company_data.get('founders', [])}")
        print(f"Co-investors: {company_data.get('co_investors', [])}")
        print(f"Background: '{company_data.get('background', '')[:50]}...' (first 50 chars)")
        
        # Validate required fields
        required_fields = {
            "name": company_data.get("name", "").strip(),
            "description": company_data.get("description", "").strip(),
            "address": company_data.get("address", company_data.get("location", "")).strip(),
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            error_msg = f"Missing required company data fields: {', '.join(missing_fields)}. "
            error_msg += f"Received payload keys: {list(data.keys())}. "
            error_msg += f"Company data keys: {list(company_data.keys())}. "
            error_msg += "Please ensure Zapier sends: company_data__name, company_data__description, company_data__address (or company_data__location)"
            print(f"❌ VALIDATION ERROR: {error_msg}")
            return jsonify({
                "error": error_msg,
                "success": False,
                "missing_fields": missing_fields,
                "received_keys": list(data.keys()),
                "company_data_keys": list(company_data.keys())
            }), 400
        
        # Warn about missing optional but important fields
        optional_fields = {
            "founders": company_data.get("founders", []),
            "co_investors": company_data.get("co_investors", []),
            "background": company_data.get("background", "").strip(),
            "investment_round": company_data.get("investment_round", "").strip(),
        }
        
        missing_optional = [field for field, value in optional_fields.items() if not value]
        if missing_optional:
            print(f"⚠️  Warning: Missing optional fields: {', '.join(missing_optional)}")
            print("   Slide will be generated but may have empty sections")
        
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
                try:
                    headshot_path = handle_image_input(
                        data["headshot"],
                        temp_dir,
                        "headshot.jpg"
                    )
                except Exception as e:
                    print(f"Warning: Failed to process headshot from 'headshot' field: {e}")
                    headshot_path = None
            elif "headshot_url" in data:
                try:
                    print(f"Downloading headshot from URL: {data['headshot_url'][:100]}...")
                    headshot_path = handle_image_input(
                        data["headshot_url"],
                        temp_dir,
                        "headshot.jpg"
                    )
                    print(f"✓ Headshot downloaded successfully")
                except Exception as e:
                    print(f"Warning: Failed to download headshot from URL: {e}")
                    import traceback
                    traceback.print_exc()
                    headshot_path = None
            
            # Handle logo - check multiple possible field names
            if "logo" in data:
                try:
                    logo_path = handle_image_input(
                        data["logo"],
                        temp_dir,
                        "logo.png"
                    )
                except Exception as e:
                    print(f"Warning: Failed to process logo from 'logo' field: {e}")
                    logo_path = None
            elif "logo_url" in data:
                try:
                    print(f"Downloading logo from URL: {data['logo_url'][:100]}...")
                    logo_path = handle_image_input(
                        data["logo_url"],
                        temp_dir,
                        "logo.png"
                    )
                    print(f"✓ Logo downloaded successfully")
                except Exception as e:
                    print(f"Warning: Failed to download logo from URL: {e}")
                    import traceback
                    traceback.print_exc()
                    logo_path = None
            
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
                        # Use first headshot as fallback - HTML slide generator will process it
                        if headshot_paths:
                            # Save the raw headshot path - HTML slide generator will handle processing
                            combined_headshot_path = headshot_paths[0]
                            # Read bytes for compatibility, but we'll use the path directly
                            with open(headshot_paths[0], 'rb') as f:
                                combined_headshot_bytes = f.read()
                        else:
                            combined_headshot_path = None
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
                
                # Step 4: Create slide (HTML → PDF preferred, then Canva if configured)
                print("Creating slide...")
                slide_pdf_path = os.path.join(temp_dir, "slide.pdf")
                
                try:
                    # Save combined headshot temporarily
                    # Ensure it's saved as PNG with RGBA format for transparency processing
                    temp_headshot_path = os.path.join(temp_dir, "headshot_combined.png")
                    from PIL import Image
                    # Load the image to ensure it's in the right format (io is already imported at top)
                    headshot_img = Image.open(io.BytesIO(combined_headshot_bytes))
                    # Convert to RGBA to ensure alpha channel exists
                    if headshot_img.mode != 'RGBA':
                        headshot_img = headshot_img.convert('RGBA')
                    # Save as PNG to preserve transparency capability
                    headshot_img.save(temp_headshot_path, 'PNG')
                    print(f"✓ Saved headshot for processing: {temp_headshot_path} (mode: {headshot_img.mode})")
                    
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
                
                # Step 5: Check if slides already exist for this Notion page
                notion_page_id = notion_metadata.get("page_id")
                existing_slides = False
                existing_google_drive_link = None
                existing_canva_design_id = None
                
                if notion_page_id and Config.NOTION_API_KEY:
                    try:
                        notion = NotionIntegration()
                        existing_data = notion.get_company_by_page_id(notion_page_id)
                        if existing_data:
                            # Check if this page already has slides
                            existing_google_drive_link = existing_data.get("google_drive_link")
                            existing_canva_design_id = existing_data.get("canva_design_id")
                            
                            if existing_google_drive_link or existing_canva_design_id:
                                existing_slides = True
                                print(f"📋 Found existing slides for this Notion page:")
                                if existing_google_drive_link:
                                    print(f"   Google Drive: {existing_google_drive_link}")
                                if existing_canva_design_id:
                                    print(f"   Canva Design ID: {existing_canva_design_id}")
                                print("   Will update/replace existing slides...")
                            else:
                                print("📄 No existing slides found, creating new ones...")
                    except Exception as e:
                        print(f"⚠️  Could not check for existing slides: {e}")
                        # Continue with creating new slides
                
                # Step 6/7: Upload or append PDF to Google Drive (preserve DocSend link)
                print("Uploading PDF to Google Drive (append/overwrite if existing)...")
                filename = f"{company_data.get('name', 'slide').replace(' ', '_')}_slide.pdf"
                google_drive_link = None
                try:
                    drive = GoogleDriveIntegration()

                    # Preferred static target (SlidesGen.pdf) via env/Config
                    static_file_id = os.getenv("GOOGLE_DRIVE_STATIC_FILE_ID") or getattr(Config, "GOOGLE_DRIVE_STATIC_FILE_ID", None)
                    static_file_name = os.getenv("GOOGLE_DRIVE_STATIC_FILE_NAME") or getattr(Config, "GOOGLE_DRIVE_STATIC_FILE_NAME", None)

                    target_file_id = None
                    # Resolve static file ID by name if only name is provided
                    if not static_file_id and static_file_name:
                        target_file_id = drive.find_file_id_by_name(static_file_name, parent_folder_id=Config.GOOGLE_DRIVE_FOLDER_ID)
                        if target_file_id:
                            print(f"   Found static Drive file by name '{static_file_name}': {target_file_id}")
                    elif static_file_id:
                        target_file_id = static_file_id

                    # If no static target, fall back to existing link from Notion
                    if not target_file_id and existing_slides and existing_google_drive_link:
                        target_file_id = drive.extract_file_id_from_url(existing_google_drive_link)

                    # If still none, this is a fresh upload (or static name not found)
                    if not target_file_id:
                        google_drive_link = drive.upload_pdf(
                            slide_pdf_bytes,
                            static_file_name or filename,
                            folder_id=Config.GOOGLE_DRIVE_FOLDER_ID
                        )
                        results["google_drive_link"] = google_drive_link
                        print(f"✓ Uploaded new Drive PDF: {google_drive_link}")
                    else:
                        try:
                            print("   Downloading target Drive PDF...")
                            existing_bytes = drive.download_file(target_file_id)
                            old_reader = PdfReader(io.BytesIO(existing_bytes))
                            new_reader = PdfReader(io.BytesIO(slide_pdf_bytes))
                            
                            # Check if we should replace existing slide for this company
                            # If the same Notion page is being edited, replace the old slide instead of appending
                            company_name = company_data.get('name', '').lower().strip()
                            should_replace = existing_slides and notion_page_id
                            
                            if should_replace:
                                print(f"   Replacing existing slide for company '{company_name}' (Notion page edited)...")
                                # Try to find and remove the old slide for this company
                                # Extract company name from PDF pages to identify which page to replace
                                writer = PdfWriter()
                                replaced = False
                                
                                # Try to identify the company's slide by checking page text
                                for i, page in enumerate(old_reader.pages):
                                    try:
                                        page_text = page.extract_text().lower()
                                        # Check if this page contains the company name
                                        if company_name and company_name in page_text:
                                            print(f"   Found old slide for '{company_name}' at page {i+1}, replacing it...")
                                            # Skip this page (replace with new slide)
                                            replaced = True
                                            # Add new slide in its place
                                            for new_page in new_reader.pages:
                                                writer.add_page(new_page)
                                        else:
                                            # Keep pages that don't match this company
                                            writer.add_page(page)
                                    except Exception as e:
                                        # If text extraction fails, keep the page
                                        print(f"   Warning: Could not extract text from page {i+1}: {e}")
                                        writer.add_page(page)
                                
                                # If we didn't find a matching page, append the new slide
                                if not replaced:
                                    print(f"   Could not find old slide for '{company_name}', appending new slide...")
                                    for p in old_reader.pages:
                                        writer.add_page(p)
                                    for p in new_reader.pages:
                                        writer.add_page(p)
                            else:
                                # No existing slides for this page, just append
                                print("   Appending new slide(s) to existing PDF...")
                                writer = PdfWriter()
                                for p in old_reader.pages:
                                    writer.add_page(p)
                                for p in new_reader.pages:
                                    writer.add_page(p)
                            
                            merged_buf = io.BytesIO()
                            writer.write(merged_buf)
                            merged_buf.seek(0)
                            merged_bytes = merged_buf.read()
                            google_drive_link = drive.overwrite_pdf(target_file_id, merged_bytes)
                            results["google_drive_link"] = google_drive_link
                            if should_replace and replaced:
                                print(f"✓ Replaced existing slide in Drive PDF: {google_drive_link}")
                            else:
                                print(f"✓ Overwrote existing Drive PDF (DocSend-friendly): {google_drive_link}")
                        except Exception as e:
                            print(f"⚠️  Append/overwrite failed, uploading new file instead: {e}")
                            google_drive_link = drive.upload_pdf(
                                slide_pdf_bytes,
                                static_file_name or filename,
                                folder_id=Config.GOOGLE_DRIVE_FOLDER_ID
                            )
                            results["google_drive_link"] = google_drive_link
                            print(f"✓ Uploaded new Drive PDF (fallback): {google_drive_link}")
                except Exception as e:
                    print(f"Warning: Google Drive upload failed: {e}")
                    results["errors"].append(f"Google Drive: {str(e)}")
                
                # Step 8: Delete old Canva design if it exists
                if existing_slides and existing_canva_design_id:
                    try:
                        has_canva_creds = (
                            (Config.CANVA_API_KEY or (Config.CANVA_CLIENT_ID and Config.CANVA_CLIENT_SECRET))
                        )
                        if has_canva_creds:
                            print(f"🗑️  Deleting old Canva design: {existing_canva_design_id}")
                            canva = CanvaIntegration()
                            canva.delete_design(existing_canva_design_id)
                        else:
                            print("⚠️  Canva credentials not configured, skipping deletion")
                    except Exception as e:
                        print(f"⚠️  Error deleting old Canva design: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue anyway - we'll create new design
                
                # Step 9: Upload PDF to Canva as asset (required)
                canva_asset_id = None
                canva_design_id = None
                canva_design_url = None
                try:
                    has_canva_creds = (
                        (Config.CANVA_API_KEY or (Config.CANVA_CLIENT_ID and Config.CANVA_CLIENT_SECRET))
                        and Config.CANVA_TEMPLATE_ID
                    )
                    if has_canva_creds:
                        # Ensure filename is defined (should be from Step 7, but double-check)
                        if 'filename' not in locals():
                            filename = f"{company_data.get('name', 'slide').replace(' ', '_')}_slide.pdf"
                        
                        canva = CanvaIntegration()
                        
                        # Check if we should append to existing Canva design
                        static_canva_design_id = os.getenv("CANVA_STATIC_DESIGN_ID") or getattr(Config, "CANVA_STATIC_DESIGN_ID", None)
                        target_canva_design_id = None
                        
                        # Priority: static design ID > existing design from Notion
                        if static_canva_design_id:
                            target_canva_design_id = static_canva_design_id
                            print(f"   Using static Canva design ID: {target_canva_design_id}")
                        elif existing_slides and existing_canva_design_id:
                            target_canva_design_id = existing_canva_design_id
                            print(f"   Found existing Canva design ID: {target_canva_design_id}")
                        
                        if target_canva_design_id:
                            # Append to existing design
                            print("Appending slide to existing Canva design...")
                            try:
                                canva_asset_id = canva.append_slide_to_design(target_canva_design_id, slide_pdf_bytes, filename)
                                results["canva_asset_id"] = canva_asset_id
                                
                                # Check if it's a job ID (import job) or design ID
                                import re
                                is_job_id = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', canva_asset_id, re.IGNORECASE)
                                if is_job_id:
                                    # Wait for import completion and get design ID
                                    print("Waiting for Canva import to complete...")
                                    status_info = canva.wait_for_import_completion(canva_asset_id, max_wait_seconds=60, poll_interval=2)
                                    if status_info.get('status') == 'success':
                                        canva_design_id = status_info.get('design_id')
                                        canva_design_url = status_info.get('design_url')
                                        results["canva_design_id"] = canva_design_id
                                        results["canva_design_url"] = canva_design_url
                                        print(f"✓ Appended slide to Canva design: {canva_design_id}")
                                    else:
                                        print(f"⚠️  Canva import job did not complete successfully: {status_info.get('status')}")
                                else:
                                    # It's already a design ID
                                    canva_design_id = canva_asset_id
                                    results["canva_design_id"] = canva_design_id
                                    print(f"✓ Appended slide to Canva design: {canva_design_id}")
                            except Exception as e:
                                print(f"⚠️  Failed to append to existing design: {e}")
                                print("   Falling back to uploading as new design...")
                                # Fall through to new design upload
                                target_canva_design_id = None
                        
                        if not target_canva_design_id:
                            # Upload as new design
                            print("Uploading slide PDF to Canva as new design...")
                            canva_asset_id = canva.upload_pdf_asset(slide_pdf_bytes, filename)
                            results["canva_asset_id"] = canva_asset_id
                            
                            # Check if it's a job ID (import job) or asset ID
                            import re
                            is_job_id = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', canva_asset_id, re.IGNORECASE)
                            if is_job_id:
                                # Wait for import completion and get design ID
                                print("Waiting for Canva import to complete...")
                                status_info = canva.wait_for_import_completion(canva_asset_id, max_wait_seconds=60, poll_interval=2)
                                if status_info.get('status') == 'success':
                                    canva_design_id = status_info.get('design_id')
                                    canva_design_url = status_info.get('design_url')
                                    results["canva_design_id"] = canva_design_id
                                    results["canva_design_url"] = canva_design_url
                                    print(f"✓ Created new Canva design: {canva_design_id}")
                                else:
                                    print(f"⚠️  Canva import job did not complete successfully: {status_info.get('status')}")
                            else:
                                print(f"✓ Uploaded PDF to Canva assets: {canva_asset_id}")
                    else:
                        print("Warning: Canva credentials not configured, skipping PDF upload")
                        results["errors"].append("Canva PDF upload: Credentials not configured")
                except Exception as e:
                    print(f"Error: Canva PDF upload failed: {e}")
                    results["errors"].append(f"Canva PDF upload: {str(e)}")
                    # Don't fail the entire workflow, but log the error
                
                # Step 10: DocSend (optional - uses Google Drive sync)
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
                
                # Step 11: Update Notion record
                print("Updating Notion record...")
                if notion_page_id and Config.NOTION_API_KEY:
                    try:
                        notion = NotionIntegration()
                        notion.update_company_record(
                            page_id=notion_page_id,
                            google_drive_link=google_drive_link,
                            docsend_link=docsend_link,
                            canva_design_id=canva_design_id,
                            canva_design_url=canva_design_url,
                            status="completed"
                        )
                        if existing_slides:
                            print("✓ Notion record updated (replaced existing slides)")
                        else:
                            print("✓ Notion record updated (new slides created)")
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

