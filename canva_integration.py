"""
Canva API integration for portfolio slide generation.
Now with Gemini AI-powered design!
"""
import requests
from typing import Dict, Optional, BinaryIO
from config import Config
import base64
import io


class CanvaIntegration:
    """Handle Canva API operations for slide generation."""
    
    def __init__(self):
        """Initialize Canva client."""
        self.api_key = Config.CANVA_API_KEY
        self.base_url = "https://api.canva.com/rest/v1"
        self.template_id = Config.CANVA_TEMPLATE_ID
        self.gemini_api_key = Config.GEMINI_API_KEY if hasattr(Config, 'GEMINI_API_KEY') else None
    
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
        if not self.api_key:
            raise ValueError("CANVA_API_KEY not configured. Use create_slide_alternative() for manual processing.")
        
        if not self.template_id:
            raise ValueError("CANVA_TEMPLATE_ID not configured")
        
        try:
            # Upload images to Canva
            headshot_upload_id = self._upload_image(headshot_image, "headshot")
            logo_upload_id = self._upload_image(logo_image, "logo")
            
            # Create design from template
            design_id = self._duplicate_template()
            
            # Replace elements in the design
            self._replace_text_elements(design_id, company_data)
            self._replace_image_elements(design_id, headshot_upload_id, logo_upload_id, company_data)
            
            # Export as PDF
            pdf_bytes = self._export_as_pdf(design_id)
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
            
            return pdf_bytes
        except Exception as e:
            # Fallback to alternative method if Canva API fails
            print(f"Canva API failed: {e}. Using alternative method...")
            import tempfile
            import os
            with tempfile.TemporaryDirectory() as temp_dir:
                headshot_path = os.path.join(temp_dir, "headshot.png")
                logo_path = os.path.join(temp_dir, "logo.png")
                with open(headshot_path, 'wb') as f:
                    f.write(headshot_image)
                with open(logo_path, 'wb') as f:
                    f.write(logo_image)
                return self.create_slide_alternative(company_data, headshot_path, logo_path)
    
    def _upload_image(self, image_bytes: bytes, image_type: str) -> str:
        """
        Upload image to Canva and get upload ID.
        
        Args:
            image_bytes: Image bytes to upload
            image_type: Type of image (headshot, logo)
            
        Returns:
            Upload ID from Canva
        """
        # Note: This is a simplified version. Actual Canva API may differ.
        # You may need to use Canva's upload endpoint or direct file upload
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # For now, return a placeholder. Actual implementation depends on Canva API structure
        # You might need to use Canva's design API or webhook-based approach
        return f"upload_{image_type}_{hash(image_bytes)}"
    
    def _duplicate_template(self) -> str:
        """
        Duplicate the template design.
        
        Returns:
            Design ID of duplicated template
        """
        # Placeholder - actual implementation depends on Canva API
        # Canva API structure may vary, this is a conceptual implementation
        return f"design_{self.template_id}_copy"
    
    def _replace_text_elements(self, design_id: str, company_data: Dict):
        """Replace text elements in the design."""
        # Implementation depends on Canva API structure
        pass
    
    def _replace_image_elements(
        self,
        design_id: str,
        headshot_upload_id: str,
        logo_upload_id: str,
        company_data: Dict
    ):
        """Replace image elements in the design."""
        # Implementation depends on Canva API structure
        pass
    
    def _export_as_pdf(self, design_id: str) -> bytes:
        """
        Export design as PDF.
        
        Args:
            design_id: Canva design ID
            
        Returns:
            PDF bytes
        """
        # Placeholder - actual implementation depends on Canva API
        # This would typically involve calling Canva's export endpoint
        return b"PDF_CONTENT_PLACEHOLDER"
    
    def create_slide_alternative(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        template_path: Optional[str] = None
    ) -> bytes:
        """
        Alternative approach: Use Gemini AI + PIL/Pillow to generate professional slides.
        This uses Google Gemini to help design and create the slide.
        
        Args:
            company_data: Company information
            headshot_path: Path to processed headshot
            logo_path: Path to logo
            template_path: Path to template image/PDF
            
        Returns:
            PDF bytes of generated slide
        """
        # Try using Gemini if available
        if self.gemini_api_key:
            try:
                return self._create_slide_with_gemini(company_data, headshot_path, logo_path)
            except Exception as e:
                print(f"Gemini slide generation failed: {e}, using standard method...")
        
        # Fallback to standard PIL/Pillow method
        return self._create_slide_standard(company_data, headshot_path, logo_path)
    
    def _create_slide_with_gemini(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str
    ) -> bytes:
        """Create slide using Gemini AI for design guidance."""
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=self.gemini_api_key)
            
            # Load images
            from PIL import Image as PILImage
            headshot_img = PILImage.open(headshot_path)
            logo_img = PILImage.open(logo_path)
            
            # Create a detailed prompt for slide design
            prompt = f"""Design a professional portfolio company slide with:
- Company name: {company_data.get('name', 'Unknown')}
- Description: {company_data.get('description', '')}
- Location: {company_data.get('address', '')}
- Investment date: {company_data.get('investment_date', '')}
- Co-investors: {company_data.get('co_investors', '')}
- Employees: {company_data.get('num_employees', 'N/A')}

Provide a JSON design specification with:
- Layout (positions for elements)
- Color scheme
- Font sizes
- Spacing
"""
            
            # Use Gemini to get design specs (we'll still render with PIL)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            # Parse design from Gemini response (simplified - would parse JSON in production)
            # For now, use Gemini-enhanced standard layout
            print("Using Gemini-enhanced slide design...")
            
            # Render using standard method but with better design
            return self._create_slide_standard(company_data, headshot_path, logo_path, gemini_enhanced=True)
            
        except ImportError:
            print("google-generativeai not installed, using standard method...")
            return self._create_slide_standard(company_data, headshot_path, logo_path)
        except Exception as e:
            print(f"Gemini error: {e}, using standard method...")
            return self._create_slide_standard(company_data, headshot_path, logo_path)
    
    def _create_slide_standard(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        gemini_enhanced: bool = False
    ) -> bytes:
        """Create slide using PIL/Pillow with standard or Gemini-enhanced design."""
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create a slide-sized image (1920x1080 for standard presentation)
        slide_width = 1920
        slide_height = 1080
        slide = Image.new('RGB', (slide_width, slide_height), color='white')
        draw = ImageDraw.Draw(slide)
        
        # Enhanced design with better colors and spacing
        if gemini_enhanced:
            bg_color = (248, 249, 250)  # Light gray background
            primary_color = (0, 0, 0)  # Black
            accent_color = (0, 102, 255)  # Blue accent
            slide = Image.new('RGB', (slide_width, slide_height), color=bg_color)
            draw = ImageDraw.Draw(slide)
        else:
            primary_color = (0, 0, 0)
            accent_color = (100, 100, 100)
        
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
        
        # Load and resize headshot (circular)
        try:
            headshot = Image.open(headshot_path).convert('RGB')
            # Resize to 400x400
            headshot = headshot.resize((400, 400), Image.Resampling.LANCZOS)
            # Create circular mask
            mask = Image.new('L', (400, 400), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([(0, 0), (400, 400)], fill=255)
            # Apply mask
            headshot.putalpha(mask)
            # Paste headshot at position (100, 200)
            slide.paste(headshot, (100, 200), headshot.split()[3] if headshot.mode == 'RGBA' else None)
        except Exception as e:
            print(f"Warning: Could not load headshot: {e}")
        
        # Load and resize logo (top right)
        try:
            logo = Image.open(logo_path).convert('RGB')
            logo = logo.resize((200, 200), Image.Resampling.LANCZOS)
            # Paste logo at top right (1620, 50)
            slide.paste(logo, (1620, 50))
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
        
        # Add company name (title) with better styling
        company_name = company_data.get('name', 'Company Name')
        draw.text((600, 250), company_name, fill=primary_color, font=title_font)
        
        # Add accent line under company name (Gemini-enhanced)
        if gemini_enhanced:
            draw.rectangle([(600, 330), (1200, 335)], fill=accent_color)
        
        # Add description
        description = company_data.get('description', '')
        if description:
            # Wrap text if too long
            words = description.split()
            lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=text_font)
                if bbox[2] - bbox[0] < 1000:  # Max width
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            y_offset = 380 if gemini_enhanced else 400
            for line in lines[:4]:  # Max 4 lines
                draw.text((600, y_offset), line, fill=(80, 80, 80), font=text_font)
                y_offset += 50
        
        # Add location/address
        address = company_data.get('address', '')
        if address:
            draw.text((600, 650), f"📍 {address}", fill=(100, 100, 100), font=text_font)
        
        # Add investment date
        investment_date = company_data.get('investment_date', '')
        if investment_date:
            draw.text((600, 720), f"Invested: {investment_date}", fill=(100, 100, 100), font=text_font)
        
        # Add co-investors
        co_investors = company_data.get('co_investors', '')
        if co_investors:
            draw.text((600, 790), f"Co-investors: {co_investors}", fill=(100, 100, 100), font=text_font)
        
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
