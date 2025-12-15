"""
PDF/Image template-based slide generator.
Uses Canva PDF or image template and overlays text/images using PIL.
Supports both PDF and image templates (JPG, PNG, etc.)
"""
import os
from typing import Dict, Optional
import io
from PIL import Image, ImageDraw, ImageFont
import hashlib
import img2pdf
from collections import Counter
import numpy as np

# Fix for reportlab compatibility
try:
    hashlib.md5(b'test', usedforsecurity=False)
except TypeError:
    _original_md5 = hashlib.md5
    def _patched_md5(data=None, usedforsecurity=True):
        return _original_md5(data) if data is not None else _original_md5()
    hashlib.md5 = _patched_md5

class HTMLSlideGenerator:
    def __init__(self):
        from config import Config
        
        # Get the directory where this script is located (works on Render too)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # On Render: script_dir = /opt/render/project/src, project_root = /opt/render/project
        # Locally: script_dir = /path/to/slauson-automation, project_root = /path/to/slauson-automation
        # Check if we're in a 'src' subdirectory (Render) or directly in project root
        if os.path.basename(script_dir) == 'src':
            project_root = os.path.dirname(script_dir)
        else:
            project_root = script_dir
        
        print(f"DEBUG: script_dir={script_dir}, project_root={project_root}")
        
        # Slide template path - check config first, then try default locations
        self.template_path = getattr(Config, 'SLIDE_TEMPLATE_PATH', None) if hasattr(Config, 'SLIDE_TEMPLATE_PATH') else None
        if not self.template_path or not os.path.exists(self.template_path):
            # Try default locations (project root first, then templates folder, then script dir)
            default_template_paths = [
                # Project root (where user added the file)
                os.path.join(project_root, 'SLAUSON&CO.Template.pdf'),
                os.path.join(project_root, 'SLAUSON&CO.template'),
                os.path.join(project_root, 'SLAUSON&CO.Template'),
                # Templates folder
                os.path.join(project_root, 'templates', 'SLAUSON&CO.Template.pdf'),
                os.path.join(script_dir, 'templates', 'SLAUSON&CO.Template.pdf'),
                'templates/SLAUSON&CO.Template.pdf',
                # Script directory
                os.path.join(script_dir, 'SLAUSON&CO.Template.pdf'),
                os.path.join(script_dir, 'SLAUSON&CO.template'),
                # Current working directory
                'SLAUSON&CO.Template.pdf',
                'SLAUSON&CO.template',
                # Generic template names
                os.path.join(project_root, 'templates', 'template.pdf'),
                os.path.join(script_dir, 'templates', 'template.pdf'),
                'templates/template.pdf',
                'templates/template.png',
                'templates/template.jpg',
            ]
            print(f"DEBUG: Checking {len(default_template_paths)} template paths...")
            for path in default_template_paths:
                if path and os.path.exists(path):
                    self.template_path = path
                    print(f"✓ Found template at: {self.template_path}")
                    break
                else:
                    print(f"  - Not found: {path}")
        
        # Map template path - check config first, then try default locations
        self.map_template_path = getattr(Config, 'MAP_TEMPLATE_PATH', None) if hasattr(Config, 'MAP_TEMPLATE_PATH') else None
        if not self.map_template_path or not os.path.exists(self.map_template_path):
            # Try default locations (relative to script, then project root, then current working directory)
            default_map_paths = [
                os.path.join(script_dir, 'templates', 'map_template.pdf'),
                os.path.join(project_root, 'templates', 'map_template.pdf'),
                'templates/map_template.pdf',
                os.path.join(script_dir, 'templates', 'SLAUSON&CO. (1).pdf'),
                os.path.join(project_root, 'templates', 'SLAUSON&CO. (1).pdf'),
                'templates/SLAUSON&CO. (1).pdf',
            ]
            for path in default_map_paths:
                if path and os.path.exists(path):
                    self.map_template_path = path
                    print(f"✓ Found map template at: {self.map_template_path}")
                    break

    def _load_font(self, size: int, bold: bool = False):
        """
        Load a font with robust fallbacks that work on Render.
        Tries common system fonts, then DejaVu (available in most containers), then default.
        """
        font_candidates = []
        # Preferred bundled fonts on Linux containers (Render uses these)
        if bold:
            font_candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
            font_candidates.append("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
        font_candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        font_candidates.append("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
        # Try to find fonts via fontconfig (common on Linux)
        try:
            import subprocess
            result = subprocess.run(['fc-list'], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                # Look for DejaVu or Liberation in font list
                for line in result.stdout.split('\n'):
                    if 'DejaVu' in line or 'Liberation' in line:
                        font_path = line.split(':')[0] if ':' in line else None
                        if font_path and os.path.exists(font_path):
                            if bold and 'Bold' in font_path:
                                font_candidates.insert(0, font_path)
                            elif not bold and 'Bold' not in font_path:
                                font_candidates.insert(0, font_path)
        except Exception:
            pass  # Fontconfig not available, continue with hardcoded paths
        
        # macOS fonts (for local development only)
        if bold:
            font_candidates.append("/System/Library/Fonts/Helvetica-Bold.ttf")
            font_candidates.append("/System/Library/Fonts/Arial Bold.ttf")
        font_candidates.append("/System/Library/Fonts/Helvetica.ttc")
        font_candidates.append("/System/Library/Fonts/Arial.ttf")

        for path in font_candidates:
            try:
                if os.path.exists(path) or not os.path.isabs(path):
                    # Only check existence for absolute paths
                    return ImageFont.truetype(path, size)
            except (OSError, IOError, Exception) as e:
                # Silently continue to next candidate
                continue
        
        # Final fallback - always works
        print(f"Warning: Could not load custom font, using default font for size {size}")
        return ImageFont.load_default()
    
    def _pdf_to_image(self, pdf_path: str) -> Image.Image:
        """Convert first page of PDF to PIL Image."""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            if images:
                return images[0].convert('RGBA')
        except ImportError:
            # Fallback: try PyPDF2 + extract images
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(pdf_path)
                page = reader.pages[0]
                # Try to extract images from PDF
                if '/XObject' in page['/Resources']:
                    xObject = page['/Resources']['/XObject'].get_object()
                    for obj in xObject:
                        if xObject[obj]['/Subtype'] == '/Image':
                            # Extract image data
                            data = xObject[obj].get_data()
                            img = Image.open(io.BytesIO(data))
                            return img.convert('RGBA')
                # If no images found, render PDF as image using alternative method
                raise ImportError("pdf2image required for PDF templates")
            except Exception as e:
                raise ImportError(
                    f"Could not convert PDF to image. Please install pdf2image: pip install pdf2image. "
                    f"Error: {e}"
                )
        except Exception as e:
            raise Exception(f"Failed to convert PDF to image: {e}")
    
    def _get_dominant_color(self, img: Image.Image, region: tuple, exclude_colors: list = None) -> tuple:
        """Get dominant color in a region."""
        x, y, w, h = region
        region_img = img.crop((x, y, x + w, y + h))
        pixels = list(region_img.getdata())
        
        if exclude_colors:
            pixels = [p for p in pixels if p[:3] not in exclude_colors]
        
        if not pixels:
            return (42, 42, 42)  # Default dark grey
        
        color_counts = Counter([p[:3] for p in pixels])
        return color_counts.most_common(1)[0][0]
    
    def _get_text_color_from_template(self, template: Image.Image, x: int, y: int, width: int, height: int) -> tuple:
        """Extract text color from template."""
        region = template.crop((x, y, x + width, y + height))
        pixels = list(region.getdata())
        
        bg_color = Counter([p[:3] for p in pixels]).most_common(1)[0][0]
        bg_brightness = sum(bg_color) / 3
        
        text_pixels = []
        for p in pixels:
            rgb = p[:3] if len(p) >= 3 else p
            brightness = sum(rgb) / 3
            if abs(brightness - bg_brightness) > 40:
                text_pixels.append(rgb)
        
        if text_pixels:
            return Counter(text_pixels).most_common(1)[0][0]
        
        return (255, 140, 0) if y < 200 else (255, 255, 255)
    
    def _get_city_coordinates(self, city_name: str) -> tuple:
        """
        Get normalized coordinates (0-1) for US cities on a map.
        Returns (x, y) where x is 0 (west) to 1 (east), y is 0 (north) to 1 (south).
        """
        # Normalize city name
        city_lower = city_name.lower().split(',')[0].strip()
        
        # Approximate US city positions (normalized coordinates) - Updated for accurate map projection
        city_positions = {
            # West Coast
            'san francisco': (0.05, 0.42),  # Updated: West Coast, California
            'los angeles': (0.09, 0.62),   # Updated: West Coast, California
            'san diego': (0.10, 0.70),
            'seattle': (0.08, 0.20),
            'portland': (0.09, 0.25),
            # East Coast
            'new york': (0.92, 0.35),      # Updated: East Coast
            'boston': (0.95, 0.30),
            'philadelphia': (0.90, 0.38),
            'washington': (0.88, 0.40),
            'miami': (0.93, 0.80),
            'atlanta': (0.80, 0.60),
            # Central
            'chicago': (0.65, 0.35),
            'dallas': (0.48, 0.72),        # Updated: Texas
            'houston': (0.50, 0.75),
            'austin': (0.48, 0.72),        # Updated: Texas
            'denver': (0.40, 0.45),
            'phoenix': (0.25, 0.65),
            'las vegas': (0.20, 0.55),
            'detroit': (0.70, 0.32),
            'minneapolis': (0.55, 0.25),
            # Other major cities
            'san jose': (0.06, 0.44),
            'oakland': (0.05, 0.43),
            'sacramento': (0.07, 0.40),
        }
        
        # Try exact match first
        if city_lower in city_positions:
            return city_positions[city_lower]
        
        # Try partial matches
        for city, coords in city_positions.items():
            if city in city_lower or city_lower in city:
                return coords
        
        # Default to center of US
        return (0.50, 0.50)

    def create_slide(self, company_data: Dict, headshot_path: str, logo_path: str, map_path: Optional[str] = None) -> bytes:
        # Check if template exists, try default locations if not found
        if not self.template_path or not os.path.exists(self.template_path):
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir) if os.path.basename(script_dir) in ['src', 'slauson-automation'] else script_dir
            
            # Try to find template in common locations (project root first)
            possible_paths = [
                # Project root (where user added the file)
                os.path.join(project_root, 'SLAUSON&CO.Template.pdf'),
                os.path.join(project_root, 'SLAUSON&CO.template'),
                os.path.join(project_root, 'SLAUSON&CO.Template'),
                # Templates folder
                os.path.join(project_root, 'templates', 'SLAUSON&CO.Template.pdf'),
                os.path.join(script_dir, 'templates', 'SLAUSON&CO.Template.pdf'),
                'templates/SLAUSON&CO.Template.pdf',
                # Script directory
                os.path.join(script_dir, 'SLAUSON&CO.Template.pdf'),
                os.path.join(script_dir, 'SLAUSON&CO.template'),
                # Current working directory
                'SLAUSON&CO.Template.pdf',
                'SLAUSON&CO.template',
                # Generic template names
                os.path.join(project_root, 'templates', 'template.pdf'),
                os.path.join(script_dir, 'templates', 'template.pdf'),
                'templates/template.pdf',
                'templates/template.png',
                'templates/template.jpg',
            ]
            found_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    found_path = path
                    print(f"✓ Found template at: {found_path}")
                    break
            
            if not found_path:
                raise ValueError(
                    f"Template not found. Tried: {self.template_path}\n"
                    f"Please set SLIDE_TEMPLATE_PATH in .env or place template at project root: SLAUSON&CO.Template.pdf\n"
                    f"Script dir: {script_dir}, Project root: {project_root}\n"
                    f"Checked paths: {possible_paths[:5]}..."
                )
            self.template_path = found_path
        
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
        
        # Load fonts (robust fallbacks for Render)
        name_font = self._load_font(140, bold=True)
        body_font = self._load_font(28)
        small_font = self._load_font(20)
        sidebar_font = self._load_font(28)
        
        # Extract company data
        company_name = company_data.get('name', '').upper()
        founders_text = company_data.get('founders', '')
        if isinstance(founders_text, list):
            founders_text = '\n'.join(founders_text)  # Use newlines instead of commas
        elif isinstance(founders_text, str) and ',' in founders_text:
            # Convert comma-separated to newline-separated
            founders_text = '\n'.join([f.strip() for f in founders_text.split(',')])
        
        co_investors_text = company_data.get('co_investors', '')
        if isinstance(co_investors_text, list):
            co_investors_text = '\n'.join(co_investors_text)  # Use newlines instead of commas
        elif isinstance(co_investors_text, str) and ',' in co_investors_text:
            # Convert comma-separated to newline-separated
            co_investors_text = '\n'.join([f.strip() for f in co_investors_text.split(',')])
        
        background_text = company_data.get('background', company_data.get('description', ''))
        location = company_data.get('address', company_data.get('location', 'Los Angeles'))
        if ',' in location:
            location = location.split(',')[0].strip()
        
        investment_stage = company_data.get('investment_stage', '')
        if not investment_stage:
            round_val = company_data.get('investment_round', 'PRE-SEED')
            quarter_val = company_data.get('quarter', 'Q2')
            year_val = company_data.get('year', '2024')
            investment_stage = f"{round_val} {quarter_val}, {year_val}"
        
        # 1. Replace company name (transparent background, significantly raised, very thick bold font, orange color)
        # Align with founders position
        founders_block_y = 400  # Approximate Y position of founders yellow block
        founders_text_x = 320  # Founders text X position
        
        # Company name position: aligned with founders but moved a bit to the left, significantly raised
        name_x = founders_text_x - 50  # Moved a bit to the left from founders position
        name_y = 80  # Significantly raised (top of slide)
        
        # Use orange color similar to the rest of the slide (lighter, more vibrant orange)
        name_color = (255, 140, 0)  # More vibrant orange, similar to slide orange
        
        # Use very thick, bold font (matching the image style - extra thick and bold)
        name_font = self._load_font(180, bold=True)
        
        # Draw company name with stroke (outline) to make it appear thicker
        # First draw the stroke (outline) in the same color but slightly darker
        stroke_color = (200, 80, 30)  # Slightly darker orange for stroke
        # Draw stroke by drawing text multiple times with slight offsets
        for adj in range(-3, 4):
            for adj2 in range(-3, 4):
                if adj != 0 or adj2 != 0:
                    draw.text((name_x + adj, name_y + adj2), company_name, fill=stroke_color, font=name_font)
        
        # Then draw the main text on top
        draw.text((name_x, name_y), company_name, fill=name_color, font=name_font)
        
        # 2. Replace logo (circular, top right) - fit within circular bounds, higher position, transparent, more circular
        try:
            logo_img = Image.open(logo_path).convert('RGBA')
            logo_x, logo_y = width - 170, 10  # Raised more (was 20, now 10) to avoid map overlap
            logo_size = 130
            
            # Don't erase background - keep it transparent (no black box)
            # Just paste the logo directly with circular mask
            
            # Resize logo to fit within circle (with more padding for circular shape)
            # Make it more circular by using square aspect ratio
            logo_img.thumbnail((logo_size - 20, logo_size - 20), Image.Resampling.LANCZOS)
            
            # Create perfectly circular mask
            circle_mask = Image.new('L', (logo_size, logo_size), 0)
            circle_draw = ImageDraw.Draw(circle_mask)
            circle_draw.ellipse([(0, 0), (logo_size, logo_size)], fill=255)
            
            # Center logo in circle (square crop for circular appearance)
            logo_w, logo_h = logo_img.size
            # Use the smaller dimension to make it more circular
            min_dim = min(logo_w, logo_h)
            logo_img = logo_img.crop(((logo_w - min_dim) // 2, (logo_h - min_dim) // 2, 
                                     (logo_w + min_dim) // 2, (logo_h + min_dim) // 2))
            logo_img = logo_img.resize((logo_size - 20, logo_size - 20), Image.Resampling.LANCZOS)
            
            # Apply circular mask to logo
            logo_masked = Image.new('RGBA', (logo_size, logo_size), (0, 0, 0, 0))
            logo_masked.paste(logo_img, (10, 10), logo_img)  # Center with 10px padding
            logo_masked.putalpha(circle_mask)
            
            slide.paste(logo_masked, (logo_x, logo_y), logo_masked)
            draw = ImageDraw.Draw(slide)
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
        
        # 3. Updated Map Logic - Map is already in template, just add location text and adjust pin position
        try:
            # Map visual boundaries (Approximate based on 1920x1080 slide)
            # The map starts roughly at x=1250 and ends near the right edge
            map_area_x = 1250  # Updated to match visual position
            map_area_y = 110  # Updated to match visual position
            map_width = 620   # Increased width to match visual scale
            map_height = 450  # Increased height
            
            # Use more accurate normalized coordinates for this specific map projection
            city_coords = self._get_city_coordinates(location)
            
            # Calculate pixel position
            pin_x = map_area_x + int(city_coords[0] * map_width)
            pin_y = map_area_y + int(city_coords[1] * map_height)
            
            # Draw the pin (yellow location pin icon - teardrop shape with circular hole)
            yellow = (255, 215, 0)
            black = (0, 0, 0)
            
            # Pin dimensions - larger for visibility
            pin_width = 40  # Width of the rounded top
            pin_height = 50  # Total height including point
            point_length = 12  # Length of the pointed bottom
            hole_radius = 6  # Radius of the circular hole
            
            # Create a temporary image for the pin to draw the teardrop shape
            pin_img_size = max(pin_width, pin_height + point_length) + 20
            pin_img = Image.new('RGBA', (pin_img_size, pin_img_size), (0, 0, 0, 0))
            pin_draw = ImageDraw.Draw(pin_img)
            
            # Calculate center position in the pin image
            center_x = pin_img_size // 2
            center_y = pin_img_size // 2
            
            # Draw shadow first (slightly offset and darker) for depth
            shadow_offset = 3
            shadow_center_x = center_x + shadow_offset
            shadow_center_y = center_y + shadow_offset
            
            # Shadow: rounded top (ellipse) + pointed bottom (triangle)
            # Top ellipse for shadow
            shadow_top_y = shadow_center_y - pin_height // 2
            pin_draw.ellipse(
                [(shadow_center_x - pin_width // 2, shadow_top_y - pin_width // 4),
                 (shadow_center_x + pin_width // 2, shadow_top_y + pin_width // 4)],
                fill=(50, 50, 50, 120)
            )
            # Bottom triangle for shadow
            shadow_points = [
                (shadow_center_x - pin_width // 2, shadow_top_y + pin_width // 4),
                (shadow_center_x + pin_width // 2, shadow_top_y + pin_width // 4),
                (shadow_center_x, shadow_center_y + point_length + shadow_offset),
            ]
            pin_draw.polygon(shadow_points, fill=(50, 50, 50, 120))
            
            # Draw main teardrop shape (yellow)
            # Top: rounded ellipse (the rounded part of the teardrop)
            top_y = center_y - pin_height // 2
            pin_draw.ellipse(
                [(center_x - pin_width // 2, top_y - pin_width // 4),
                 (center_x + pin_width // 2, top_y + pin_width // 4)],
                fill=yellow, outline=black, width=2
            )
            
            # Bottom: triangle connecting to point (the pointed part)
            teardrop_points = [
                (center_x - pin_width // 2, top_y + pin_width // 4),  # Left bottom of ellipse
                (center_x + pin_width // 2, top_y + pin_width // 4),  # Right bottom of ellipse
                (center_x, center_y + point_length),  # Point at bottom
            ]
            pin_draw.polygon(teardrop_points, fill=yellow, outline=black, width=2)
            
            # Draw circular hole in the center (dark circle for depth)
            hole_center_x = center_x
            hole_center_y = top_y  # Position hole at top center
            pin_draw.ellipse(
                [(hole_center_x - hole_radius, hole_center_y - hole_radius),
                 (hole_center_x + hole_radius, hole_center_y + hole_radius)],
                fill=black
            )
            
            # Add inner highlight ring for 3D effect (lighter inner ring)
            pin_draw.ellipse(
                [(hole_center_x - hole_radius + 2, hole_center_y - hole_radius + 2),
                 (hole_center_x + hole_radius - 2, hole_center_y + hole_radius - 2)],
                fill=(100, 100, 100)
            )
            
            # Paste the pin onto the main slide (centered at pin_x, pin_y)
            paste_pin_x = pin_x - pin_img_size // 2
            paste_pin_y = pin_y - pin_img_size // 2
            slide.paste(pin_img, (paste_pin_x, paste_pin_y), pin_img)
            draw = ImageDraw.Draw(slide)
            
            # Place the city name label with yellow block (similar to other yellow blocks)
            yellow = (255, 215, 0)  # Yellow for the block
            black = (0, 0, 0)  # Black text on yellow background
            
            # Use larger, bold font for location text
            location_font = self._load_font(30, bold=True)
            
            # Get text dimensions with larger font
            label_bbox = draw.textbbox((0, 0), location, font=location_font)
            text_width = label_bbox[2] - label_bbox[0]
            text_height = label_bbox[3] - label_bbox[1]
            
            # Yellow box dimensions (bigger padding for larger text)
            box_padding_x = 24  # Increased from 20
            box_padding_y = 12  # Increased from 10
            box_width = text_width + box_padding_x * 2
            box_height = text_height + box_padding_y * 2
            
            # Position box with bigger space from pin (moved further right and down)
            box_x = pin_x + 40  # More space from pin (was 15, now 40)
            box_y = pin_y + 20  # More space from pin (was -10, now +20)
            
            # Make sure box stays within map bounds
            if box_x + box_width > map_area_x + map_width:
                box_x = pin_x - box_width - 40  # Move to the left if it would go outside
            if box_y + box_height > map_area_y + map_height:
                box_y = pin_y - box_height - 20  # Move up if it would go outside
            
            # Erase old location area (keep transparent; no colored background)
            location_bg = self._get_dominant_color(template, (box_x - 10, box_y - 10, box_width + 20, box_height + 20))
            draw.rectangle([(box_x - 10, box_y - 10), (box_x + box_width + 10, box_y + box_height + 10)], fill=location_bg)
            
            # Draw location text (no background box, transparent behind text)
            text_x = box_x + box_padding_x
            text_y = box_y + box_padding_y
            draw.text((text_x, text_y), location, fill=black, font=location_font)
            
        except Exception as e:
            print(f"Warning: Map update failed: {e}")
        
        # 4. Replace Founders text (moved left and down, transparent)
        # Detect yellow block area for founders (left side, below company name)
        founders_block_y = 400  # Approximate Y position of founders yellow block
        founders_text_y = founders_block_y + 15  # Moved down a little
        founders_text_x = 320  # Moved a little to the left (was 350)
        founders_color = self._get_text_color_from_template(template, founders_text_x, founders_text_y, 600, 100)
        
        # Don't erase background - keep it transparent (no black box)
        # Draw founders text with newlines directly
        founders_lines = founders_text.split('\n')
        for i, line in enumerate(founders_lines):
            draw.text((founders_text_x, founders_text_y + i * 35), line, fill=founders_color, font=body_font)
        
        # 5. Replace Co-Investors text (separate text box, to the right of founders, aligned with founders height)
        investors_block_y = 500  # Approximate Y position of co-investors yellow block
        investors_text_y = founders_text_y  # Aligned with founders (same height)
        investors_text_x = 650  # Moved to the right of founders (founders is at 320, so co-investors at 650)
        investors_color = self._get_text_color_from_template(template, investors_text_x, investors_text_y, 600, 100)
        
        # Don't erase background - keep it transparent (no black box)
        # Draw co-investors text with newlines directly (separate text box)
        investors_lines = co_investors_text.split('\n')
        for i, line in enumerate(investors_lines):
            draw.text((investors_text_x, investors_text_y + i * 35), line, fill=investors_color, font=body_font)
        
        # 6. Replace Background text (aligned with founders, wider text area, bigger font, transparent background)
        bg_block_y = 600  # Approximate Y position of background yellow block
        bg_text_y = bg_block_y + 50  # Text starts below yellow block
        bg_text_x = founders_text_x  # Aligned with founders (moved left from 400 to match founders at 320)
        bg_text_width = 700  # Wider text area (was 500) to fill space more
        words = background_text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=body_font)
            if bbox[2] - bbox[0] < bg_text_width:  # Wider width for background
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Get text color from template (don't erase background - keep it transparent)
        bg_color = self._get_text_color_from_template(template, bg_text_x, bg_text_y, bg_text_width, 200)
        
        # Use slightly bigger font for background text
        bg_font = self._load_font(32)
        
        # Draw text directly without erasing background (transparent)
        for i, line in enumerate(lines[:10]):
            draw.text((bg_text_x, bg_text_y + i * 36), line, fill=bg_color, font=bg_font)  # Slightly more spacing
        
        # 7. Replace headshots (below map, moved left, bigger size, transparent)
        try:
            from image_processor import ImageProcessor
            
            # Remove background from headshot to make it transparent
            try:
                headshot_no_bg_bytes = ImageProcessor.remove_background(headshot_path)
                headshot_img = Image.open(io.BytesIO(headshot_no_bg_bytes)).convert('RGBA')
            except Exception as e:
                print(f"Warning: Background removal failed, using original: {e}")
                # Fallback: use original image
                headshot_img = Image.open(headshot_path).convert('RGBA')
            
            # Position headshots below the map, moved to the left
            # Map area: right side, upper-middle
            map_area_x = width - 450  # Right side of map
            map_area_y = 280
            map_width = 380
            map_height = 260
            
            # Headshot moved to the left, increased size, and raised
            headshot_area_width = 550  # Increased size (was 450)
            headshot_area_height = 500  # Increased size (was 400)
            # Move left by offsetting from map center
            headshot_area_x = map_area_x + (map_width - headshot_area_width) // 2 - 150  # Moved more to the left (was -100, now -150)
            headshot_area_y = map_area_y + map_height - 50  # Raised (was +20, now -50 to move up)
            
            # Don't erase background - keep it transparent (no black box)
            # Just paste the headshot directly
            
            # Resize headshot to be bigger
            headshot_img.thumbnail((headshot_area_width, headshot_area_height), Image.Resampling.LANCZOS)
            
            # Center headshot in the area
            headshot_w, headshot_h = headshot_img.size
            paste_x = headshot_area_x + (headshot_area_width - headshot_w) // 2
            paste_y = headshot_area_y + (headshot_area_height - headshot_h) // 2
            
            # Paste with transparency (no background rectangle)
            slide.paste(headshot_img, (paste_x, paste_y), headshot_img)
            draw = ImageDraw.Draw(slide)
        except Exception as e:
            print(f"Warning: Could not load headshot: {e}")
            import traceback
            traceback.print_exc()
        
        # 8. Replace investment stage in sidebar (transparent, black, thicker text like company name, includes year)
        # Find Slauson&Co position in sidebar (bottom of sidebar)
        slauson_y = height - 200  # Approximate position of "SLAUSON&CO." text (bottom of sidebar)
        
        # Parse investment stage to format as "STAGE QUARTER YEAR" (e.g., "SEED Q2 2024")
        # Format is typically like "SEED Q2, 2024" or "PRE-SEED Q2, 2024"
        stage_parts = investment_stage.upper().split(',')
        if len(stage_parts) >= 2:
            stage_quarter = stage_parts[0].strip()  # "SEED Q2" or "PRE-SEED Q2"
            year_text = stage_parts[1].strip()  # "2024"
            # Combine into "STAGE QUARTER YEAR" format
            stage_text = f"{stage_quarter} {year_text}"  # "SEED Q2 2024"
        else:
            stage_text = investment_stage.upper()
        
        # Use bigger, bolder font for sidebar text (similar size to company name but rotated)
        sidebar_bold_font = self._load_font(40, bold=True)
        
        # Don't erase background - keep it transparent
        # Use black color
        stage_color = (0, 0, 0)  # Black color
        stroke_color = (50, 50, 50)  # Dark grey for stroke (thicker effect)
        
        # Draw investment stage at the TOP of sidebar (opposite end from Slauson&Co)
        # Align with Slauson&Co position (which is at the bottom of sidebar, left-aligned)
        # Slauson&Co is positioned more to the left, around x=10-20 in the sidebar
        sidebar_width = 200
        slauson_x = 10  # More to the left to align with Slauson&Co text
        
        stage_top_y = 80  # Near the top of the sidebar
        
        # Get text dimensions first to calculate proper image size
        temp_img = Image.new('RGBA', (1000, 1000), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), stage_text, font=sidebar_bold_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Create much larger image to accommodate rotated text (text will be rotated 90 degrees)
        # When rotated, width becomes height and height becomes width
        # Add extra padding to prevent cutoff - use larger padding for stroke effect
        padding = 100  # Increased padding significantly
        stage_img_width = text_height + padding * 2  # Width after rotation
        stage_img_height = text_width + padding * 2  # Height after rotation
        
        # Ensure minimum size to prevent cutoff
        stage_img_width = max(stage_img_width, 300)
        stage_img_height = max(stage_img_height, 500)
        
        stage_img = Image.new('RGBA', (stage_img_width, stage_img_height), (0, 0, 0, 0))
        stage_draw = ImageDraw.Draw(stage_img)
        
        # Align text to appear at the left edge after rotation
        # When rotated -90 degrees, the top edge of horizontal text becomes the left edge of vertical text
        # So we position text at the top of the horizontal image
        text_x = stage_img_width // 2 - text_width // 2  # Center horizontally before rotation
        text_y = padding  # Position at top edge (with padding) - this becomes left edge after rotation
        
        # Draw stroke by drawing text multiple times with slight offsets (thicker effect)
        for adj in range(-2, 3):
            for adj2 in range(-2, 3):
                if adj != 0 or adj2 != 0:
                    stage_draw.text((text_x + adj, text_y + adj2), stage_text, fill=stroke_color, font=sidebar_bold_font)
        
        # Then draw the main text on top
        stage_draw.text((text_x, text_y), stage_text, fill=stage_color, font=sidebar_bold_font)
        
        # Rotate the image 90 degrees counter-clockwise
        stage_img = stage_img.rotate(-90, expand=True)
        
        # Get final dimensions after rotation
        final_width, final_height = stage_img.size
        
        # Paste at the right side of the orange sidebar (moved significantly to the right)
        # After rotation, the text runs vertically, positioned at the right edge of sidebar
        sidebar_width = 200  # Orange sidebar width
        paste_x = sidebar_width - final_width - 20  # Position at right side of sidebar with padding
        paste_y = max(20, stage_top_y)  # Ensure it doesn't go outside top edge
        
        slide.paste(stage_img, (paste_x, paste_y), stage_img)
        
        # Convert to RGB for PDF
        slide_rgb = Image.new('RGB', slide.size, (42, 42, 42))
        slide_rgb.paste(slide, mask=slide.split()[3] if slide.mode == 'RGBA' else None)
        
        # Convert to PDF
        img_bytes = io.BytesIO()
        slide_rgb.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        pdf_bytes = img2pdf.convert(img_bytes.getvalue())
        return pdf_bytes
