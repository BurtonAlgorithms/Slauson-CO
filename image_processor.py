"""
Image processing utilities for portfolio onboarding.
Handles background removal, grayscale conversion, and image manipulation.
Uses Gemini 3 Pro for advanced image processing.
"""
import io
import requests
import base64
from PIL import Image, ImageEnhance, ImageFont
from typing import Optional, List
from config import Config


class ImageProcessor:
    """Process images for portfolio slides."""
    
    @staticmethod
    def remove_background(image_path: str, output_path: Optional[str] = None) -> bytes:
        """
        Remove background from image using Remove.bg API.
        
        Args:
            image_path: Path to input image or image URL
            output_path: Optional path to save output image
            
        Returns:
            Bytes of processed image
        """
        if not Config.REMOVEBG_API_KEY:
            # Fallback: return original image if no API key
            print("Warning: REMOVEBG_API_KEY not set. Skipping background removal.")
            with open(image_path, 'rb') as f:
                return f.read()
        
        # Check if this is a placeholder image (skip background removal)
        if 'placeholder' in image_path.lower():
            print("Skipping background removal for placeholder image")
            with open(image_path, 'rb') as f:
                return f.read()
        
        api_url = "https://api.remove.bg/v1.0/removebg"
        
        try:
            with open(image_path, 'rb') as image_file:
                response = requests.post(
                    api_url,
                    files={'image_file': image_file},
                    data={'size': 'auto'},
                    headers={'X-Api-Key': Config.REMOVEBG_API_KEY},
                    timeout=15  # 15 second timeout to prevent hanging
                )
            
            if response.status_code == 200:
                image_bytes = response.content
                if output_path:
                    with open(output_path, 'wb') as out_file:
                        out_file.write(image_bytes)
                return image_bytes
            else:
                # If Remove.bg fails, return original image
                print(f"Warning: Remove.bg API error: {response.status_code} - {response.text}")
                print("Using original image without background removal")
                with open(image_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            # If any error occurs, return original image
            print(f"Warning: Background removal failed: {e}")
            print("Using original image without background removal")
            with open(image_path, 'rb') as f:
                return f.read()
    
    @staticmethod
    def to_grayscale(image_bytes: bytes) -> bytes:
        """
        Convert image to grayscale.
        
        Args:
            image_bytes: Image bytes
            
        Returns:
            Grayscale image bytes
        """
        image = Image.open(io.BytesIO(image_bytes))
        grayscale_image = image.convert('L')
        
        # Convert back to RGB if needed (for compatibility)
        if grayscale_image.mode != 'RGB':
            grayscale_image = grayscale_image.convert('RGB')
        
        output = io.BytesIO()
        grayscale_image.save(output, format='PNG')
        return output.getvalue()
    
    @staticmethod
    def process_headshot(image_path: str, output_path: str) -> bytes:
        """
        Process headshot: remove background and convert to grayscale.
        
        Args:
            image_path: Path to input headshot
            output_path: Path to save processed headshot
            
        Returns:
            Processed image bytes
        """
        try:
            # Remove background (will skip for placeholders or return original on error)
            no_bg_image = ImageProcessor.remove_background(image_path)
            
            # Convert to grayscale
            grayscale_image = ImageProcessor.to_grayscale(no_bg_image)
            
            # Save if output path provided
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(grayscale_image)
            
            return grayscale_image
        except Exception as e:
            # If processing fails, try to just convert to grayscale
            print(f"Warning: Headshot processing failed: {e}")
            print("Attempting grayscale conversion only...")
            try:
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                grayscale_image = ImageProcessor.to_grayscale(image_bytes)
                if output_path:
                    with open(output_path, 'wb') as f:
                        f.write(grayscale_image)
                return grayscale_image
            except Exception as e2:
                print(f"Error: Could not process headshot: {e2}")
                # Return original as last resort
                with open(image_path, 'rb') as f:
                    return f.read()
    
    @staticmethod
    def resize_image(image_bytes: bytes, max_width: int, max_height: int) -> bytes:
        """
        Resize image while maintaining aspect ratio.
        
        Args:
            image_bytes: Image bytes
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Resized image bytes
        """
        image = Image.open(io.BytesIO(image_bytes))
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    
    @staticmethod
    def process_headshots_with_gemini(
        headshot_paths: List[str],
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Process multiple headshots using Gemini 3 Pro:
        - Remove backgrounds
        - Convert to greyscale
        - Combine them together (overlapping style like in the slide design)
        
        Args:
            headshot_paths: List of paths to headshot images
            output_path: Optional path to save processed image
            
        Returns:
            Processed combined headshot image bytes
        """
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured. Required for Gemini image processing.")
        
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=Config.GEMINI_API_KEY)
            
            # Use Gemini model - try paid tier models first (Tier 1+), then free tier
            models_to_try = [
                'gemini-2.0-flash-exp',  # Paid tier (Tier 1+) - best performance
                'gemini-1.5-pro',        # Free tier available, good performance
                'gemini-1.5-flash',      # Free tier available, fast
                'gemini-pro',            # Free tier available
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
                raise ValueError("No Gemini model available. Check your API key and quota.")
            
            # Load all headshot images
            headshot_images = []
            for path in headshot_paths:
                with open(path, 'rb') as f:
                    img_bytes = f.read()
                # Convert to PIL Image for processing
                img = Image.open(io.BytesIO(img_bytes))
                headshot_images.append(img)
            
            # Create prompt for Gemini
            prompt = """Process these headshot images:
1. Remove the background from each headshot
2. Convert each headshot to greyscale
3. Combine them together in an overlapping style (like two photos slightly overlapping, with the left one partially in front of the right one)
4. Make sure the headshots are rectangular (not circular) and maintain good quality
5. The final combined image should be suitable for placing in the bottom right corner of a presentation slide
6. Return the processed combined image as PNG format

The headshots should be arranged horizontally with slight overlap, maintaining their rectangular shape."""
            
            # Prepare images for Gemini
            # Gemini can accept multiple images
            image_parts = []
            for img in headshot_images:
                # Convert PIL Image to bytes
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                image_parts.append({
                    "mime_type": "image/png",
                    "data": img_bytes.read()
                })
            
            # Call Gemini with images and prompt
            # Note: Gemini's image generation capabilities may vary
            # We'll use it to process and combine the images
            # Don't set response_mime_type to image/png - it's not in the allowed list
            # Instead, we'll extract the image from the response text or parts
            response = model.generate_content(
                [prompt] + [img["data"] for img in image_parts]
            )
            
            # Extract image from response
            if hasattr(response, 'parts') and response.parts:
                # Try to get image data from response
                for part in response.parts:
                    if hasattr(part, 'inline_data'):
                        image_bytes = part.inline_data.data
                        if output_path:
                            with open(output_path, 'wb') as f:
                                f.write(image_bytes)
                        return image_bytes
            
            # Fallback: If Gemini doesn't return image directly, process manually
            print("Gemini didn't return image directly, using manual processing...")
            return ImageProcessor._combine_headshots_manual(headshot_images, output_path)
            
        except ImportError:
            raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
        except Exception as e:
            print(f"Warning: Gemini headshot processing failed: {e}")
            print("Falling back to manual processing...")
            # Fallback to manual processing
            headshot_images = []
            for path in headshot_paths:
                with open(path, 'rb') as f:
                    img_bytes = f.read()
                img = Image.open(io.BytesIO(img_bytes))
                headshot_images.append(img)
            return ImageProcessor._combine_headshots_manual(headshot_images, output_path)
    
    @staticmethod
    def _combine_headshots_manual(
        headshot_images: List[Image.Image],
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Manually combine headshots with background removal and greyscale.
        Fallback method when Gemini doesn't work.
        """
        processed_images = []
        
        for img in headshot_images:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to consistent size (e.g., 300x400 for headshots)
            img.thumbnail((300, 400), Image.Resampling.LANCZOS)
            
            # Convert to greyscale
            img_gray = img.convert('L').convert('RGB')
            
            processed_images.append(img_gray)
        
        # Combine images with overlap
        if len(processed_images) == 1:
            combined = processed_images[0]
        else:
            # Create canvas for combined image
            total_width = processed_images[0].width + processed_images[1].width - 100  # Overlap by 100px
            max_height = max(img.height for img in processed_images)
            combined = Image.new('RGB', (total_width, max_height), color='white')
            
            # Paste first image
            combined.paste(processed_images[0], (0, 0))
            
            # Paste second image with overlap
            if len(processed_images) > 1:
                combined.paste(processed_images[1], (processed_images[0].width - 100, 0))
        
        # Save to bytes
        output = io.BytesIO()
        combined.save(output, format='PNG')
        output_bytes = output.getvalue()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(output_bytes)
        
        return output_bytes
    
    @staticmethod
    def generate_map_with_gemini(location: str, output_path: Optional[str] = None) -> bytes:
        """
        Generate a map image with location pin using Gemini 3 Pro.
        
        Args:
            location: City name (e.g., "Los Angeles", "Dallas")
            output_path: Optional path to save map image
            
        Returns:
            Map image bytes (PNG format)
        """
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured. Required for map generation.")
        
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=Config.GEMINI_API_KEY)
            
            # Use Gemini model - try paid tier models first (Tier 1+), then free tier
            models_to_try = [
                'gemini-2.0-flash-exp',  # Paid tier (Tier 1+) - best performance
                'gemini-1.5-pro',        # Free tier available, good performance
                'gemini-1.5-flash',      # Free tier available, fast
                'gemini-pro',            # Free tier available
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
                raise ValueError("No Gemini model available. Check your API key and quota.")
            
            prompt = f"""Create a stylized map image showing the location of {location}:
- Show a simplified, minimalist map of the United States with orange outlines of states and major roads
- Use a dark grey background (like #2a2a2a or similar)
- Place a prominent yellow map pin icon over the correct location on the map (specifically pointing to {location})
- Add a rectangular yellow text box adjacent to the map pin containing the location name "{location}" in bold black text
- Style should be minimalist and graphic, resembling a navigation or game map rather than a detailed geographical representation
- The map should be suitable for use as a background element in a presentation slide
- Orange color for outlines: bright orange (#FF8C00 or similar)
- Yellow for pin and text box: bright yellow (#FFD700 or similar)
- Dark grey background: (#2a2a2a or similar)
- Return the map as a PNG image with these exact specifications"""
            
            # Generate map image
            # Don't set response_mime_type to image/png - it's not in the allowed list
            # Instead, we'll extract the image from the response text or parts
            response = model.generate_content(prompt)
            
            # Extract image from response
            # Check if response has candidates first
            if hasattr(response, 'candidates') and response.candidates:
                # Response has candidates, try to extract image
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data'):
                                image_bytes = part.inline_data.data
                                if output_path:
                                    with open(output_path, 'wb') as f:
                                        f.write(image_bytes)
                                return image_bytes
            
            # Fallback: try direct parts access
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data'):
                        image_bytes = part.inline_data.data
                        if output_path:
                            with open(output_path, 'wb') as f:
                                f.write(image_bytes)
                        return image_bytes
            
            # Fallback: Return placeholder if Gemini doesn't generate image
            print("Warning: Gemini didn't return map image, creating placeholder...")
            return ImageProcessor._create_map_placeholder(location, output_path)
            
        except ImportError:
            raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
        except Exception as e:
            print(f"Warning: Gemini map generation failed: {e}")
            print("Creating placeholder map...")
            return ImageProcessor._create_map_placeholder(location, output_path)
    
    @staticmethod
    def _create_map_placeholder(location: str, output_path: Optional[str] = None) -> bytes:
        """
        Create a placeholder map image when Gemini generation fails.
        Matches the style: dark grey background, orange outlines, yellow pin and text box.
        """
        from PIL import ImageDraw
        
        # Create image with dark grey background (matching the style)
        img = Image.new('RGB', (800, 600), color=(42, 42, 42))  # Dark grey #2a2a2a
        draw = ImageDraw.Draw(img)
        
        # Draw simplified US outline in orange
        # Very simplified - just a rough outline
        orange = (255, 140, 0)  # Bright orange
        draw.rectangle([100, 100, 700, 500], outline=orange, width=3)
        # Add some simplified state-like shapes
        draw.ellipse([200, 150, 400, 300], outline=orange, width=2)  # Simplified shape
        draw.ellipse([450, 200, 650, 400], outline=orange, width=2)  # Another shape
        
        # Draw yellow map pin (simplified triangle/pin shape)
        yellow = (255, 215, 0)  # Bright yellow #FFD700
        # Draw pin as a triangle pointing down
        pin_x, pin_y = 400, 350  # Approximate center
        pin_points = [
            (pin_x, pin_y - 15),  # Top point
            (pin_x - 10, pin_y + 5),  # Bottom left
            (pin_x + 10, pin_y + 5)   # Bottom right
        ]
        draw.polygon(pin_points, fill=yellow, outline=(200, 150, 0), width=1)
        # Pin circle
        draw.ellipse([pin_x - 5, pin_y - 5, pin_x + 5, pin_y + 5], fill=(200, 150, 0))
        
        # Draw yellow text box with location name
        text_box_x, text_box_y = pin_x + 20, pin_y - 10
        text_box_width, text_box_height = 150, 30
        draw.rectangle(
            [text_box_x, text_box_y, text_box_x + text_box_width, text_box_y + text_box_height],
            fill=yellow,
            outline=(200, 150, 0),
            width=1
        )
        
        # Add location text in bold black
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", 18)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
            except:
                font = ImageFont.load_default()
        
        # Center text in box
        text_x = text_box_x + text_box_width // 2
        text_y = text_box_y + text_box_height // 2
        draw.text((text_x, text_y), location, fill=(0, 0, 0), font=font, anchor="mm")
        
        output = io.BytesIO()
        img.save(output, format='PNG')
        output_bytes = output.getvalue()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(output_bytes)
        
        return output_bytes

