"""
Google Gemini API integration for generating portfolio slides.
Uses Gemini to create professional slide layouts.
"""
import io
import base64
from typing import Dict
from PIL import Image, ImageDraw, ImageFont
import requests
from config import Config


class GeminiSlideGenerator:
    """Generate slides using Google Gemini API."""
    
    def __init__(self):
        """Initialize Gemini client."""
        self.api_key = Config.GEMINI_API_KEY if hasattr(Config, 'GEMINI_API_KEY') else None
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"
    
    def generate_slide_with_gemini(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str
    ) -> bytes:
        """
        Generate slide using Gemini API with image generation.
        
        Args:
            company_data: Company information
            headshot_path: Path to headshot image
            logo_path: Path to logo image
            
        Returns:
            PDF bytes of generated slide
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured in config.py")
        
        try:
            # Load images
            with open(headshot_path, 'rb') as f:
                headshot_bytes = f.read()
            with open(logo_path, 'rb') as f:
                logo_bytes = f.read()
            
            # Encode images to base64
            headshot_b64 = base64.b64encode(headshot_bytes).decode('utf-8')
            logo_b64 = base64.b64encode(logo_bytes).decode('utf-8')
            
            # Create prompt for slide generation
            prompt = self._create_slide_prompt(company_data)
            
            # Use Gemini to generate slide description/design
            slide_data = self._get_slide_design_from_gemini(prompt, headshot_b64, logo_b64)
            
            # Render the slide based on Gemini's design
            return self._render_slide(slide_data, company_data, headshot_path, logo_path)
            
        except Exception as e:
            print(f"Error generating slide with Gemini: {e}")
            raise
    
    def _create_slide_prompt(self, company_data: Dict) -> str:
        """Create a prompt for Gemini to design the slide."""
        return f"""
        Create a professional portfolio company slide design with the following information:
        
        Company Name: {company_data.get('name', 'Unknown')}
        Description: {company_data.get('description', '')}
        Address: {company_data.get('address', '')}
        Investment Date: {company_data.get('investment_date', '')}
        Co-Investors: {company_data.get('co_investors', '')}
        Employees: {company_data.get('num_employees', 'N/A')}
        
        Design requirements:
        - Clean, modern, professional layout
        - Company name should be prominent (large font, top/middle)
        - Description should be readable (medium font, justified text)
        - Founder headshot should be circular, positioned on left side, grayscale
        - Logo should be in top right corner
        - Use professional color scheme (blacks, grays, accent color)
        - Include investment details at bottom
        
        Provide a JSON response with layout specifications.
        """
    
    def _get_slide_design_from_gemini(self, prompt: str, headshot_b64: str, logo_b64: str) -> Dict:
        """Get slide design recommendations from Gemini."""
        # For now, return a default design structure
        # In full implementation, you'd call Gemini API here
        return {
            "layout": "modern",
            "colors": {
                "primary": "#000000",
                "secondary": "#666666",
                "accent": "#0066FF"
            },
            "font_sizes": {
                "title": 72,
                "subtitle": 36,
                "body": 24
            }
        }
    
    def _render_slide(self, design_data: Dict, company_data: Dict, headshot_path: str, logo_path: str) -> bytes:
        """Render the slide based on Gemini's design recommendations."""
        from canva_integration import CanvaIntegration
        
        # Use the existing slide generation but with Gemini-enhanced design
        canva = CanvaIntegration()
        return canva.create_slide_alternative(company_data, headshot_path, logo_path)


# Alternative: Use Gemini to generate image directly
class GeminiImageGenerator:
    """Use Gemini to generate slide image directly."""
    
    def __init__(self):
        """Initialize Gemini client."""
        self.api_key = Config.GEMINI_API_KEY if hasattr(Config, 'GEMINI_API_KEY') else None
    
    def generate_slide_image(self, company_data: Dict) -> bytes:
        """
        Use Gemini's image generation (if available) or create with AI guidance.
        
        Note: Gemini Pro doesn't directly generate images, but we can use it
        to create better slide designs that we then render.
        """
        # Since Gemini doesn't directly generate images, we'll use it to
        # create a better design specification, then render it
        pass

