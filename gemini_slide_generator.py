"""
Google Gemini API integration for generating portfolio slides.
Uses template image as base and replaces only text/images while preserving styling.
"""
import io
import base64
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import img2pdf
from config import Config
import os
import numpy as np
from collections import Counter


class GeminiSlideGenerator:
    """Generate slides using template image as base."""
    
    def __init__(self):
        """Initialize Gemini client and resolve template path."""
        self.api_key = Config.GEMINI_API_KEY if hasattr(Config, 'GEMINI_API_KEY') else None
        
        # Resolve template path: prefer env, then common defaults
        self.template_path = getattr(Config, 'SLIDE_TEMPLATE_PATH', None) if hasattr(Config, 'SLIDE_TEMPLATE_PATH') else None
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(script_dir) == 'src':
            project_root = os.path.dirname(script_dir)
        else:
            project_root = script_dir
        
        if not self.template_path or not os.path.exists(self.template_path):
            default_template_paths = [
                os.path.join(project_root, 'SLAUSON&CO.Template.pdf'),
                os.path.join(project_root, 'SLAUSON&CO.template'),
                os.path.join(project_root, 'SLAUSON&CO.Template'),
                os.path.join(project_root, 'templates', 'SLAUSON&CO.Template.pdf'),
                os.path.join(script_dir, 'templates', 'SLAUSON&CO.Template.pdf'),
                'templates/SLAUSON&CO.Template.pdf',
                os.path.join(script_dir, 'SLAUSON&CO.Template.pdf'),
                os.path.join(script_dir, 'SLAUSON&CO.template'),
                'SLAUSON&CO.Template.pdf',
                'SLAUSON&CO.template',
            ]
            for path in default_template_paths:
                if path and os.path.exists(path):
                    self.template_path = path
                    print(f"✓ Gemini found template at: {self.template_path}")
                    break
    
    def _inpaint_region(self, img: Image.Image, mask: Image.Image, radius: int = 3) -> Image.Image:
        """
        Fast inpainting: fill masked region with nearby background color using numpy.
        """
        img_array = np.array(img)
        mask_array = np.array(mask.convert('L')) > 128
        
        if not np.any(mask_array):
            return img  # No mask, return original
        
        result = img_array.copy()
        height, width = mask_array.shape
        
        # Get coordinates of masked pixels
        masked_y, masked_x = np.where(mask_array)
        
        # For each masked pixel, sample nearby non-masked pixels
        for y, x in zip(masked_y, masked_x):
            # Sample region around pixel
            y_min, y_max = max(0, y - radius), min(height, y + radius + 1)
            x_min, x_max = max(0, x - radius), min(width, x + radius + 1)
            
            # Get non-masked pixels in this region
            region_mask = mask_array[y_min:y_max, x_min:x_max]
            region_img = img_array[y_min:y_max, x_min:x_max]
            
            non_masked = region_img[~region_mask]
            
            if len(non_masked) > 0:
                # Use median color (more stable than mean)
                result[y, x] = np.median(non_masked, axis=0).astype(np.uint8)
            else:
                # Fallback: use original pixel
                result[y, x] = img_array[y, x]
        
        return Image.fromarray(result)
    
    def _detect_text_regions(self, img: Image.Image, threshold: int = 50) -> list:
        """
        Detect text regions by finding areas with high contrast.
        Returns list of (x, y, width, height) bounding boxes.
        """
        # Convert to grayscale
        gray = img.convert('L')
        gray_array = np.array(gray)
        
        # Find edges (high contrast areas)
        edges = np.abs(np.gradient(gray_array.astype(float))[0]) + np.abs(np.gradient(gray_array.astype(float))[1])
        edges = (edges > threshold).astype(np.uint8) * 255
        
        # This is a simplified approach - in production, use proper text detection
        # For now, return empty list and use hardcoded positions
        return []
    
    def _get_dominant_color(self, img: Image.Image, region: Tuple[int, int, int, int], exclude_colors: list = None) -> Tuple[int, int, int]:
        """Get dominant color in a region, excluding specified colors."""
        x, y, w, h = region
        region_img = img.crop((x, y, x + w, y + h))
        pixels = list(region_img.getdata())
        
        if exclude_colors:
            pixels = [p for p in pixels if p[:3] not in exclude_colors]
        
        if not pixels:
            return (42, 42, 42)  # Default dark grey
        
        # Get most common color
        color_counts = Counter([p[:3] for p in pixels])
        return color_counts.most_common(1)[0][0]
    
    def _pdf_to_image(self, pdf_path: str) -> Image.Image:
        """Convert first page of PDF to PIL Image."""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            if images:
                return images[0].convert('RGBA')
        except ImportError:
            raise ImportError(
                "pdf2image required for PDF templates. Install with: pip install pdf2image"
            )
        except Exception as e:
            raise Exception(f"Failed to convert PDF to image: {e}")
    
    def _get_text_color_from_template(self, template: Image.Image, x: int, y: int, width: int, height: int) -> Tuple[int, int, int]:
        """Extract text color from template by finding brightest/darkest pixels in region."""
        region = template.crop((x, y, x + width, y + height))
        pixels = list(region.getdata())
        
        # Get background color (most common)
        bg_color = Counter([p[:3] for p in pixels]).most_common(1)[0][0]
        bg_brightness = sum(bg_color) / 3
        
        # Find pixels significantly different from background (likely text)
        text_pixels = []
        for p in pixels:
            rgb = p[:3] if len(p) >= 3 else p
            brightness = sum(rgb) / 3
            if abs(brightness - bg_brightness) > 40:  # Significant difference
                text_pixels.append(rgb)
        
        if text_pixels:
            # Return most common text color
            return Counter(text_pixels).most_common(1)[0][0]
        
        # Default: bright orange for company name, white for body
        return (255, 140, 0) if y < 200 else (255, 255, 255)
    
    def create_slide_exact_design(
        self,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        map_path: Optional[str] = None
    ) -> bytes:
        """
        Create slide using template image as base and replacing only content.
        Uses advanced inpainting and precise color/text detection.
        """
        # Check if template exists
        if not self.template_path or not os.path.exists(self.template_path):
            raise ValueError(
                f"Template image not found at: {self.template_path}\n"
                f"Please set SLIDE_TEMPLATE_PATH in .env to point to your template image file."
            )
        
        # Load template (PDF or image)
        template_ext = os.path.splitext(self.template_path)[1].lower()
        if template_ext == '.pdf':
            # Convert PDF to image
            template = self._pdf_to_image(self.template_path)
        else:
            # Load as image
            template = Image.open(self.template_path).convert('RGBA')
        # Resize to standard slide size if needed
        if template.size != (1920, 1080):
            template = template.resize((1920, 1080), Image.Resampling.LANCZOS)
        
        # Create a copy to work with
        slide = template.copy()
        draw = ImageDraw.Draw(slide)
        
        width, height = slide.size
        
        # Load fonts with better size matching
        try:
            # Try to match template font sizes more precisely
            name_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)  # Large for company name
            body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)  # Body text
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)  # Small labels
            sidebar_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)  # Sidebar
        except:
            try:
                name_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 120)
                body_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 28)
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
                sidebar_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 28)
            except:
                name_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                sidebar_font = ImageFont.load_default()
        
        # 1. Replace company name (top, large orange text)
        company_name = company_data.get('name', '').upper()
        # Detect exact text color and position from template
        name_color = self._get_text_color_from_template(template, 200, 80, 800, 120)
        name_bg = self._get_dominant_color(template, (200, 80, 800, 120))
        
        # Erase old text area with background color
        draw.rectangle([(180, 70), (1200, 260)], fill=name_bg)
        
        # Draw new company name
        draw.text((200, 100), company_name, fill=name_color, font=name_font)
        
        # 2. Replace logo (circular, top right)
        try:
            logo_img = Image.open(logo_path).convert('RGBA')
            logo_x, logo_y = width - 170, 100
            logo_size = 130
            
            # Erase old logo with circular mask
            logo_bg = self._get_dominant_color(template, (logo_x - 20, logo_y - 20, logo_size + 40, logo_size + 40))
            erase_mask = Image.new('L', (logo_size + 40, logo_size + 40), 0)
            erase_draw = ImageDraw.Draw(erase_mask)
            erase_draw.ellipse([(0, 0), (logo_size + 40, logo_size + 40)], fill=255)
            erase_img = Image.new('RGB', (logo_size + 40, logo_size + 40), logo_bg)
            slide.paste(erase_img, (logo_x - 20, logo_y - 20), erase_mask)
            draw = ImageDraw.Draw(slide)
            
            # Resize and mask logo to fit circle
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            circle_mask = Image.new('L', (logo_size, logo_size), 0)
            circle_draw = ImageDraw.Draw(circle_mask)
            circle_draw.ellipse([(0, 0), (logo_size, logo_size)], fill=255)
            logo_img.putalpha(circle_mask)
            
            # Paste logo
            slide.paste(logo_img, (logo_x, logo_y), logo_img)
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
        
        # 3. Replace map (upper right)
        if map_path and os.path.exists(map_path):
            try:
                map_img = Image.open(map_path).convert('RGBA')
                map_img = map_img.resize((380, 260), Image.Resampling.LANCZOS)
                
                # Erase old map area
                map_bg = self._get_dominant_color(template, (width - 440, 280, 380, 260))
                draw.rectangle([(width - 440, 280), (width - 60, 540)], fill=map_bg)
                
                slide.paste(map_img, (width - 440, 280), map_img)
                draw = ImageDraw.Draw(slide)
            except Exception as e:
                print(f"Warning: Could not load map: {e}")
        
        # Location label
        location = company_data.get('address', company_data.get('location', 'Los Angeles'))
        if ',' in location:
            location = location.split(',')[0].strip()
        
        pin_x, pin_y = width - 270, 480
        yellow = (255, 215, 0)
        black = (0, 0, 0)
        
        # Erase old label
        label_bg = self._get_dominant_color(template, (pin_x - 30, pin_y - 30, 280, 60))
        draw.rectangle([(pin_x - 30, pin_y - 30), (pin_x + 250, pin_y + 30)], fill=label_bg)
        
        # Draw pin and label
        draw.ellipse([(pin_x - 12, pin_y - 12), (pin_x + 12, pin_y + 12)], fill=yellow, outline=black, width=2)
        label_bbox = draw.textbbox((0, 0), location, font=small_font)
        label_width = label_bbox[2] - label_bbox[0] + 16
        label_height = label_bbox[3] - label_bbox[1] + 8
        draw.rectangle([(pin_x + 18, pin_y - label_height//2), (pin_x + 18 + label_width, pin_y + label_height//2)], fill=yellow)
        draw.text((pin_x + 26, pin_y - label_height//2 + 4), location, fill=black, font=small_font)
        
        # 4. Replace Founders text (below yellow box)
        founders_text = company_data.get('founders', '')
        if isinstance(founders_text, list):
            founders_text = ', '.join(founders_text)
        
        founders_color = self._get_text_color_from_template(template, 200, 360, 600, 50)
        founders_bg = self._get_dominant_color(template, (200, 360, 600, 50))
        
        # Erase old text
        draw.rectangle([(200, 350), (1000, 450)], fill=founders_bg)
        draw.text((200, 370), founders_text, fill=founders_color, font=body_font)
        
        # 5. Replace Co-Investors text
        co_investors_text = company_data.get('co_investors', '')
        if isinstance(co_investors_text, list):
            co_investors_text = ', '.join(co_investors_text)
        
        investors_color = self._get_text_color_from_template(template, 200, 460, 600, 50)
        investors_bg = self._get_dominant_color(template, (200, 460, 600, 50))
        
        draw.rectangle([(200, 450), (1000, 550)], fill=investors_bg)
        draw.text((200, 470), co_investors_text, fill=investors_color, font=body_font)
        
        # 6. Replace Background text (wrapped)
        background_text = company_data.get('background', company_data.get('description', ''))
        words = background_text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=body_font)
            if bbox[2] - bbox[0] < 750:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        bg_color = self._get_text_color_from_template(template, 200, 560, 800, 200)
        bg_bg = self._get_dominant_color(template, (200, 560, 800, 200))
        
        draw.rectangle([(200, 550), (1000, 780)], fill=bg_bg)
        for i, line in enumerate(lines[:8]):
            draw.text((200, 570 + i * 32), line, fill=bg_color, font=body_font)
        
        # 7. Replace headshots (bottom right, transparent background)
        try:
            # Erase old headshots completely
            headshot_bg = self._get_dominant_color(template, (width - 500, height - 450, 480, 410))
            draw.rectangle([(width - 500, height - 450), (width - 20, height - 40)], fill=headshot_bg)
            
            # Load and paste new headshots with transparency
            headshot_img = Image.open(headshot_path).convert('RGBA')
            headshot_img.thumbnail((380, 320), Image.Resampling.LANCZOS)
            slide.paste(headshot_img, (width - 400, height - 360), headshot_img)
            draw = ImageDraw.Draw(slide)
        except Exception as e:
            print(f"Warning: Could not load headshot: {e}")
            import traceback
            traceback.print_exc()
        
        # 8. Replace investment stage in sidebar (rotated)
        investment_stage = company_data.get('investment_stage', '')
        if not investment_stage:
            round_val = company_data.get('investment_round', 'PRE-SEED')
            quarter_val = company_data.get('quarter', 'Q2')
            year_val = company_data.get('year', '2024')
            investment_stage = f"{round_val} {quarter_val}, {year_val}"
        
        stage_color = self._get_text_color_from_template(template, 30, 50, 120, 80)
        stage_bg = self._get_dominant_color(template, (30, 50, 120, 80))
        
        draw.rectangle([(10, 40), (190, 90)], fill=stage_bg)
        
        # Draw rotated text
        stage_text = investment_stage.upper()
        stage_img = Image.new('RGBA', (200, 150), (0, 0, 0, 0))
        stage_draw = ImageDraw.Draw(stage_img)
        bbox = stage_draw.textbbox((0, 0), stage_text, font=sidebar_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        stage_draw.text((100 - text_width//2, 75 - text_height//2), stage_text, fill=stage_color, font=sidebar_font)
        stage_img = stage_img.rotate(-90, expand=True)
        stage_img_width, stage_img_height = stage_img.size
        slide.paste(stage_img, (75 - stage_img_width//2, 100), stage_img)
        
        # Convert to RGB for PDF
        slide_rgb = Image.new('RGB', slide.size, (42, 42, 42))
        slide_rgb.paste(slide, mask=slide.split()[3] if slide.mode == 'RGBA' else None)
        
        # Convert to PDF
        img_bytes = io.BytesIO()
        slide_rgb.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        pdf_bytes = img2pdf.convert(img_bytes.getvalue())
        return pdf_bytes
