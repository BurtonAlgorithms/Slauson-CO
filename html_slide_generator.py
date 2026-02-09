"""
PDF/Image template-based slide generator.
Uses Canva PDF or image template and overlays text/images using PIL.
Supports both PDF and image templates (JPG, PNG, etc.)
"""
import os
from typing import Dict, Optional
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import hashlib
import img2pdf
from collections import Counter
import numpy as np
from functools import lru_cache

# PPTX support for editable Canva designs
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

# Fix for reportlab compatibility
try:
    hashlib.md5(b'test', usedforsecurity=False)
except TypeError:
    _original_md5 = hashlib.md5
    def _patched_md5(data=None, usedforsecurity=True):
        return _original_md5(data) if data is not None else _original_md5()
    hashlib.md5 = _patched_md5

class HTMLSlideGenerator:
    # Class-level cache for rembg session (avoids reloading model on every request)
    _rembg_session = None
    
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

        # Optional debug: prove which bundled fonts are present at runtime (Railway/Render shells aren't always available).
        if os.getenv("DEBUG_FONTS", "").strip().lower() in ("1", "true", "yes", "y", "on"):
            try:
                fonts_dir = os.path.join(script_dir, "assets", "fonts")
                exists = os.path.exists(fonts_dir)
                print(f"DEBUG_FONTS: assets/fonts exists={exists} path={fonts_dir}")
                if exists:
                    files = sorted(os.listdir(fonts_dir))
                    print(f"DEBUG_FONTS: assets/fonts files={files}")
                    bebas_path = os.path.join(fonts_dir, "BebasNeue-Regular.ttf")
                    print(f"DEBUG_FONTS: BebasNeue-Regular.ttf exists={os.path.exists(bebas_path)} size={os.path.getsize(bebas_path) if os.path.exists(bebas_path) else 'N/A'}")
            except Exception as e:
                print(f"DEBUG_FONTS: could not inspect bundled fonts: {e}")
        
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

    def _load_font(self, size: int, bold: bool = False, preferred_family: Optional[str] = None):
        """
        Load a font with robust fallbacks that work on Render.
        Tries common system fonts, then DejaVu (available in most containers), then default.
        """
        def _looks_italic(font_path: str) -> bool:
            try:
                base = os.path.basename(font_path).lower()
            except Exception:
                base = str(font_path).lower()
            return ("italic" in base) or ("oblique" in base) or ("slanted" in base)

        font_candidates = []
        
        # Optional: try a preferred font family first (e.g., "Trouble")
        if preferred_family:
            try:
                fam = preferred_family.strip()
            except Exception:
                fam = str(preferred_family)
            fam_lower = fam.lower()
            
            # 1) Project-bundled fonts (recommended for consistency)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bundled_dirs = [
                os.path.join(script_dir, "assets"),
                os.path.join(script_dir, "assets", "fonts"),
                os.path.join(script_dir, "assets", "font"),
                os.path.join(script_dir, "fonts"),
            ]
            bundled_names = [
                f"{fam}.ttf",
                f"{fam}.otf",
                f"{fam} Font.ttf",
                f"{fam} Font.otf",
                f"{fam.replace(' ', '')}.ttf",
                f"{fam.replace(' ', '')}.otf",
                f"{fam}-Regular.ttf",
                f"{fam}-Regular.otf",
                f"{fam}-Bold.ttf",
                f"{fam}-Bold.otf",
            ]
            for d in bundled_dirs:
                for n in bundled_names:
                    font_candidates.append(os.path.join(d, n))
            
            # 2) Common OS font folders (local dev)
            system_dirs = [
                os.path.expanduser("~/Library/Fonts"),
                "/Library/Fonts",
                "/System/Library/Fonts",
                "/usr/share/fonts",
                "/usr/local/share/fonts",
            ]
            for d in system_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                    for fname in os.listdir(d):
                        fname_lower = fname.lower()
                        if fam_lower in fname_lower and fname_lower.endswith((".ttf", ".otf", ".ttc")):
                            if "italic" in fname_lower or "oblique" in fname_lower or "slanted" in fname_lower:
                                continue
                            font_candidates.append(os.path.join(d, fname))
                except Exception:
                    pass
            
            # 3) Linux font discovery via fontconfig (if available)
            try:
                import subprocess
                result = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=1)
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if fam_lower in line.lower():
                            font_path = line.split(":")[0] if ":" in line else None
                            if font_path and os.path.exists(font_path):
                                if _looks_italic(font_path):
                                    continue
                                font_candidates.insert(0, font_path)
            except Exception:
                pass

        # Preferred bundled fonts on Linux containers (Render uses these)
        if bold:
            font_candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
            font_candidates.append("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
        font_candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        font_candidates.append("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
        # Try to find fonts via fontconfig (common on Linux).
        #
        # Important: if a preferred_family is requested, do NOT insert DejaVu/Liberation
        # ahead of the preferred family candidates (Railway/Nix often returns DejaVuSerif
        # which would override BebasNeue even when it's bundled).
        if not preferred_family:
            try:
                import subprocess
                result = subprocess.run(['fc-list'], capture_output=True, text=True, timeout=1)
                if result.returncode == 0:
                    # Look for DejaVu or Liberation in font list
                    for line in result.stdout.split('\n'):
                        if 'DejaVu' in line or 'Liberation' in line:
                            font_path = line.split(':')[0] if ':' in line else None
                            if font_path and os.path.exists(font_path):
                                if _looks_italic(font_path):
                                    continue
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

        debug_fonts = os.getenv("DEBUG_FONTS", "").strip().lower() in ("1", "true", "yes", "y", "on")

        for path in font_candidates:
            try:
                if os.path.exists(path) or not os.path.isabs(path):
                    # Only check existence for absolute paths
                    if _looks_italic(path):
                        continue
                    font = ImageFont.truetype(path, size)
                    if debug_fonts:
                        print(f"✓ Loaded font: {path} (size={size}, bold={bold})")
                    return font
            except (OSError, IOError, Exception) as e:
                # Continue to next candidate, but log *targeted* failures when debugging.
                if debug_fonts:
                    try:
                        base = os.path.basename(path).lower()
                        # Only log likely-relevant failures to avoid spam.
                        if (
                            (preferred_family and preferred_family.lower().replace(" ", "") in base.replace(" ", ""))
                            or "bebas" in base
                            or path.startswith("/app/assets/")
                        ):
                            print(f"✗ Failed to load font: {path} (size={size}, bold={bold}) err={e}")
                    except Exception:
                        pass
                continue
        
        # Fallback: Pillow bundles DejaVu fonts in most builds; use them if available.
        # This keeps text sizing consistent even in minimal containers (Railway/Nixpacks).
        try:
            import PIL

            pil_fonts_dir = os.path.join(os.path.dirname(PIL.__file__), "fonts")
            pil_font_path = os.path.join(
                pil_fonts_dir,
                "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            )
            if os.path.exists(pil_font_path):
                font = ImageFont.truetype(pil_font_path, size)
                if os.getenv("DEBUG_FONTS", "").strip() in ("1", "true", "yes", "y", "on"):
                    print(f"✓ Loaded font (Pillow bundled): {pil_font_path} (size={size}, bold={bold})")
                return font
        except Exception:
            pass

        # Final fallback: bitmap default (NOTE: ignores `size`, will look tiny).
        print(
            "Warning: Could not load any TrueType font (custom/system/Pillow-bundled). "
            f"Falling back to PIL default bitmap font (requested size={size})."
        )
        return ImageFont.load_default()

    def _parse_name_list(self, value) -> list:
        """
        Normalize a founders/co-investors field into a list of non-empty strings.
        Accepts:
        - list[str]
        - comma-separated string
        - newline-separated string
        """
        if not value:
            return []
        if isinstance(value, list):
            items = value
        else:
            s = str(value)
            # If already newline-separated, split on newlines first.
            if "\n" in s:
                items = s.splitlines()
            else:
                items = s.split(",") if "," in s else [s]
        out = []
        for it in items:
            try:
                t = str(it).strip()
            except Exception:
                t = ""
            if t:
                out.append(t)
        return out

    def _make_white_background_transparent(self, img: Image.Image, threshold: int = 245) -> Image.Image:
        """
        Convert near-white pixels to transparent.
        Useful for icon PNGs that ship with a white box background.
        """
        try:
            rgba = img.convert("RGBA")
            arr = np.array(rgba)
            rgb = arr[:, :, :3]
            alpha = arr[:, :, 3]
            mask_white = (rgb[:, :, 0] >= threshold) & (rgb[:, :, 1] >= threshold) & (rgb[:, :, 2] >= threshold) & (alpha > 0)
            arr[mask_white, 3] = 0
            return Image.fromarray(arr, mode="RGBA")
        except Exception:
            return img.convert("RGBA")

    def _load_map_pin_icon(self, project_root: str) -> Optional[Image.Image]:
        """
        Load a custom map pin icon (PNG) if available.

        Order:
        1) MAP_PIN_ICON_PATH env var (absolute or relative)
        2) assets/pin_marker.png in this repo
        """
        candidates = []
        env_path = os.getenv("MAP_PIN_ICON_PATH")
        if env_path:
            candidates.append(env_path)
        candidates.append(os.path.join(project_root, "assets", "pin_marker.png"))

        for path in candidates:
            try:
                if not path:
                    continue
                resolved = path
                if not os.path.isabs(resolved):
                    resolved = os.path.join(project_root, resolved)
                if not os.path.exists(resolved):
                    continue
                icon = Image.open(resolved).convert("RGBA")
                icon = self._make_white_background_transparent(icon)
                # Trim transparent margins if any
                bbox = icon.split()[3].getbbox()
                if bbox:
                    icon = icon.crop(bbox)
                return icon
            except Exception:
                continue
        return None

    def _load_location_label_bg(self, project_root: str) -> Optional[Image.Image]:
        """
        Load a custom background image for the map location label.

        Order:
        1) MAP_LOCATION_LABEL_BG_PATH env var (absolute or relative)
        2) assets/location_label_bg.png in this repo
        """
        candidates = []
        env_path = os.getenv("MAP_LOCATION_LABEL_BG_PATH")
        if env_path:
            candidates.append(env_path)
        candidates.append(os.path.join(project_root, "assets", "location_label_bg.png"))

        for path in candidates:
            try:
                if not path:
                    continue
                resolved = path
                if not os.path.isabs(resolved):
                    resolved = os.path.join(project_root, resolved)
                if not os.path.exists(resolved):
                    continue
                bg = Image.open(resolved).convert("RGBA")
                bg = self._make_white_background_transparent(bg)
                # Trim transparent margins if any
                bbox = bg.split()[3].getbbox()
                if bbox:
                    bg = bg.crop(bbox)
                return bg
            except Exception:
                continue
        return None

    def _resize_pill_bg(self, bg: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """
        Resize a pill-shaped background without squishing the rounded ends.

        Strategy:
        - Scale background to target height (preserve aspect ratio)
        - 3-slice horizontally: left cap + stretchable center + right cap
        """
        bg = bg.convert("RGBA")
        target_w = max(1, int(target_w))
        target_h = max(1, int(target_h))

        # First, scale to target height while preserving aspect ratio.
        if bg.size[1] != target_h:
            scale = target_h / float(bg.size[1])
            scaled_w = max(1, int(bg.size[0] * scale))
            bg = bg.resize((scaled_w, target_h), Image.Resampling.LANCZOS)

        # Choose a cap width based on height (typical pill geometry).
        # Clamp so the center slice always has positive width.
        cap_w = min(max(1, int(bg.size[1] * 0.55)), max(1, (bg.size[0] // 2) - 1))

        # If the requested width is too small, just do a normal resize.
        if target_w <= cap_w * 2 + 1:
            return bg.resize((target_w, target_h), Image.Resampling.LANCZOS)

        left = bg.crop((0, 0, cap_w, target_h))
        right = bg.crop((bg.size[0] - cap_w, 0, bg.size[0], target_h))
        center = bg.crop((cap_w, 0, bg.size[0] - cap_w, target_h))

        center_w = target_w - (cap_w * 2)
        center = center.resize((center_w, target_h), Image.Resampling.LANCZOS)

        out = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        out.paste(left, (0, 0), left)
        out.paste(center, (cap_w, 0), center)
        out.paste(right, (cap_w + center_w, 0), right)
        return out

    def _dominant_visible_rgb(self, img: Image.Image) -> Optional[tuple]:
        """
        Estimate a dominant RGB color from an RGBA image, ignoring transparent pixels,
        near-white backgrounds, and very dark outline/shadow pixels.
        """
        try:
            rgba = img.convert("RGBA")
            arr = np.array(rgba)
            rgb = arr[:, :, :3].astype(np.int16)
            a = arr[:, :, 3].astype(np.int16)

            # Visible pixels only
            mask = a > 10

            # Exclude near-white (common icon background)
            mask &= ~((rgb[:, :, 0] > 245) & (rgb[:, :, 1] > 245) & (rgb[:, :, 2] > 245))

            # Exclude very dark pixels (often outline/shadow)
            luma = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2])
            mask &= luma > 45

            coords = np.where(mask)
            if coords[0].size < 50:
                return None

            pixels = rgb[coords]
            med = np.median(pixels, axis=0)
            return (int(med[0]), int(med[1]), int(med[2]))
        except Exception:
            return None

    def _tint_rgba_to_color(self, img: Image.Image, target_rgb: tuple) -> Image.Image:
        """
        Tint an RGBA image towards a target color while preserving shading.
        Uses per-channel scaling based on the image's average visible color.
        """
        try:
            rgba = img.convert("RGBA")
            arr = np.array(rgba).astype(np.float32)
            rgb = arr[:, :, :3]
            a = arr[:, :, 3]

            mask = a > 0
            if mask.sum() == 0:
                return rgba

            base = rgb[mask].mean(axis=0)
            base = np.maximum(base, 1.0)

            target = np.array(target_rgb, dtype=np.float32)
            scale = target / base
            scale = np.clip(scale, 0.15, 6.0)

            rgb = np.clip(rgb * scale, 0, 255)
            arr[:, :, :3] = rgb
            return Image.fromarray(arr.astype(np.uint8), mode="RGBA")
        except Exception:
            return img.convert("RGBA")

    def _darken_rgba(self, img: Image.Image, factor: float = 0.88) -> Image.Image:
        """
        Darken an RGBA image by multiplying RGB channels (preserves alpha).
        factor < 1.0 makes it darker.
        """
        try:
            rgba = img.convert("RGBA")
            arr = np.array(rgba).astype(np.float32)
            arr[:, :, :3] = np.clip(arr[:, :, :3] * float(factor), 0, 255)
            return Image.fromarray(arr.astype(np.uint8), mode="RGBA")
        except Exception:
            return img.convert("RGBA")
    
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
    
    def _remove_background_manual(self, img: Image.Image, tol: int = 38, feather: int = 2) -> Image.Image:
        """
        Flood-fill from the border to remove background (RGBA alpha=0),
        using multi-corner background samples + auto tolerance fallback.
        """
        try:
            import numpy as np
        except ImportError:
            print("   Warning: numpy not available for manual background removal")
            return img.convert("RGBA")

        img = img.convert("RGBA")
        arr = np.array(img)
        rgb = arr[..., :3].astype(np.int16)
        alpha = arr[..., 3].astype(np.uint8)
        H, W = rgb.shape[:2]

        corner_size = max(12, min(H, W) // 18)

        # Compute per-corner medians (better for gradients / non-uniform bg)
        tl = np.median(rgb[0:corner_size, 0:corner_size].reshape(-1, 3), axis=0)
        tr = np.median(rgb[0:corner_size, W - corner_size:W].reshape(-1, 3), axis=0)
        bl = np.median(rgb[H - corner_size:H, 0:corner_size].reshape(-1, 3), axis=0)
        br = np.median(rgb[H - corner_size:H, W - corner_size:W].reshape(-1, 3), axis=0)
        bgs = np.stack([tl, tr, bl, br], axis=0).astype(np.int16)

        def compute_close_mask(t):
            diffs = rgb[None, ...] - bgs[:, None, None, :]
            dist2 = (diffs * diffs).sum(axis=3)  # (4,H,W)
            dist = np.sqrt(dist2.min(axis=0))    # (H,W)
            return dist <= t

        tol_candidates = [tol, 45, 55, 65, 75] if tol < 45 else [tol, tol + 10, tol + 20]
        best = None

        from collections import deque

        for t in tol_candidates:
            close = compute_close_mask(t)

            bg_mask = np.zeros((H, W), dtype=bool)
            q = deque()

            def push(y, x):
                # Check bounds FIRST before accessing arrays
                if not (0 <= y < H and 0 <= x < W):
                    return
                if close[y, x] and not bg_mask[y, x]:
                    bg_mask[y, x] = True
                    q.append((y, x))

            # seed edges
            for x in range(W):
                push(0, x); push(H - 1, x)
            for y in range(H):
                push(y, 0); push(y, W - 1)

            # 8-neighborhood flood fill
            while q:
                y, x = q.popleft()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        push(y + dy, x + dx)

            removed_frac = bg_mask.mean()
            if 0.05 <= removed_frac <= 0.80:
                best = (t, bg_mask, removed_frac)
                break

            if best is None or abs(removed_frac - 0.30) < abs(best[2] - 0.30):
                best = (t, bg_mask, removed_frac)

        t, bg_mask, removed_frac = best
        print(f"   Manual BG removal: tol={t}, removed={removed_frac:.1%}")

        new_alpha = alpha.copy()
        new_alpha[bg_mask] = 0

        out = arr.copy()
        out[..., 3] = new_alpha
        out_img = Image.fromarray(out, "RGBA")

        if feather and feather > 0:
            a = out_img.split()[-1].filter(ImageFilter.GaussianBlur(radius=min(feather, 2)))
            out_img.putalpha(a)

        return out_img

    def _remove_background_gray(self, img: Image.Image, tol: int = 18, feather: int = 2) -> Image.Image:
        """
        Flood-fill background removal for GRAYSCALE headshots.
        Uses luminance-only distance with border sampling and auto-tuned tolerance.
        PROTECTS CENTER REGION to avoid removing the subject.
        """
        try:
            import numpy as np
        except ImportError:
            print("   Warning: numpy not available for gray background removal")
            return img.convert("RGBA")

        img = img.convert("RGBA")
        arr = np.array(img)
        H, W = arr.shape[:2]

        # Luminance (even if already grayscale, this is safe)
        lum = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]).astype(np.float32)
        alpha = arr[..., 3].astype(np.uint8)

        # Border-strip background samples in luminance (safer than corners for tight crops)
        bs = max(8, min(H, W) // 25)
        border = np.concatenate([
            lum[:bs, :].ravel(),
            lum[-bs:, :].ravel(),
            lum[:, :bs].ravel(),
            lum[:, -bs:].ravel(),
        ])
        bg = np.median(border)
        dist = np.abs(lum - bg)

        # PROTECT CENTER REGION - don't remove pixels in the center 60% of image
        # This prevents removing the person's face/body
        center_y_start = int(H * 0.2)
        center_y_end = int(H * 0.8)
        center_x_start = int(W * 0.2)
        center_x_end = int(W * 0.8)
        center_protection = np.zeros((H, W), dtype=bool)
        center_protection[center_y_start:center_y_end, center_x_start:center_x_end] = True

        from collections import deque

        def flood(t):
            close = dist <= t
            bg_mask = np.zeros((H, W), dtype=bool)
            q = deque()

            def push(y, x):
                # Check bounds FIRST before accessing arrays
                if not (0 <= y < H and 0 <= x < W):
                    return
                # CRITICAL: Don't flood into center region (protects subject)
                if center_protection[y, x]:
                    return
                if close[y, x] and not bg_mask[y, x]:
                    bg_mask[y, x] = True
                    q.append((y, x))

            # Only start flood from borders (not center)
            for x in range(W):
                push(0, x); push(H - 1, x)
            for y in range(H):
                push(y, 0); push(y, W - 1)

            while q:
                y, x = q.popleft()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        push(y + dy, x + dx)

            return bg_mask

        # More aggressive tolerance to match rembg performance (40-50% removal for headshots)
        tol_candidates = [8, 12, 15, 18, 20, 25, 30]
        best_mask = None
        best_score = None
        best_t = tol_candidates[0]

        for t in tol_candidates:
            mask = flood(t)
            removed = mask.mean()
            # Target 40-45% removal (normal for headshots - person is 50-60% of image)
            target_removal = 0.42
            score = abs(removed - target_removal)
            if best_score is None or score < best_score:
                best_score = score
                best_mask = mask
                best_t = t
            # Stop early if we get good removal (35-50% is ideal for headshots)
            if 0.35 <= removed <= 0.50:
                break

        removed_frac = best_mask.mean()
        
        # Safety check: ensure we didn't remove too much from center
        center_removed = (best_mask & center_protection).sum() / center_protection.sum()
        if center_removed > 0.05:  # If >5% of center was removed, that's bad
            print(f"   WARNING: Removed {center_removed:.1%} from center region - too aggressive!")
            # Use even more conservative mask
            for t in [3, 5, 8]:
                mask = flood(t)
                removed = mask.mean()
                center_rem = (mask & center_protection).sum() / center_protection.sum()
                if center_rem < 0.05 and 0.05 <= removed <= 0.20:
                    best_mask = mask
                    best_t = t
                    removed_frac = removed
                    print(f"   Using ultra-conservative tolerance: tol={best_t}, removed={removed_frac:.1%}, center={center_rem:.1%}")
                    break
        
        print(f"   Gray BG removal: tol={best_t}, removed={removed_frac:.1%}")
        
        # Final safety: if we removed too much overall (>60%), be more conservative
        # Note: 40-50% removal is normal for headshots (person is 50-60% of image)
        if removed_frac > 0.60:
            print(f"   WARNING: Removed too much overall ({removed_frac:.1%}), using minimal removal...")
            # Try with very low tolerance
            for t in [3, 5, 8]:
                mask = flood(t)
                removed = mask.mean()
                if 0.05 <= removed <= 0.50:  # Allow up to 50% removal (normal for headshots)
                    best_mask = mask
                    best_t = t
                    removed_frac = removed
                    print(f"   Using minimal tolerance: tol={best_t}, removed={removed_frac:.1%}")
                    break

        new_alpha = alpha.copy()
        new_alpha[best_mask] = 0

        out = arr.copy()
        out[..., 3] = new_alpha
        out_img = Image.fromarray(out, "RGBA")

        if feather and feather > 0:
            a = out_img.split()[-1].filter(ImageFilter.GaussianBlur(radius=min(feather, 2)))
            out_img.putalpha(a)

        return out_img

    def _alpha_stats(self, im: Image.Image):
        """Return (opaque_frac, transparent_frac, mean_alpha)."""
        a = np.array(im.split()[-1], dtype=np.uint8)
        opaque = (a > 200).mean()
        transparent = (a < 10).mean()
        return float(opaque), float(transparent), float(a.mean())

    def _remove_bg_rembg(self, rgba_img: Image.Image) -> Optional[Image.Image]:
        """
        Local ML segmentation using rembg (minimal, no post-processing).
        Uses cached session to avoid reloading model on every request.
        """
        try:
            import warnings
            # Suppress onnxruntime GPU warnings (Render doesn't have GPU)
            warnings.filterwarnings('ignore', category=UserWarning, module='onnxruntime')
            
            from rembg import remove, new_session
            
            # Use cached session if available, otherwise create new one
            if HTMLSlideGenerator._rembg_session is None:
                # Suppress stderr during model loading to reduce log noise
                import sys
                import os
                old_stderr = sys.stderr
                devnull = open(os.devnull, 'w')
                try:
                    sys.stderr = devnull
                    HTMLSlideGenerator._rembg_session = new_session('u2net')
                finally:
                    sys.stderr = old_stderr
                    devnull.close()
                print("   rembg session initialized (model loaded)")

            buf = io.BytesIO()
            rgba_img.save(buf, format="PNG")
            input_data = buf.getvalue()

            out = remove(input_data, session=HTMLSlideGenerator._rembg_session)

            out_img = Image.open(io.BytesIO(out)).convert("RGBA")
            out_img.load()
            return out_img
        except Exception as e:
            print(f"   rembg failed: {e}")
            return None

    def _to_grayscale_preserve_alpha(self, img: Image.Image) -> Image.Image:
        """
        Convert to grayscale while preserving alpha channel.
        """
        r, g, b, a = img.split()
        gray = img.convert("L")
        return Image.merge("RGBA", (gray, gray, gray, a))

    def _enforce_alpha_floor(self, img: Image.Image, floor: int = 50) -> Image.Image:
        """
        Ensure non-zero alpha pixels are at least 'floor' to avoid disappearing cutouts.
        """
        try:
            a = np.array(img.split()[-1], dtype=np.uint8)
            mask = a > 0
            a[mask] = np.maximum(a[mask], floor)
            a_img = Image.fromarray(a, 'L')
            r, g, b, _ = img.split()
            return Image.merge("RGBA", (r, g, b, a_img))
        except Exception:
            return img

    def _strengthen_alpha(self, img: Image.Image, thresh: int = 25, boost: float = 2.0) -> Image.Image:
        """
        Make weak alpha masks usable:
        - zero tiny alpha (background)
        - boost remaining alpha (foreground)
        """
        try:
            img = img.convert("RGBA")
            arr = np.array(img)
            a = arr[..., 3].astype(np.float32)
            a[a < thresh] = 0
            a = np.clip(a * boost, 0, 255)
            arr[..., 3] = a.astype(np.uint8)
            return Image.fromarray(arr, "RGBA")
        except Exception:
            return img


    def _remove_bg_openai(self, path: str) -> Optional[Image.Image]:
        """
        Optional AI background removal using OpenAI images.edit.
        Safe to call even if SDK or key is missing.
        """
        try:
            from openai import OpenAI
        except Exception:
            # SDK not installed
            return None

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Try Config if available
            try:
                from config import Config
                api_key = getattr(Config, "OPENAI_API_KEY", None)
            except Exception:
                api_key = None
        if not api_key:
            return None

        try:
            client = OpenAI(api_key=api_key)
            # Important: pass a file handle so mimetype is recognized (not octet-stream)
            with open(path, "rb") as f:
                resp = client.images.edit(
                    model="gpt-image-1",
                    image=f,
                    prompt="Remove the background; return transparent PNG of the person.",
                    size="1024x1024",
                    output_format="png",
                )

            if not resp or not getattr(resp, "data", None):
                return None

            out_b64 = resp.data[0].b64_json
            if not out_b64:
                return None

            import base64
            out_bytes = base64.b64decode(out_b64)
            out_img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
            out_img.load()
            return out_img
        except Exception as e:
            print(f"   OpenAI bg removal failed: {e}")
            return None


    def _darken_edges(self, img: Image.Image) -> Image.Image:
        """
        Gently darkens only semi-transparent edge pixels to reduce white halo.
        Does NOT darken fully opaque pixels (avoids making the whole face dark).
        """
        try:
            import numpy as np
        except ImportError:
            return img
        arr = np.array(img)
        rgb = arr[..., :3].astype(np.float32)
        a = arr[..., 3].astype(np.float32) / 255.0

        # Only darken semi-transparent edge band (not fully opaque pixels)
        edge = (a > 0.02) & (a < 0.85)

        # Gentle darken: factor stays between 0.7..1.0 based on alpha
        factor = 0.7 + 0.3 * a
        rgb[edge] *= factor[edge][..., None]

        out = arr.copy()
        out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        return Image.fromarray(out, "RGBA")

    def _fix_alpha_mask(self, img: Image.Image, a_min: int = 8) -> Image.Image:
        """
        Safe version: keeps largest blob, fills holes, hardens alpha.
        Has guards to avoid nuking the entire image if alpha is soft.
        """
        arr = np.array(img.convert("RGBA"))
        a = arr[..., 3].astype(np.uint8)
        H, W = a.shape

        # If almost nothing is non-zero alpha, don't touch it
        if (a > 0).mean() < 0.01:
            print("   _fix_alpha_mask: alpha mostly empty, skipping")
            return img

        fg = (a > a_min)

        # If fg is too small, lower threshold automatically (common for soft masks)
        if fg.mean() < 0.01:
            a_min2 = max(1, a_min // 2)
            fg = (a > a_min2)
            print(f"   _fix_alpha_mask: fg too small, lowering a_min {a_min}->{a_min2}")

        # Still nothing? skip.
        if fg.mean() < 0.005:
            print("   _fix_alpha_mask: fg still too small, skipping")
            return img

        visited = np.zeros((H, W), dtype=bool)
        best_coords = None
        best_size = 0
        from collections import deque

        for y0 in range(H):
            for x0 in range(W):
                if fg[y0, x0] and not visited[y0, x0]:
                    q = deque([(y0, x0)])
                    visited[y0, x0] = True
                    coords = []
                    while q:
                        y, x = q.popleft()
                        coords.append((y, x))
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                if dy == 0 and dx == 0:
                                    continue
                                ny, nx = y + dy, x + dx
                                if 0 <= ny < H and 0 <= nx < W and fg[ny, nx] and not visited[ny, nx]:
                                    visited[ny, nx] = True
                                    q.append((ny, nx))
                    if len(coords) > best_size:
                        best_size = len(coords)
                        best_coords = coords

        # If we failed to find a component (or it's tiny), don't touch the image
        if not best_coords or best_size < int(0.01 * H * W):
            print(f"   _fix_alpha_mask: best component too small ({best_size}), skipping")
            return img

        keep = np.zeros((H, W), dtype=bool)
        ys, xs = zip(*best_coords)
        keep[np.array(ys), np.array(xs)] = True

        # Fill holes: background regions not connected to border
        bg = ~keep
        hole = bg.copy()
        q = deque()

        def push(y, x):
            if 0 <= y < H and 0 <= x < W and hole[y, x]:
                hole[y, x] = False
                q.append((y, x))

        for x in range(W):
            push(0, x); push(H - 1, x)
        for y in range(H):
            push(y, 0); push(y, W - 1)

        while q:
            y, x = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    push(y + dy, x + dx)

        filled = keep | hole

        new_a = a.copy()
        new_a[~filled] = 0

        # Mild harden (avoid killing soft hair)
        # map [0..255] to [0..255] with a small lift
        new_a = np.clip((new_a.astype(np.int16) - 5) * 255 // (255 - 5), 0, 255).astype(np.uint8)

        arr[..., 3] = new_a
        return Image.fromarray(arr, "RGBA")

    def _fallback_original_headshot(self, path: str, max_size: int = 1500) -> Optional[Image.Image]:
        """Return a safe grayscale RGBA version of the original image (no bg removal)."""
        try:
            img = Image.open(path).convert("RGBA")
            img.load()
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            r, g, b, a = img.split()
            gray = img.convert("L")
            return Image.merge("RGBA", (gray, gray, gray, a))
        except Exception as e:
            print(f"Warning: fallback original headshot failed: {e}")
            return None


    def _resize_cover(self, im: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """
        Scale UP or DOWN to completely fill (target_w, target_h) while preserving aspect ratio,
        then center-crop to exact size. (Like CSS background-size: cover)
        """
        im = im.convert("RGBA")
        w, h = im.size
        if w == 0 or h == 0:
            return im

        scale = max(target_w / w, target_h / h)  # cover => fill box
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Center crop to exact target size
        left = max(0, (new_w - target_w) // 2)
        top = max(0, (new_h - target_h) // 2)
        return im.crop((left, top, left + target_w, top + target_h))

    def _refine_edges(self, img: Image.Image, erode_size: int = 3, blur_radius: float = 1.0) -> Image.Image:
        """
        Shrinks the alpha mask (erode) to remove halos, then softens the edge.
        """
        r, g, b, a = img.split()
        if erode_size > 0:
            a = a.filter(ImageFilter.MinFilter(erode_size))
        if blur_radius > 0:
            a = a.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        img.putalpha(a)
        return img

    def _remove_bg_best_effort(self, path: str, use_api: bool) -> Image.Image:
        """
        Best-effort background removal:
        1) remove.bg API if available
        2) local rembg segmentation
        3) conservative grayscale flood-fill as last resort
        """
        img = Image.open(path).convert("RGBA")
        img.load()

        # Downscale before anything expensive
        max_size = 1500
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # 1) remove.bg API (if available)
        if use_api:
            try:
                from image_processor import ImageProcessor
                print(f"   Removing background via API for {path} ...")
                b = ImageProcessor.remove_background(path)
                if b:
                    api_img = Image.open(io.BytesIO(b)).convert("RGBA")
                    api_img.load()
                    o, t, ma = self._alpha_stats(api_img)
                    print(f"   API alpha stats: opaque={o:.2f}, transp={t:.2f}, meanA={ma:.0f}")
                    if o > 0.10 and t > 0.10:
                        return api_img
            except Exception as e:
                print(f"   API removal failed: {e}")

        # 2) OpenAI images.edit (optional, if key + SDK available) — now a backup
        openai_img = self._remove_bg_openai(path)
        if openai_img is not None:
            o, t, ma = self._alpha_stats(openai_img)
            print(f"   OpenAI alpha stats: opaque={o:.2f}, transp={t:.2f}, meanA={ma:.0f}")
            if o > 0.10 and t > 0.10:
                return openai_img

        # 3) local rembg
        rembg_img = self._remove_bg_rembg(img)
        if rembg_img is not None:
            o, t, ma = self._alpha_stats(rembg_img)
            print(f"   rembg alpha stats: opaque={o:.2f}, transp={t:.2f}, meanA={ma:.0f}")
            if o > 0.10 and t > 0.10:
                return rembg_img

        # 4) Last resort: conservative flood-fill for studio backgrounds (protects center/subject)
        ff = self._remove_background_gray(img, tol=8, feather=1)
        o, t, ma = self._alpha_stats(ff)
        print(f"   floodfill alpha stats: opaque={o:.2f}, transp={t:.2f}, meanA={ma:.0f}")
        return ff
    
    def _detect_orange_us_bbox(self, img: Image.Image):
        """
        Detect the orange US map outline bbox in the template.
        Restricts search to the TOP-RIGHT region to avoid the orange sidebar.
        Returns (x0, y0, w, h). Falls back if it fails.
        """
        try:
            W, H = img.size
            arr = np.array(img.convert("RGB"))
            
            # --- ROI: where the map is on your template ---
            # tune these if needed, but this matches your layout (map is top-right)
            x_start = int(W * 0.55)
            x_end   = int(W * 0.99)
            y_start = int(H * 0.02)
            y_end   = int(H * 0.45)
            
            roi = arr[y_start:y_end, x_start:x_end]
            r, g, b = roi[..., 0], roi[..., 1], roi[..., 2]
            
            # Orange outline is bright orange lines, not a solid block:
            # loosen thresholds a bit so thin lines still count
            orange_mask = (r > 160) & (g > 80) & (g < 210) & (b < 140)
            
            ys, xs = np.where(orange_mask)
            if len(xs) < 300:  # thin outlines -> fewer pixels; don't require 2000
                print(f"   Warning: Only {len(xs)} orange pixels in ROI, using fallback bbox")
                return (1250, 110, 620, 450)
            
            # bbox in ROI coords
            x0r, x1r = int(xs.min()), int(xs.max())
            y0r, y1r = int(ys.min()), int(ys.max())
            
            # Convert ROI bbox back to full-image coords
            x0 = x_start + x0r
            x1 = x_start + x1r
            y0 = y_start + y0r
            y1 = y_start + y1r
            
            pad = 10
            x0 = max(0, x0 - pad)
            y0 = max(0, y0 - pad)
            x1 = min(W - 1, x1 + pad)
            y1 = min(H - 1, y1 + pad)
            
            print(f"   Detected MAP bbox (ROI): ({x0}, {y0}, {x1-x0}, {y1-y0})")
            return (x0, y0, x1 - x0, y1 - y0)
        except Exception as e:
            print(f"   Warning: Error detecting orange bbox: {e}, using fallback")
            return (1250, 110, 620, 450)
    
    @lru_cache(maxsize=256)
    def _geocode_city(self, city: str):
        """
        Geocode city name to (lat, lon) using geopy.
        Returns (lat, lon) or None.
        Cached to avoid rate limits and improve performance.
        """
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="slide_pin_placer")
            # Bias to US
            loc = geolocator.geocode(f"{city}, USA", country_codes="us", timeout=3)
            if not loc:
                return None
            print(f"   Geocoded '{city}' to ({loc.latitude}, {loc.longitude})")
            return (loc.latitude, loc.longitude)
        except ImportError:
            print(f"   Warning: geopy not installed, cannot geocode '{city}'")
            return None
        except Exception as e:
            print(f"   Warning: Geocoding failed for '{city}': {e}")
            return None
    
    def _fallback_latlon(self, city: str):
        """
        Fallback lat/lon for common cities and all US state capitals when geopy isn't available.
        Uses real coordinates (no nudges) except for LA which is intentionally shifted.
        Note: AK/HI coordinates will clamp to contiguous US bounds unless handled specially.
        """
        # Parse city name - handle both "City, State" and "City State" formats
        parts = city.lower().split(',')
        city_part = parts[0].strip()
        state_part = parts[1].strip() if len(parts) > 1 else ""
        
        LATLON = {
            # Keep these as-is per your request (even though LA is intentionally shifted)
            "los angeles": (34.0522, -118.5),  # intentionally shifted
            "san francisco": (37.7749, -122.4194),
            "miami": (25.7617, -80.1918),
            "new york": (40.7128, -74.0060),
            "new york city": (40.7128, -74.0060),
            
            # Major cities
            "seattle": (47.6062, -122.3321),
            "boston": (42.3601, -71.0589),
            "chicago": (41.8781, -87.6298),
            "new orleans": (29.9511, -90.0715),
            
            # US State Capitals (standard coords)
            "montgomery": (32.3668, -86.3000),        # AL
            "juneau": (58.3019, -134.4197),           # AK  (needs special handling on contiguous map)
            "phoenix": (33.4484, -112.0740),          # AZ
            "little rock": (34.7465, -92.2896),       # AR
            "sacramento": (38.5816, -121.4944),       # CA
            "denver": (39.7392, -104.9903),           # CO
            "hartford": (41.7658, -72.6734),          # CT
            "dover": (39.1582, -75.5244),             # DE
            "tallahassee": (30.4383, -84.2807),       # FL
            "atlanta": (33.7490, -84.3880),           # GA
            "honolulu": (21.3069, -157.8583),         # HI  (needs special handling on contiguous map)
            "boise": (43.6150, -116.2023),            # ID
            "springfield": (39.7817, -89.6501),       # IL (capital)
            "indianapolis": (39.7684, -86.1581),      # IN
            "des moines": (41.5868, -93.6250),        # IA
            "topeka": (39.0473, -95.6752),            # KS
            "frankfort": (38.2009, -84.8733),         # KY
            "baton rouge": (30.4515, -91.1871),       # LA
            "augusta": (44.3106, -69.7795),           # ME (capital)  <-- note ambiguity with Augusta, GA
            "annapolis": (38.9784, -76.4922),         # MD
            "lansing": (42.7325, -84.5555),           # MI
            "saint paul": (44.9537, -93.0900),        # MN
            "st. paul": (44.9537, -93.0900),          # MN alias
            "jackson": (32.2988, -90.1848),           # MS
            "jefferson city": (38.5767, -92.1735),    # MO
            "helena": (46.5891, -112.0391),           # MT
            "lincoln": (40.8136, -96.7026),           # NE
            "carson city": (39.1638, -119.7674),      # NV
            "concord": (43.2081, -71.5376),           # NH
            "trenton": (40.2171, -74.7429),           # NJ
            "santa fe": (35.6870, -105.9378),         # NM
            "albany": (42.6526, -73.7562),            # NY (capital)
            "raleigh": (35.7796, -78.6382),           # NC
            "bismarck": (46.8083, -100.7837),         # ND
            "columbus": (39.9612, -82.9988),          # OH
            "oklahoma city": (35.4676, -97.5164),     # OK
            "salem": (44.9429, -123.0351),            # OR
            "harrisburg": (40.2732, -76.8867),        # PA
            "providence": (41.8240, -71.4128),        # RI
            "columbia": (34.0007, -81.0348),          # SC (capital)
            "pierre": (44.3683, -100.3510),           # SD
            "nashville": (36.1627, -86.7816),         # TN
            "austin": (30.2672, -97.7431),            # TX
            "salt lake city": (40.7608, -111.8910),   # UT
            "montpelier": (44.2601, -72.5754),        # VT
            "richmond": (37.5407, -77.4360),          # VA
            "olympia": (47.0379, -122.9007),          # WA
            "charleston": (38.3498, -81.6326),        # WV (capital) -- ambiguous with Charleston, SC city
            "madison": (43.0748, -89.3848),           # WI
            "cheyenne": (41.1400, -104.8202),         # WY
            
            # Optional disambiguation aliases (HIGHLY recommended)
            "augusta me": (44.3106, -69.7795),
            "augusta ga": (33.4735, -82.0105),
            "charleston wv": (38.3498, -81.6326),
            "charleston sc": (32.7765, -79.9311),
        }
        
        # Try disambiguation key first (e.g., "augusta me", "charleston wv")
        if state_part:
            # Map common state abbreviations to full state names for disambiguation
            state_map = {
                "me": "me", "maine": "me",
                "ga": "ga", "georgia": "ga",
                "wv": "wv", "west virginia": "wv",
                "sc": "sc", "south carolina": "sc"
            }
            state_key = state_map.get(state_part, "")
            if state_key:
                disambiguation_key = f"{city_part} {state_key}"
                if disambiguation_key in LATLON:
                    return LATLON[disambiguation_key]
        
        # Fall back to city name only
        key = city_part
        return LATLON.get(key)
    
    
    def _latlon_to_map_xy(self, lat: float, lon: float, map_x: int, map_y: int, map_w: int, map_h: int):
        """
        Improved lat/lon to map coordinate conversion with calibration support.
        Uses known city positions to calibrate the projection.
        """
        # More accurate contiguous US bounds
        lon_min, lon_max = -124.5, -67.0  # Adjusted for better accuracy
        lat_min, lat_max = 25.0, 49.0
        
        # Adjust padding to match the actual map borders in your template
        # You may need to fine-tune these based on your specific template
        PAD_L = 0.03  # Left padding
        PAD_R = 0.05  # Right padding  
        PAD_T = 0.08  # Top padding (increased to lower West Coast cities)
        PAD_B = 0.08  # Bottom padding
        
        inner_x = map_x + int(map_w * PAD_L)
        inner_y = map_y + int(map_h * PAD_T)
        inner_w = int(map_w * (1.0 - PAD_L - PAD_R))
        inner_h = int(map_h * (1.0 - PAD_T - PAD_B))
        
        # Clamp to bounds
        lon = max(lon_min, min(lon_max, lon))
        lat = max(lat_min, min(lat_max, lat))
        
        # Equirectangular projection
        x_norm = (lon - lon_min) / (lon_max - lon_min)
        y_norm = 1.0 - (lat - lat_min) / (lat_max - lat_min)
        
        x = inner_x + int(x_norm * inner_w)
        y = inner_y + int(y_norm * inner_h)
        
        return x, y
    
    def calibrate_map_projection(self, template_path: str):
        """
        Helper to calibrate map projection by testing known cities.
        Run this once to find the best padding values.
        """
        template = self._pdf_to_image(template_path) if template_path.endswith('.pdf') else Image.open(template_path)
        template.load()  # Load fully before resize to avoid memory issues
        template = template.resize((1920, 1080), Image.Resampling.LANCZOS)
        
        map_x, map_y, map_w, map_h = self._detect_orange_us_bbox(template)
        
        # Test cities with known positions
        test_cities = {
            'Los Angeles': (34.0522, -118.2437),
            'New York': (40.7128, -74.0060),
            'Chicago': (41.8781, -87.6298),
            'Miami': (25.7617, -80.1918),
            'Seattle': (47.6062, -122.3321),
        }
        
        print(f"\nMap bounds: x={map_x}, y={map_y}, w={map_w}, h={map_h}")
        print("\nTesting pin positions:")
        for city, (lat, lon) in test_cities.items():
            x, y = self._latlon_to_map_xy(lat, lon, map_x, map_y, map_w, map_h)
            print(f"{city:15} -> ({x}, {y})")
        
        # Draw test pins on template
        test_img = template.copy()
        draw = ImageDraw.Draw(test_img)
        for city, (lat, lon) in test_cities.items():
            x, y = self._latlon_to_map_xy(lat, lon, map_x, map_y, map_w, map_h)
            draw.ellipse([(x-10, y-10), (x+10, y+10)], fill=(255, 0, 0))
            draw.text((x+15, y-10), city, fill=(255, 0, 0))
        
        test_img.save('map_calibration_test.png')
        print("\nSaved test image to: map_calibration_test.png")
        print("Check if pins are in correct positions and adjust PAD_L, PAD_R, PAD_T, PAD_B values")
    
    def _parse_headshots(self, headshot_path):
        """
        Accepts:
          - single path string
          - comma-separated string "a.png,b.png"
          - list/tuple of paths
        Returns list[str]
        """
        if not headshot_path:
            return []
        if isinstance(headshot_path, (list, tuple)):
            return [p for p in headshot_path if p]
        if isinstance(headshot_path, str) and "," in headshot_path:
            return [p.strip() for p in headshot_path.split(",") if p.strip()]
        return [headshot_path]
    
    def _get_city_coordinates(self, city_name: str) -> tuple:
        """
        Get normalized coordinates (0-1) for US cities on a map.
        Returns (x, y) where x is 0 (west) to 1 (east), y is 0 (north) to 1 (south).
        FALLBACK ONLY - prefer using _geocode_city + _latlon_to_map_xy
        """
        # Normalize city name
        city_lower = city_name.lower().split(',')[0].strip()
        
        # Approximate US city positions (normalized coordinates) - Fallback only
        city_positions = {
            # West Coast
            'san francisco': (0.05, 0.42),
            'los angeles': (0.10, 0.60),
            'san diego': (0.10, 0.70),
            'seattle': (0.08, 0.20),
            'portland': (0.09, 0.25),
            # East Coast
            'new york': (0.92, 0.35),
            'boston': (0.95, 0.30),
            'philadelphia': (0.90, 0.38),
            'washington': (0.88, 0.40),
            'miami': (0.93, 0.80),
            'atlanta': (0.80, 0.60),
            # Central
            'chicago': (0.65, 0.35),
            'dallas': (0.48, 0.72),
            'houston': (0.50, 0.75),
            'austin': (0.48, 0.72),
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

    def create_slide(self, company_data: Dict, headshot_path: str, logo_path: str, map_path: Optional[str] = None, output_format: str = "pdf") -> bytes:
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
            template.load()  # Load fully before resize to avoid memory issues
        
        # Resize to standard slide size if needed
        if template.size != (1920, 1080):
            template = template.resize((1920, 1080), Image.Resampling.LANCZOS)
        
        # Create a copy to work with
        slide = template.copy()
        draw = ImageDraw.Draw(slide)
        width, height = slide.size
        
        # Load fonts (robust fallbacks for Render/Railway)
        name_font = self._load_font(140, bold=True)
        # Body text under Founders / Co-Investors / Background: Inter 28pt Regular
        body_font = self._load_font(28, bold=False, preferred_family="Inter_28pt-Regular")
        small_font = self._load_font(20, bold=False, preferred_family="Inter_28pt-Regular")
        sidebar_font = self._load_font(28)
        
        # Extract company data
        company_name = company_data.get('name', '').upper()
        # Hard caps to avoid overflow into other regions:
        # - Founders: max 3 names
        # - Co-investors: max 5 names
        founders_items = self._parse_name_list(company_data.get("founders", ""))[:3]
        co_investors_items = self._parse_name_list(company_data.get("co_investors", ""))[:5]

        founders_text = "\n".join(founders_items)
        co_investors_text = "\n".join(co_investors_items)
        
        background_text = company_data.get('background', company_data.get('description', ''))
        # Extract city + state from address - handle formats like
        # "123 Innovation Drive, San Francisco, CA 94105" -> "San Francisco, CA"
        full_address = company_data.get('address', company_data.get('location', 'Los Angeles'))
        # Try to extract city + state (or fall back to whatever we were given)
        if ',' in full_address:
            parts = [p.strip() for p in full_address.split(',')]
            # If address has 3+ parts, city is usually the second part (street, city, state/zip)
            if len(parts) >= 3:
                city = parts[1]  # e.g., "San Francisco"
                # parts[2] is typically "CA 94105" (or "CA"). Keep only the state token.
                state_token = (parts[2].split() or [""])[0].strip()
                if state_token:
                    location = f"{city}, {state_token}"
                else:
                    location = city
            else:
                # If we only have 2 parts (e.g., "San Francisco, CA"), keep both.
                location = ", ".join([p for p in parts[:2] if p])
        else:
            location = full_address
        
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
        
        # Detect orange US map bounding box from template (restricted to top-right ROI)
        # Do this once and reuse for both company name overlap detection and map pin placement
        map_area_x, map_area_y, map_width, map_height = self._detect_orange_us_bbox(template)
        
        # Company name position: left aligned with founders, with a consistent top margin.
        name_x = founders_text_x - 60  # Slightly more left breathing room
        desired_title_top = 95  # Keep title visually aligned regardless of font size (smaller = lower baseline)
        
        # Use orange color for title
        # Requested: #FF9100
        name_color = (255, 145, 0)
        
        # Dynamic font sizing:
        # - Try a larger default for short names (e.g., ASTRANIS) so it feels premium.
        # - If it would overlap with the map region, shrink until it fits (existing behavior).
        name_len = len(company_name.strip())
        if name_len <= 10:
            base_font_size = 230
        elif name_len <= 14:
            base_font_size = 220
        else:
            base_font_size = 185
        name_font_size = base_font_size
        
        # Calculate text width with base font to check for overlap
        # Title font: prefer Bebas Neue if available (bundled or installed), otherwise fall back.
        # Use BebasNeue-Regular.ttf (non-italic, regular face) when available.
        test_font = self._load_font(name_font_size, bold=False, preferred_family="BebasNeue")
        text_bbox = draw.textbbox((0, 0), company_name, font=test_font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # If text would overlap with map, reduce font size until it fits.
        # Keep it as large as possible (less aggressive reduction than before).
        max_allowed_width = map_area_x - name_x - 90  # Leave margin before map
        while text_width > max_allowed_width and name_font_size > 60:
            # Reduce by 5% each iteration for smoother sizing (keeps text bigger)
            name_font_size = int(name_font_size * 0.95)
            test_font = self._load_font(name_font_size, bold=False, preferred_family="BebasNeue")
            text_bbox = draw.textbbox((0, 0), company_name, font=test_font)
            text_width = text_bbox[2] - text_bbox[0]
        
        # Prefer a larger minimum size, but only if it still fits.
        desired_min_size = 100
        if name_font_size < desired_min_size:
            min_font = self._load_font(desired_min_size, bold=False, preferred_family="BebasNeue")
            min_bbox = draw.textbbox((0, 0), company_name, font=min_font)
            min_width = min_bbox[2] - min_bbox[0]
            if min_width <= max_allowed_width:
                name_font_size = desired_min_size
        
        # Hard floor so it never becomes unreadably tiny
        name_font_size = max(80, name_font_size)
        if name_font_size < base_font_size:
            print(f"   Company name too long ({len(company_name)} chars), reduced font size to {name_font_size}px to avoid map overlap")
        
        # Use very thick, bold font (matching the image style - extra thick and bold)
        name_font = self._load_font(name_font_size, bold=False, preferred_family="BebasNeue")

        # Compute Y from font bbox so the visual top stays consistent across font sizes.
        try:
            final_bbox = draw.textbbox((0, 0), company_name, font=name_font)
            final_text_width = final_bbox[2] - final_bbox[0]

            # If the title did NOT need shrinking to avoid the map, nudge it right a bit so the
            # slide feels less left-heavy (e.g., "Veridyna"). Never let it overlap the map.
            if name_font_size >= base_font_size:
                right_limit_x = map_area_x - 90 - final_text_width  # keep same map margin
                available_shift = right_limit_x - name_x
                if available_shift > 0:
                    # Move a fraction of available gap, capped, with a small minimum threshold.
                    desired_shift = min(60, int(available_shift * 0.35))
                    if desired_shift >= 12:
                        name_x = int(name_x + desired_shift)
            name_y = int(desired_title_top - final_bbox[1])
        except Exception:
            name_y = 110

        if os.getenv("DEBUG_LAYOUT", "").strip() in ("1", "true", "yes", "y", "on"):
            print(
                f"DEBUG_LAYOUT title: '{company_name}' size={name_font_size} "
                f"pos=({name_x},{name_y}) maxW={max_allowed_width} textW={text_width}"
            )
        
        # Draw company name with a very subtle stroke (outline) for contrast.
        # Keep it thin + minimal passes so it doesn't look "bold".
        stroke_width = 1
        # Use alpha for a softer outline (works on RGBA slides).
        stroke_color = (200, 80, 30, 95)
        # Minimal passes to keep it very subtle.
        offsets = [
            (-stroke_width, 0),
            (stroke_width, 0),
        ]
        for dx, dy in offsets:
            draw.text((name_x + dx, name_y + dy), company_name, fill=stroke_color, font=name_font)
        
        # Then draw the main text on top
        draw.text((name_x, name_y), company_name, fill=name_color, font=name_font)
        
        # 2. Replace logo (circular, top right) - fit within circular bounds, higher position, transparent, more circular
        try:
            logo_img = Image.open(logo_path).convert('RGBA')
            # Load image fully before operations to avoid lazy loading issues
            logo_img.load()
            logo_x, logo_y = width - 170, 10  # Raised more (was 20, now 10) to avoid map overlap
            logo_size = 130
            
            # Don't erase background - keep it transparent (no black box)
            # Just paste the logo directly with circular mask
            
            # Create perfectly circular mask first
            circle_mask = Image.new('L', (logo_size, logo_size), 0)
            circle_draw = ImageDraw.Draw(circle_mask)
            circle_draw.ellipse([(0, 0), (logo_size, logo_size)], fill=255)
            
            # Resize logo to fill the entire circle (no padding, fill the circle)
            # Center crop to square first
            logo_w, logo_h = logo_img.size
            min_dim = min(logo_w, logo_h)
            logo_img = logo_img.crop(((logo_w - min_dim) // 2, (logo_h - min_dim) // 2, 
                                     (logo_w + min_dim) // 2, (logo_h + min_dim) // 2))
            
            # Resize to fill the entire circle (logo_size x logo_size)
            logo_img = logo_img.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            # Apply circular mask to logo - this makes it truly circular
            logo_masked = Image.new('RGBA', (logo_size, logo_size), (0, 0, 0, 0))
            logo_masked.paste(logo_img, (0, 0))  # Paste at origin, no padding
            logo_masked.putalpha(circle_mask)  # Apply circular mask to make it round
            
            slide.paste(logo_masked, (logo_x, logo_y), logo_masked)
            draw = ImageDraw.Draw(slide)
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
        
        # 3. Updated Map Logic - Map is already in template, just add location text and adjust pin position
        try:
            # Reuse map bbox detected earlier (for company name overlap detection)
            # map_area_x, map_area_y, map_width, map_height already set above
            
            # Get lat/lon for city
            # Special case: Override Los Angeles to use adjusted coordinates (moved left)
            location_lower = location.lower().strip()
            if "los angeles" in location_lower or location_lower == "la":
                latlon = (34.0522, -118.5)  # Adjusted longitude to move pin left
            else:
                latlon = self._geocode_city(location) or self._fallback_latlon(location)
                if not latlon:
                    latlon = (39.5, -98.35)  # fallback center US
            
            # Debug prints to confirm bbox detection
            print(f"   DEBUG map bbox: ({map_area_x}, {map_area_y}, {map_width}, {map_height})")
            print(f"   DEBUG location: {location}, latlon: {latlon}")
            
            # Note: AK (Juneau) and HI (Honolulu) coordinates will be clamped to contiguous US bounds
            # in _latlon_to_map_xy, so they won't appear accurately on the map. Consider skipping
            # pin placement for these states or implementing inset logic if needed.
            lat, lon = latlon
            pin_x, pin_y = self._latlon_to_map_xy(lat, lon, map_area_x, map_area_y, map_width, map_height)
            # REMOVED: pin_y -= 6  # Remove aesthetic offset as it causes inaccuracy
            
            print(f"   PIN: ({pin_x}, {pin_y})")
            
            # Resolve project root once (used for custom pin + label assets)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir) if os.path.basename(script_dir) == "src" else script_dir

            # Use a custom marker icon if available (recommended).
            pin_icon = self._load_map_pin_icon(project_root)
            # Force marker + label pill to requested yellow: #FFF200
            marker_rgb = (255, 242, 0)

            if pin_icon:
                # Resize while preserving aspect ratio (anchor bottom-center on pin_x/pin_y).
                target_h = 64
                scale = target_h / float(pin_icon.size[1])
                target_w = max(1, int(pin_icon.size[0] * scale))
                pin_icon = pin_icon.resize((target_w, target_h), Image.Resampling.LANCZOS)
                # Tint the icon to the requested color for consistency.
                try:
                    pin_icon = self._tint_rgba_to_color(pin_icon, marker_rgb)
                except Exception:
                    pass
                w, h = pin_icon.size
                paste_pin_x = int(pin_x - w / 2)
                paste_pin_y = int(pin_y - h)
                slide.paste(pin_icon, (paste_pin_x, paste_pin_y), pin_icon)
                draw = ImageDraw.Draw(slide)
            else:
                # Fallback: draw the pin (yellow location pin icon - teardrop shape with circular hole)
                yellow = (255, 242, 0)  # #FFF200
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
                
                # Paste the pin onto the main slide so the bottom tip lands on (pin_x, pin_y)
                paste_pin_x = pin_x - pin_img_size // 2
                paste_pin_y = pin_y - pin_img_size // 2
                # Move image up so the bottom tip hits (pin_x, pin_y) instead of centering
                paste_pin_y -= int(pin_img_size * 0.20)  # Adjust 0.18-0.25 if needed
                slide.paste(pin_img, (paste_pin_x, paste_pin_y), pin_img)
                draw = ImageDraw.Draw(slide)
            
            # Place the city name label with yellow block (similar to other yellow blocks)
            yellow = (255, 242, 0)  # #FFF200
            black = (0, 0, 0)  # Black text on yellow background
            
            # Location label font: georgiai.ttf (bundled in assets/fonts)
            location_font = self._load_font(32, bold=False, preferred_family="georgiai")
            location_stroke_width = 1
            
            # Get text dimensions with larger font
            label_bbox = draw.textbbox((0, 0), location, font=location_font, stroke_width=location_stroke_width)
            text_width = label_bbox[2] - label_bbox[0]
            text_height = label_bbox[3] - label_bbox[1]
            
            # Yellow box dimensions (bigger padding for larger text)
            box_padding_x = 24  # Increased from 20
            box_padding_y = 12  # Increased from 10
            box_width = text_width + box_padding_x * 2
            box_height = text_height + box_padding_y * 2
            
            # Position box with more space from pin; raise significantly to avoid being too low
            box_x = pin_x + 40  # More space from pin (was 15, now 40)
            box_y = pin_y - 70  # Raised more (was -50, now -70 to move label higher)
            
            # Make sure box stays within map bounds
            if box_x + box_width > map_area_x + map_width:
                box_x = pin_x - box_width - 40  # Move to the left if it would go outside
            if box_y + box_height > map_area_y + map_height:
                box_y = pin_y - box_height - 20  # Move up if it would go outside
            
            # Draw label background. Prefer custom rounded background image if available.
            label_bg = self._load_location_label_bg(project_root)
            if label_bg:
                bg_resized = self._resize_pill_bg(label_bg, int(box_width), int(box_height))
                # Tint label background to match marker color (when available)
                bg_resized = self._tint_rgba_to_color(bg_resized, marker_rgb)
                slide.paste(bg_resized, (int(box_x), int(box_y)), bg_resized)
                draw = ImageDraw.Draw(slide)
            else:
                # Fallback: plain rectangle
                draw.rectangle([(box_x, box_y), (box_x + box_width, box_y + box_height)], fill=yellow)
            
            # Draw location text in the yellow box (centered with padding)
            text_x = box_x + box_padding_x
            text_y = box_y + box_padding_y
            draw.text(
                (text_x, text_y),
                location,
                fill=black,
                font=location_font,
                stroke_width=location_stroke_width,
                stroke_fill=black
            )
            
        except Exception as e:
            print(f"Warning: Map update failed: {e}")
        
        # 4. Replace Founders text (moved left and down, transparent)
        # Detect yellow block area for founders (left side, below company name)
        founders_block_y = 400  # Approximate Y position of founders yellow block
        founders_text_y = founders_block_y + 15  # Moved down a little
        founders_text_x = 320  # Moved a little to the left (was 350)
        founders_color = self._get_text_color_from_template(template, founders_text_x, founders_text_y, 600, 100)
        
        # Don't erase background - keep it transparent (no black box)
        # Draw founders text (max 3 names)
        founders_lines = founders_text.split('\n') if founders_text else []
        for i, line in enumerate(founders_lines):
            draw.text((founders_text_x, founders_text_y + i * 35), line, fill=founders_color, font=body_font)
        
        # 5. Replace Co-Investors text (separate text box, to the right of founders, aligned with founders height)
        investors_block_y = 500  # Approximate Y position of co-investors yellow block
        investors_text_y = founders_text_y  # Aligned with founders (same height)
        investors_text_x = 650  # Moved to the right of founders (founders is at 320, so co-investors at 650)
        investors_color = self._get_text_color_from_template(template, investors_text_x, investors_text_y, 600, 100)
        
        # Don't erase background - keep it transparent (no black box)
        # Draw co-investors text (max 5 names)
        investors_lines = co_investors_text.split('\n') if co_investors_text else []
        for i, line in enumerate(investors_lines):
            draw.text((investors_text_x, investors_text_y + i * 35), line, fill=investors_color, font=body_font)
        
        # 6. Replace Background text (aligned with founders, wider text area, bigger font, transparent background)
        bg_block_y = 600  # Approximate Y position of background yellow block
        bg_text_y = bg_block_y + 5  # Text starts below yellow block (smaller gap)
        bg_text_x = founders_text_x  # Aligned with founders (moved left from 400 to match founders at 320)
        # Allow background copy to use more horizontal room (without running into the headshot on the right).
        bg_text_width = 800

        # Background font: +2px vs Founders/Co-Investors (slightly bigger)
        bg_font = self._load_font(30, bold=False, preferred_family="Inter_28pt-Regular")
        bg_line_spacing = 37

        words = background_text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=bg_font)
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
        
        # Draw text directly without erasing background (transparent)
        for i, line in enumerate(lines[:10]):
            draw.text((bg_text_x, bg_text_y + i * bg_line_spacing), line, fill=bg_color, font=bg_font)
        
        # 7. Replace headshots (below map, moved left, bigger size, transparent)
        headshot_processed = False
        try:
            from image_processor import ImageProcessor
            
            # First, validate that the headshot file exists and is a valid image
            # If not, skip headshot processing (don't crash the entire slide generation)
            if not headshot_path or not os.path.exists(headshot_path):
                print(f"Warning: Headshot file not found: {headshot_path}, skipping headshot")
                headshot_path = None
            
            if headshot_path:
                # Try to open the original image first to validate it (quick check)
                try:
                    test_img = Image.open(headshot_path)
                    # Don't verify - just check if we can open it (verify is slow)
                    test_img.close()
                except Exception as e:
                    print(f"Warning: Headshot file is not a valid image: {e}, skipping headshot")
                    headshot_path = None
            
            headshot_paths = self._parse_headshots(headshot_path)
            headshot_paths = [p for p in headshot_paths if p and os.path.exists(p)]
            if not headshot_paths:
                print("   Skipping headshot processing (no valid headshot file)")
            else:
                # Remove background from headshot(s) to make them transparent
                use_api_removal = False
                try:
                    from config import Config
                    if hasattr(Config, 'REMOVEBG_API_KEY') and Config.REMOVEBG_API_KEY and Config.REMOVEBG_API_KEY.strip():
                        use_api_removal = True
                except:
                    pass
                
                print("   REMOVEBG_API_KEY not set, using manual background removal" if not use_api_removal else "   Using remove.bg API when available")

                # Headshot target box (smaller to not cover map)
                headshot_area_width = 500   # Reduced from 600 to avoid covering map
                headshot_area_height = 500   # Keep square
                
                # Position below the map, not overlapping
                headshot_area_x = map_area_x + (map_width - headshot_area_width) // 2 - 50  # Centered under map, slightly left
                headshot_area_y = map_area_y + map_height + 55  # Position below map with larger gap (lowered)

                def load_process_headshot(path: str) -> Optional[Image.Image]:
                    try:
                        print(f"    Processing headshot: {path}")
                        
                        # 0) PREPARE ORIGINAL
                        original = Image.open(path).convert("RGBA")
                        # Keep original size reasonable for processing (780x780 target, so 1500 is plenty)
                        if max(original.size) > 1500:
                            original.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
                        
                        # --- HELPER: MAP BACKGROUND FALLBACK ---
                        # If BG removal fails, composite person on top of map to simulate transparency
                        # Try to get map from slide if map_path is not available
                        def get_map_for_background():
                            """Try to get map image from various sources."""
                            # First, try bundled map background image (committed to repo)
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            bundled_map_paths = [
                                os.path.join(script_dir, "assets", "map_background.png"),
                                os.path.join(script_dir, "map_background.png"),
                                os.path.join(os.path.dirname(script_dir), "assets", "map_background.png"),
                            ]
                            for bundled_path in bundled_map_paths:
                                if os.path.exists(bundled_path):
                                    try:
                                        print(f"    Using bundled map background: {bundled_path}")
                                        return Image.open(bundled_path).convert("RGBA")
                                    except Exception as e:
                                        print(f"    Warning: Could not load bundled map: {e}")
                                        continue
                            
                            # Second, try map_path if available
                            if map_path and os.path.exists(map_path):
                                try:
                                    return Image.open(map_path).convert("RGBA")
                                except Exception as e:
                                    print(f"    Warning: Could not load map from map_path: {e}")
                            
                            # Third, try common temp locations
                            import tempfile
                            temp_dir = tempfile.gettempdir()
                            possible_map_paths = [
                                os.path.join(temp_dir, "map.png"),
                                os.path.join(temp_dir, "map_placeholder.png"),
                            ]
                            for possible_path in possible_map_paths:
                                if os.path.exists(possible_path):
                                    try:
                                        return Image.open(possible_path).convert("RGBA")
                                    except:
                                        continue
                            
                            return None
                        
                        def make_map_background(img_in):
                            print("    Applying Transparent Background Fallback...")
                            # 1. Create a square canvas based on smallest dimension
                            w, h = img_in.size
                            d = min(w, h)
                            # Center crop to square
                            left = (w - d) // 2
                            top = (h - d) // 2
                            img_sq = img_in.crop((left, top, left + d, top + d))
                            
                            # 2. Try aggressive background removal with very conservative settings
                            # Use the gray flood-fill with very low tolerance to only remove obvious background
                            try:
                                import numpy as np
                                img_rgba = img_sq.convert("RGBA")
                                arr = np.array(img_rgba)
                                H, W = arr.shape[:2]
                                
                                # Luminance
                                lum = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]).astype(np.float32)
                                alpha = arr[..., 3].astype(np.uint8)
                                
                                # Border samples for background color
                                bs = max(8, min(H, W) // 25)
                                border = np.concatenate([
                                    lum[:bs, :].ravel(),
                                    lum[-bs:, :].ravel(),
                                    lum[:, :bs].ravel(),
                                    lum[:, -bs:].ravel(),
                                ])
                                bg = np.median(border)
                                dist = np.abs(lum - bg)
                                
                                # Very conservative flood-fill - only remove pixels very close to border color
                                # Protect center 70% of image
                                center_y_start = int(H * 0.15)
                                center_y_end = int(H * 0.85)
                                center_x_start = int(W * 0.15)
                                center_x_end = int(W * 0.85)
                                center_protection = np.zeros((H, W), dtype=bool)
                                center_protection[center_y_start:center_y_end, center_x_start:center_x_end] = True
                                
                                from collections import deque
                                def flood(t):
                                    close = dist <= t
                                    bg_mask = np.zeros((H, W), dtype=bool)
                                    q = deque()
                                    
                                    def push(y, x):
                                        # Check bounds FIRST before accessing arrays
                                        if not (0 <= y < H and 0 <= x < W):
                                            return
                                        if center_protection[y, x]:
                                            return
                                        if close[y, x] and not bg_mask[y, x]:
                                            bg_mask[y, x] = True
                                            q.append((y, x))
                                    
                                    for x in range(W):
                                        push(0, x); push(H - 1, x)
                                    for y in range(H):
                                        push(y, 0); push(y, W - 1)
                                    
                                    while q:
                                        y, x = q.popleft()
                                        for dy in (-1, 0, 1):
                                            for dx in (-1, 0, 1):
                                                if dy == 0 and dx == 0:
                                                    continue
                                                push(y + dy, x + dx)
                                    
                                    return bg_mask
                                
                                # Try very low tolerance (3-8) to only remove obvious background
                                best_mask = None
                                for t in [3, 5, 8]:
                                    mask = flood(t)
                                    removed = mask.mean()
                                    if 0.05 <= removed <= 0.25:  # Only remove 5-25% (very conservative)
                                        best_mask = mask
                                        print(f"    ✓ Conservative background removal: tol={t}, removed={removed:.1%}")
                                        break
                                
                                if best_mask is None:
                                    # Use the most conservative mask
                                    best_mask = flood(3)
                                
                                # Apply mask to alpha channel
                                new_alpha = alpha.copy()
                                new_alpha[best_mask] = 0
                                
                                # Create result with transparent background
                                result = arr.copy()
                                result[..., 3] = new_alpha
                                result_img = Image.fromarray(result, "RGBA")
                                
                                # Convert to grayscale while preserving alpha
                                result_gray = result_img.convert("L")
                                alpha_channel = result_img.split()[3]
                                
                                return Image.merge("RGBA", (result_gray, result_gray, result_gray, alpha_channel))
                                
                            except Exception as e:
                                print(f"    ⚠️  Advanced removal failed: {e}, using circular crop with transparent background")
                                # Fallback: circular crop with transparent background
                                mask = Image.new('L', (d, d), 0)
                                draw_mask = ImageDraw.Draw(mask)
                                draw_mask.ellipse((0, 0, d, d), fill=255)
                                img_sq.putalpha(mask)
                                gray = img_sq.convert("L")
                                return Image.merge("RGBA", (gray, gray, gray, mask))

                        # 1) Attempt Background Removal
                        img = self._remove_bg_best_effort(path, use_api=use_api_removal)
                        
                        # Check if background removal returned None
                        if img is None:
                            print(f"    WARNING: Background removal returned None. Using Transparent Background Fallback.")
                            return make_map_background(original)

                        # 2) SAFETY CHECK 1: Did we wipe the image? 
                        # If opacity is < 10%, we deleted too much of the person. Use Circular Fallback.
                        opaque_frac, transp_frac, mean_alpha = self._alpha_stats(img)
                        print(f"    After BG removal: opaque={opaque_frac:.2f}, transp={transp_frac:.2f}, meanA={mean_alpha:.0f}")
                        if opaque_frac < 0.10: 
                            print(f"    WARNING: BG removal wiped image (opaque={opaque_frac:.2f}). Using Transparent Background Fallback.")
                            return make_map_background(original)
                        
                        # 2b) SAFETY CHECK: If we removed too much (<20% of image is person), that's suspicious
                        # Note: 40-50% opaque is actually good for headshots (person) with 50-60% transparent (background)
                        if opaque_frac < 0.20:
                            print(f"    WARNING: Only {opaque_frac:.1%} of image remains - may have removed too much. Using Transparent Background Fallback.")
                            return make_map_background(original)

                        # 3) Only clean up mask if rembg didn't work well (low transparency)
                        # If rembg already gave us good transparency, skip _fix_alpha_mask to avoid wiping it
                        if transp_frac < 0.10:
                            # Background removal was weak, try to clean it up
                            print(f"    Transparency is weak ({transp_frac:.2f}), attempting to clean mask...")
                            img_before_fix = img.copy()
                            img = self._fix_alpha_mask(img, a_min=2)
                            
                            # Check if _fix_alpha_mask made it worse
                            opaque_after, transp_after, mean_after = self._alpha_stats(img)
                            print(f"    After _fix_alpha_mask: opaque={opaque_after:.2f}, transp={transp_after:.2f}, meanA={mean_after:.0f}")
                            
                            # If it made it worse (less opaque), revert
                            if opaque_after < opaque_frac * 0.5:  # Lost more than 50% of opacity
                                print(f"    WARNING: _fix_alpha_mask made it worse, reverting...")
                                img = img_before_fix
                        else:
                            print(f"    Good transparency ({transp_frac:.2f}), skipping _fix_alpha_mask to preserve quality")
                        
                        # 4) Final safety check before processing
                        final_check_o, final_check_t, _ = self._alpha_stats(img)
                        if final_check_o < 0.05:
                            print(f"    WARNING: Image has no subject (opaque={final_check_o:.2f}). Using Transparent Background Fallback.")
                            return make_map_background(original)

                        # 5) Standard Processing (Grayscale + Edges)
                        img = self._to_grayscale_preserve_alpha(img)
                        img = self._refine_edges(img, erode_size=1, blur_radius=0.5)
                        
                        # 6) Harden alpha channel - ensure background is fully transparent (0) and foreground is fully opaque (255)
                        # This prevents semi-transparent halos when compositing
                        try:
                            import numpy as np
                            arr = np.array(img)
                            alpha = arr[..., 3].astype(np.uint8)
                            # Threshold: pixels with alpha < 128 become fully transparent (0), >= 128 become fully opaque (255)
                            # This creates a clean cutout without semi-transparent edges
                            alpha_hard = np.where(alpha < 128, 0, 255).astype(np.uint8)
                            arr[..., 3] = alpha_hard
                            img = Image.fromarray(arr, "RGBA")
                            print(f"    Hardened alpha channel (threshold=128) to ensure clean transparency")
                        except Exception as e:
                            print(f"    Warning: Could not harden alpha: {e}")
                        
                        # Final check before returning
                        final_o, final_t, final_ma = self._alpha_stats(img)
                        print(f"    Final headshot stats: opaque={final_o:.2f}, transp={final_t:.2f}, meanA={final_ma:.0f}")
                        if final_o < 0.05:
                            print(f"    WARNING: Final image has no subject (opaque={final_o:.2f}). Using Transparent Background Fallback.")
                            return make_map_background(original)

                        return img

                    except Exception as e:
                        print(f"Warning: failed headshot {path}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Final safety: Return original with map background
                        try:
                            orig = Image.open(path).convert("RGBA")
                            return make_map_background(orig)
                        except:
                            return None

                imgs = [load_process_headshot(p) for p in headshot_paths[:2]]
                imgs = [im for im in imgs if im is not None]

                if len(imgs) == 1:
                    im = imgs[0]
                    # Ensure image has alpha channel for transparency
                    if im.mode != 'RGBA':
                        im = im.convert('RGBA')
                    im = self._resize_cover(im, headshot_area_width, headshot_area_height)
                    # Paste with alpha mask to preserve transparency
                    if im.mode == 'RGBA':
                        slide.paste(im, (headshot_area_x, headshot_area_y), im.split()[3])
                    else:
                        slide.paste(im, (headshot_area_x, headshot_area_y))
                    draw = ImageDraw.Draw(slide)
                elif len(imgs) == 2:
                    gap = 30
                    each_w = (headshot_area_width - gap) // 2
                    each_h = headshot_area_height
                    left, right = imgs
                    # Ensure both images have alpha channel for transparency
                    if left.mode != 'RGBA':
                        left = left.convert('RGBA')
                    if right.mode != 'RGBA':
                        right = right.convert('RGBA')
                    left = self._resize_cover(left, each_w, each_h)
                    right = self._resize_cover(right, each_w, each_h)

                    left_x = headshot_area_x
                    right_x = headshot_area_x + each_w + gap
                    y = headshot_area_y

                    # Paste with alpha mask to preserve transparency
                    if left.mode == 'RGBA':
                        slide.paste(left, (left_x, y), left.split()[3])
                    else:
                        slide.paste(left, (left_x, y))
                    if right.mode == 'RGBA':
                        slide.paste(right, (right_x, y), right.split()[3])
                    else:
                        slide.paste(right, (right_x, y))
                draw = ImageDraw.Draw(slide)
        except Exception as e:
            print(f"Warning: Could not load headshot: {e}")
            import traceback
            traceback.print_exc()
        
        # 8. Replace investment stage in sidebar (transparent, black, thicker text like company name, includes year)
        # Find Slauson&Co position in sidebar (bottom of sidebar)
        slauson_y = height - 200  # Approximate position of "SLAUSON&CO." text (bottom of sidebar)
        
        # Parse investment stage to match the template look (e.g., "SEED Q4, 2024")
        # Input format is typically like "SEED Q2, 2024" or "PRE-SEED Q2, 2024"
        stage_parts = investment_stage.upper().split(',')
        if len(stage_parts) >= 2:
            stage_quarter = stage_parts[0].strip()  # "SEED Q2" or "PRE-SEED Q2"
            year_text = stage_parts[1].strip()  # "2024"
            # Combine into "STAGE Q#, YYYY" format
            stage_text = f"{stage_quarter}, {year_text}"  # "SEED Q2, 2024"
        else:
            stage_text = investment_stage.upper()
        
        # --- Render investment stage (fix "squished" look) ---
        # Keep the old font behavior (no preferred_family), but avoid heavy multi-pass stroke
        # and avoid large downscales after rotation (both make the text look condensed).
        sidebar_w = 200
        # Keep the sidebar stage text readable but not comically large.
        # Width (after rotation) is driven mostly by font height, so side margins + padding
        # are the safest knobs to make it "reasonable" without reintroducing squish/blur.
        top_margin = 35
        bottom_margin = 25
        # Constrain usable width so the font size matches the template (like your screenshot).
        side_margin = 35
        max_w = sidebar_w - 2 * side_margin
        max_h = height - top_margin - bottom_margin

        stage_color = (0, 0, 0)
        # Add back some padding so the text doesn't dominate the sidebar.
        padding = 10

        stage_img = None
        final_w = final_h = 0

        # Choose the largest font size that fits without resizing the rotated bitmap.
        # Cap the max size so it stays visually consistent with the template.
        for fs in range(55, 11, -1):
            # Stage text should use the same font family as the title (Bebas Neue).
            stage_font = self._load_font(fs, bold=False, preferred_family="BebasNeue")

            tmp = Image.new("RGBA", (2000, 2000), (0, 0, 0, 0))
            td = ImageDraw.Draw(tmp)
            bbox = td.textbbox((0, 0), stage_text, font=stage_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            img = Image.new("RGBA", (max(1, int(text_w + padding * 2)), max(1, int(text_h + padding * 2))), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.text(
                (padding - bbox[0], padding - bbox[1]),
                stage_text,
                fill=stage_color,
                font=stage_font,
                stroke_width=1,
                stroke_fill=stage_color,
            )

            rot = img.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
            w, h = rot.size
            if w <= max_w and h <= max_h:
                stage_img = rot
                final_w, final_h = w, h
                break

        if stage_img is None:
            # Last resort: render at a small size; still no post-rotate downscale.
            stage_font = self._load_font(18, bold=False)
            tmp = Image.new("RGBA", (2000, 2000), (0, 0, 0, 0))
            td = ImageDraw.Draw(tmp)
            bbox = td.textbbox((0, 0), stage_text, font=stage_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            img = Image.new("RGBA", (max(1, int(text_w + padding * 2)), max(1, int(text_h + padding * 2))), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.text(
                (padding - bbox[0], padding - bbox[1]),
                stage_text,
                fill=stage_color,
                font=stage_font,
                stroke_width=1,
                stroke_fill=stage_color,
            )
            stage_img = img.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
            final_w, final_h = stage_img.size

        # Compute placement
        # Center the stage text in the sidebar and place it near the top like the template.
        paste_x = max(0, (sidebar_w - final_w) // 2)
        paste_y = 110

        # Clamp so it can NEVER go off-canvas
        paste_x = max(0, min(paste_x, sidebar_w - final_w)) - 10
        paste_y = max(0, min(paste_y, height - final_h)) - 10

        # Clear the existing baked-in sidebar stage text under our overlay.
        # The template already contains stage text; drawing on top can look "squished"/blurry.
        try:
            # Sample the sidebar background (exclude black text) to get the orange fill.
            sidebar_bg_rgb = self._get_dominant_color(
                template,
                region=(10, 300, 180, 300),
                exclude_colors=[(0, 0, 0), (255, 255, 255)],
            )
            x0 = max(0, paste_x - 4)
            y0 = max(0, paste_y - 4)
            x1 = min(sidebar_w, paste_x + final_w + 4)
            y1 = min(height, paste_y + final_h + 4)
            draw.rectangle([(x0, y0), (x1, y1)], fill=sidebar_bg_rgb)
        except Exception:
            pass

        slide.paste(stage_img, (paste_x, paste_y), stage_img)

        # --- Per-slide tracking watermark (visible, for human traceability) ---
        # Note: The PDF output from this generator is image-based, so this watermark is not machine-extractable
        # via PDF text extraction. We use a separate index store for reliable replacement/deletion.
        slide_job_id = (
            company_data.get("slide_job_id")
            or company_data.get("Slide Job ID")
            or company_data.get("job_id")
        )
        if slide_job_id:
            try:
                watermark_draw = ImageDraw.Draw(slide)
                wm_font = self._load_font(14, bold=False)
                wm_text = f"Slide Job ID: {slide_job_id}"
                # Bottom-right placement (very right)
                wm_bbox = watermark_draw.textbbox((0, 0), wm_text, font=wm_font)
                wm_w = wm_bbox[2] - wm_bbox[0]
                wm_h = wm_bbox[3] - wm_bbox[1]
                margin = 10
                wm_x = max(margin, width - wm_w - margin)
                wm_y = max(margin, height - wm_h - margin)

                # Pure solid black
                wm_fill = (0, 0, 0, 255) if slide.mode == "RGBA" else (0, 0, 0)
                watermark_draw.text((wm_x, wm_y), wm_text, fill=wm_fill, font=wm_font)
            except Exception:
                pass
        
        # Convert to RGB for PDF
        slide_rgb = Image.new('RGB', slide.size, (42, 42, 42))
        slide_rgb.paste(slide, mask=slide.split()[3] if slide.mode == 'RGBA' else None)
        
        # Return based on output format
        if output_format.lower() == "pptx":
            return self._create_pptx_from_slide(
                slide, company_data, headshot_path, logo_path, map_path,
                map_area_x, map_area_y, map_width, map_height
            )
        
        # Default: Convert to PDF (flattened, not editable)
        # Convert to RGB for PDF
        slide_rgb = Image.new('RGB', slide.size, (42, 42, 42))
        slide_rgb.paste(slide, mask=slide.split()[3] if slide.mode == 'RGBA' else None)
        
        # Convert to PDF
        # Use temporary file to avoid PIL's fileno() issue with BytesIO
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            try:
                slide_rgb.save(tmp_file.name, format='PNG', optimize=False)
                with open(tmp_file.name, 'rb') as f:
                    img_bytes = f.read()
                pdf_bytes = img2pdf.convert(img_bytes)
                return pdf_bytes
            except Exception as e:
                print(f"Error: {e}")
                return None
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file.name)
                except:
                    pass
    
    def _create_pptx_from_slide(
        self, 
        template_slide: Image.Image,
        company_data: Dict,
        headshot_path: str,
        logo_path: str,
        map_path: Optional[str],
        map_area_x: int,
        map_area_y: int,
        map_width: int,
        map_height: int
    ) -> bytes:
        """
        Create an editable PPTX file with separate elements for Canva import.
        This allows headshot, logo, map, and text to be editable in Canva.
        
        Args:
            template_slide: PIL Image of the template background
            company_data: Company information
            headshot_path: Path to headshot image
            logo_path: Path to logo image
            map_path: Path to map image (optional)
            map_area_x, map_area_y, map_width, map_height: Map position/size
            
        Returns:
            PPTX file bytes
        """
        if not PPTX_AVAILABLE:
            raise ImportError("python-pptx is required for PPTX generation. Install with: pip install python-pptx")
        
        # Slide dimensions: 1920x1080 pixels = 20x11.25 inches at 96 DPI
        # Standard widescreen: 13.333" x 7.5" (16:9)
        prs = Presentation()
        prs.slide_width = Inches(13.333)  # 1920px / 144 DPI
        prs.slide_height = Inches(7.5)   # 1080px / 144 DPI
        
        # Create blank slide
        slide_layout = prs.slide_layouts[6]  # Blank layout
        slide_pptx = prs.slides.add_slide(slide_layout)
        
        # CRITICAL: Don't add full-slide background image - it causes Canva to flatten everything into one image
        # Instead, we'll add ONLY the editable elements (logo, headshot, text, map) on a blank slide
        # The user can add their own background in Canva, or we can add it as a separate editable element later
        # For now, just add a simple colored background using shapes (editable)
        from pptx.enum.shapes import MSO_SHAPE
        
        # 1) Orange sidebar (left side, editable shape)
        sidebar_width_inch = Inches(200 / 96.0)  # 200px converted to inches
        sidebar = slide_pptx.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0),
            Inches(0),
            sidebar_width_inch,
            prs.slide_height
        )
        sidebar.fill.solid()
        sidebar.fill.fore_color.rgb = RGBColor(242, 140, 40)  # Orange #F28C28
        sidebar.line.fill.background()  # No border
        
        # 2) Dark grey main area (right side, editable shape)
        main_area = slide_pptx.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            sidebar_width_inch,
            Inches(0),
            prs.slide_width - sidebar_width_inch,
            prs.slide_height
        )
        main_area.fill.solid()
        main_area.fill.fore_color.rgb = RGBColor(42, 42, 42)  # Dark grey
        main_area.line.fill.background()  # No border
        
        # Get actual positions from template (convert pixels to inches at 96 DPI)
        width, height = template_slide.size
        px_to_inch = 1.0 / 96.0  # 96 DPI standard
        
        # Add "SLAUSON&CO." text in sidebar (bottom, editable text)
        slauson_text = "SLAUSON&CO."
        slauson_y_px = height - 200  # Bottom of sidebar
        slauson_x_px = 10  # Left side of sidebar
        
        slauson_textbox = slide_pptx.shapes.add_textbox(
            Inches(slauson_x_px * px_to_inch),
            Inches(slauson_y_px * px_to_inch),
            Inches(180 * px_to_inch),  # Width for sidebar
            Inches(1.5)
        )
        slauson_tf = slauson_textbox.text_frame
        slauson_tf.word_wrap = False
        slauson_p = slauson_tf.paragraphs[0]
        slauson_run = slauson_p.add_run()
        slauson_run.text = slauson_text
        slauson_run.font.size = Pt(28)
        slauson_run.font.bold = True
        slauson_run.font.color.rgb = RGBColor(0, 0, 0)  # Black
        
        # 2) Logo (top right, editable) - from PIL code: logo_x, logo_y = width - 170, 10
        if logo_path and os.path.exists(logo_path):
            logo_img = Image.open(logo_path).convert('RGBA')
            # Load image fully before operations to avoid lazy loading issues
            logo_img.load()
            # Make circular (same as PIL code)
            logo_size_px = 130
            
            # Create circular mask first
            circle_mask = Image.new('L', (logo_size_px, logo_size_px), 0)
            circle_draw = ImageDraw.Draw(circle_mask)
            circle_draw.ellipse([(0, 0), (logo_size_px, logo_size_px)], fill=255)
            
            # Center crop to square first
            logo_w, logo_h = logo_img.size
            min_dim = min(logo_w, logo_h)
            logo_img = logo_img.crop(((logo_w - min_dim) // 2, (logo_h - min_dim) // 2, 
                                     (logo_w + min_dim) // 2, (logo_h + min_dim) // 2))
            
            # Resize to fill the entire circle (logo_size_px x logo_size_px)
            logo_img = logo_img.resize((logo_size_px, logo_size_px), Image.Resampling.LANCZOS)
            
            # Apply circular mask to logo - this makes it truly circular
            logo_masked = Image.new('RGBA', (logo_size_px, logo_size_px), (0, 0, 0, 0))
            logo_masked.paste(logo_img, (0, 0))  # Paste at origin, no padding
            logo_masked.putalpha(circle_mask)  # Apply circular mask to make it round
            
            logo_bytes = io.BytesIO()
            logo_masked.save(logo_bytes, format='PNG')
            logo_bytes.seek(0)
            
            # Position: from PIL code - logo_x, logo_y = width - 170, 10
            logo_x_inch = (width - 170) * px_to_inch
            logo_y_inch = 10 * px_to_inch
            logo_size_inch = logo_size_px * px_to_inch
            
            slide_pptx.shapes.add_picture(
                logo_bytes,
                Inches(logo_x_inch),
                Inches(logo_y_inch),
                width=Inches(logo_size_inch)
            )
        
        # 3) Company name (editable text) - from PIL code: name_x, name_y = founders_text_x - 50, 120
        company_name = company_data.get("name", "").upper()
        if company_name:
            # Position from PIL: name_x = founders_text_x - 50, name_y = 120
            # founders_text_x = 320 from PIL code
            name_x_px = 320 - 50  # 270
            name_y_px = 120
            
            # Calculate font size (same logic as PIL)
            base_font_size = 200
            name_font_size = base_font_size
            # Check for overlap with map
            max_allowed_width = map_area_x - name_x_px - 50
            # Estimate text width (rough calculation)
            estimated_width = len(company_name) * (name_font_size * 0.6)  # Rough estimate
            if estimated_width > max_allowed_width:
                name_font_size = int((max_allowed_width / estimated_width) * base_font_size)
                # Prefer a larger minimum, but only if it still fits by estimate.
                desired_min_size = 120
                if name_font_size < desired_min_size:
                    desired_estimated_width = len(company_name) * (desired_min_size * 0.6)
                    if desired_estimated_width <= max_allowed_width:
                        name_font_size = desired_min_size
                name_font_size = max(90, name_font_size)
            
            textbox = slide_pptx.shapes.add_textbox(
                Inches(name_x_px * px_to_inch),
                Inches(name_y_px * px_to_inch),
                Inches((map_area_x - name_x_px - 50) * px_to_inch),
                Inches(2.0)  # Height for large text
            )
            tf = textbox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = company_name
            run.font.size = Pt(name_font_size)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 140, 0)  # Orange color
        
        # 4) Investment stage (editable text) - positioned in sidebar
        investment_stage = company_data.get("investment_stage", "")
        if not investment_stage:
            round_val = company_data.get("investment_round", "PRE-SEED")
            quarter_val = company_data.get("quarter", "Q2")
            year_val = company_data.get("year", "2024")
            investment_stage = f"{round_val} {quarter_val} {year_val}"
        
        if investment_stage:
            paste_x_px = 15   # slightly right
            paste_y_px = 70   # lower
            
            # Make the textbox TALL/WIDE BEFORE rotation so it has room after rotation.
            # Use most of the slide height.
            box_w_px = 180
            box_h_px = 950   # <-- big, prevents "tiny" rendering
            
            textbox = slide_pptx.shapes.add_textbox(
                Inches(paste_x_px * px_to_inch),
                Inches(paste_y_px * px_to_inch),
                Inches(box_w_px * px_to_inch),
                Inches(box_h_px * px_to_inch),
            )
            textbox.rotation = 270  # bottom->top like the sidebar
            
            tf = textbox.text_frame
            tf.word_wrap = False
            
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = investment_stage
            
            # BIGGER FONT (36-46pt range)
            run.font.size = Pt(40)
            run.font.bold = False  # Less bold for easier reading
            run.font.color.rgb = RGBColor(0, 0, 0)  # Black
        
        # 5) Headshot (below map, editable)
        if headshot_path and os.path.exists(headshot_path):
            headshot_bytes = io.BytesIO()
            headshot_img = Image.open(headshot_path).convert('RGBA')
            headshot_img.load()  # Load fully before save to avoid memory issues
            # Ensure transparent background for PPTX as well (grayscale-aware)
            try:
                headshot_img = self._remove_background_gray(headshot_img, tol=8, feather=1)
            except Exception as e:
                print(f"   Warning: PPTX fallback background removal failed: {e}")
            # ALWAYS convert to grayscale while preserving alpha (headshot should be grayscale)
            headshot_img = self._to_grayscale_preserve_alpha(headshot_img)
            # Process headshot (background removal already done in PIL code)
            headshot_img.save(headshot_bytes, format='PNG', optimize=False)
            headshot_bytes.seek(0)
            
            # Position from PIL: headshot_area_width = 550 * 2.2 = 1210, headshot_area_height = 500 * 2.2 = 1100
            # headshot_area_x = map_area_x + (map_width - headshot_area_width) // 2 - 50
            # headshot_area_y = map_area_y + map_height - 50
            # Headshot target box (smaller to not cover map)
            headshot_area_width_px = 500
            headshot_area_height_px = 500
            headshot_area_x_px = map_area_x + (map_width - headshot_area_width_px) // 2 - 50  # Centered under map, slightly left
            headshot_area_y_px = map_area_y + map_height + 55  # Position below map with larger gap (lowered)
            
            slide_pptx.shapes.add_picture(
                headshot_bytes,
                Inches(headshot_area_x_px * px_to_inch),
                Inches(headshot_area_y_px * px_to_inch),
                width=Inches(headshot_area_width_px * px_to_inch),
                height=Inches(headshot_area_height_px * px_to_inch)
            )
        
        # 6) Founders text (editable) - from PIL code: founders_text_x = 320, founders_text_y = 415
        founders_items = self._parse_name_list(company_data.get("founders", ""))[:3]
        founders_text = "\n".join(founders_items)
        if founders_text:
            
            # Position from PIL: founders_text_x = 320, founders_text_y = 415
            founders_text_x_px = 320
            founders_text_y_px = 415
            
            textbox = slide_pptx.shapes.add_textbox(
                Inches(founders_text_x_px * px_to_inch),
                Inches(founders_text_y_px * px_to_inch),
                Inches(3.0),
                Inches(2.0)
            )
            tf = textbox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = founders_text
            run.font.size = Pt(24)
            run.font.color.rgb = RGBColor(255, 255, 255)  # White
        
        # 7) Co-investors text (editable) - from PIL code: investors_text_x = 650, investors_text_y = 415
        co_investors_items = self._parse_name_list(company_data.get("co_investors", ""))[:5]
        co_investors_text = "\n".join(co_investors_items)
        if co_investors_text:
            
            # Position from PIL: investors_text_x = 650, investors_text_y = 415
            investors_text_x_px = 650
            investors_text_y_px = 415
            
            textbox = slide_pptx.shapes.add_textbox(
                Inches(investors_text_x_px * px_to_inch),
                Inches(investors_text_y_px * px_to_inch),
                Inches(3.0),
                Inches(2.0)
            )
            tf = textbox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = co_investors_text
            run.font.size = Pt(24)
            run.font.color.rgb = RGBColor(255, 255, 255)  # White
        
        # 8) Background text (editable) - from PIL code: bg_text_x = 320, bg_text_y = 650
        background_text = company_data.get("background", company_data.get("description", ""))
        if background_text:
            # Position from PIL: bg_text_x = 320, bg_text_y = 650, bg_text_width = 700
            bg_text_x_px = 320
            bg_text_y_px = 650
            bg_text_width_px = 700
            
            textbox = slide_pptx.shapes.add_textbox(
                Inches(bg_text_x_px * px_to_inch),
                Inches(bg_text_y_px * px_to_inch),
                Inches(bg_text_width_px * px_to_inch),
                Inches(2.5)
            )
            tf = textbox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = background_text
            run.font.size = Pt(32)
            run.font.color.rgb = RGBColor(255, 255, 255)  # White
        
        # 9) Map (if provided, editable) - positioned at detected map area
        if map_path and os.path.exists(map_path):
            map_bytes = io.BytesIO()
            map_img = Image.open(map_path).convert('RGBA')
            map_img.load()  # Load fully before save to avoid memory issues
            map_img.save(map_bytes, format='PNG', optimize=False)
            map_bytes.seek(0)
            
            # Position: top right area (from detected map area)
            map_x = map_area_x / 96.0  # Convert pixels to inches
            map_y = map_area_y / 96.0
            map_w = map_width / 96.0
            map_h = map_height / 96.0
            
            slide_pptx.shapes.add_picture(
                map_bytes,
                Inches(map_x),
                Inches(map_y),
                width=Inches(map_w),
                height=Inches(map_h)
            )
        
        # Save to bytes
        pptx_bytes = io.BytesIO()
        prs.save(pptx_bytes)
        pptx_bytes.seek(0)
        return pptx_bytes.getvalue()
