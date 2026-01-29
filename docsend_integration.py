"""
DocSend API integration for portfolio deck management.
"""
import requests
from typing import Optional, BinaryIO
from config import Config


class DocSendIntegration:
    """Handle DocSend API operations."""
    
    def __init__(self):
        """Initialize DocSend client."""
        self.api_key = Config.DOCSEND_API_KEY
        self.base_url = "https://api.docsend.com"
        self.individual_deck_id = Config.DOCSEND_INDIVIDUAL_DECK_ID
        self.master_deck_id = Config.DOCSEND_MASTER_DECK_ID
    
    def upload_individual_slide(self, pdf_bytes: bytes, company_name: str) -> str:
        """
        Upload individual company slide to DocSend.
        
        Args:
            pdf_bytes: PDF bytes of the company slide
            company_name: Name of the company
            
        Returns:
            DocSend document link
        """
        if not self.api_key:
            raise ValueError("DOCSEND_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        files = {
            "file": (f"{company_name}_slide.pdf", pdf_bytes, "application/pdf")
        }
        
        data = {
            "name": f"{company_name} Portfolio Slide"
        }
        
        response = requests.post(
            f"{self.base_url}/documents",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 201:
            return response.json().get("link", "")
        else:
            # Check if response is HTML (login page) - means API key is invalid
            if response.headers.get('content-type', '').startswith('text/html'):
                raise Exception(f"DocSend API authentication failed - check your API key. Status: {response.status_code}")
            raise Exception(f"DocSend upload error: {response.status_code} - {response.text[:200]}")
    
    def update_master_presentation(self, pdf_bytes: bytes) -> str:
        """
        Update master portfolio presentation with new slide.
        
        Args:
            pdf_bytes: Complete PDF bytes of updated presentation
            
        Returns:
            Updated document link (should be same as before)
        """
        if not self.api_key or not self.master_deck_id:
            raise ValueError("DocSend configuration incomplete")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        files = {
            "file": ("portfolio_master.pdf", pdf_bytes, "application/pdf")
        }
        
        # Upload new version to existing document
        response = requests.put(
            f"{self.base_url}/documents/{self.master_deck_id}",
            headers=headers,
            files=files
        )
        
        if response.status_code in [200, 201]:
            # Some auth failures return HTML with a 200 status
            if response.headers.get('content-type', '').startswith('text/html'):
                raise Exception("DocSend API authentication failed - check your API key. Status: 200")
            return response.json().get("link", "")
        else:
            # Check if response is HTML (login page) - means API key is invalid
            if response.headers.get('content-type', '').startswith('text/html'):
                raise Exception(f"DocSend API authentication failed - check your API key. Status: {response.status_code}")
            raise Exception(f"DocSend update error: {response.status_code} - {response.text}")
    
    def merge_pdfs(self, existing_pdf_bytes: bytes, new_slide_bytes: bytes) -> bytes:
        """
        Merge existing presentation with new slide.
        
        Args:
            existing_pdf_bytes: Bytes of existing master presentation
            new_slide_bytes: Bytes of new company slide
            
        Returns:
            Merged PDF bytes
        """
        try:
            from PyPDF2 import PdfWriter, PdfReader
            import io
            
            writer = PdfWriter()
            
            # Add existing pages
            existing_reader = PdfReader(io.BytesIO(existing_pdf_bytes))
            for page in existing_reader.pages:
                writer.add_page(page)
            
            # Add new slide
            new_reader = PdfReader(io.BytesIO(new_slide_bytes))
            for page in new_reader.pages:
                writer.add_page(page)
            
            # Write merged PDF
            output = io.BytesIO()
            writer.write(output)
            return output.getvalue()
            
        except ImportError:
            raise ImportError("PyPDF2 required for PDF merging. Install with: pip install PyPDF2")

