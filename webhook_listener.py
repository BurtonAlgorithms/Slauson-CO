"""
Webhook listener for form submissions.
Can be used with Zapier, Make.com, or as a standalone Flask server.
"""
from flask import Flask, request, jsonify
from main import PortfolioOnboardingAutomation
import os
import tempfile
import base64
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
        if data and "company_data" in data:
            company_data = data["company_data"]
            print(f"Company data keys: {list(company_data.keys()) if isinstance(company_data, dict) else 'Not a dict'}")
            if isinstance(company_data, dict):
                print(f"Company name: {company_data.get('name', 'N/A')}")
        print(f"{'='*60}\n")
        
        if not data or "company_data" not in data:
            return jsonify({"error": "Missing company_data"}), 400
        
        company_data = data["company_data"]
        
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
            
            # Process onboarding (Notion is optional since Zapier handles it)
            automation = PortfolioOnboardingAutomation(require_notion=False)
            results = automation.process_onboarding(
                company_data,
                headshot_path,
                logo_path
            )
            
            # Add PDF as base64 in response for download
            if results.get("canva_slide_path") and os.path.exists(results["canva_slide_path"]):
                # Read PDF and encode as base64 for download
                with open(results["canva_slide_path"], 'rb') as f:
                    pdf_bytes = f.read()
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    results["pdf_base64"] = pdf_base64
                    results["pdf_filename"] = f"{company_data.get('name', 'slide').replace(' ', '_')}_slide.pdf"
                    results["pdf_path"] = results["canva_slide_path"]
            
            # Include Notion metadata in response for reference
            if notion_metadata.get("page_id"):
                results["notion_metadata"] = notion_metadata
            
            print(f"\n{'='*60}")
            print(f"Processing complete. Success: {results.get('success')}")
            if results.get('errors'):
                print(f"Errors: {results['errors']}")
            print(f"{'='*60}\n")
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

