#!/usr/bin/env python3
"""
Generate a single HTML→PDF slide with the title "ASTRANIS" to validate:
- Title font loads from assets/fonts (BebasNeue)
- Title renders large for short names
- If it would overlap the map bbox, it shrinks (existing behavior)

Output: temp_test/astranis_html_title_test.pdf
"""

import os
from pathlib import Path


def _make_transparent_headshot(path: Path, size: int = 600) -> None:
    # Create an RGBA image with transparent background so the generator can skip heavy bg removal.
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Simple silhouette circle
    draw.ellipse((40, 40, size - 40, size - 40), fill=(160, 160, 160, 255))
    img.save(path)


def _make_simple_logo(path: Path, size: int = 300) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((10, 10, size - 10, size - 10), radius=40, fill=(30, 120, 240, 255))
    img.save(path)


def _make_simple_map(path: Path, w: int = 1200, h: int = 700) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (w, h), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, w - 40, h - 40), outline=(255, 140, 0), width=6)
    img.save(path)


def main() -> int:
    # Enable debug prints for title sizing/position if you want them
    os.environ.setdefault("DEBUG_LAYOUT", "1")

    out_dir = Path("temp_test")
    out_dir.mkdir(exist_ok=True)

    headshot_path = out_dir / "astranis_headshot_rgba.png"
    logo_path = out_dir / "astranis_logo_rgba.png"
    map_path = out_dir / "astranis_map.png"
    out_pdf = out_dir / "astranis_html_title_test.pdf"

    _make_transparent_headshot(headshot_path)
    _make_simple_logo(logo_path)
    _make_simple_map(map_path)

    company_data = {
        "name": "ASTRANIS",
        "website": "https://astranis.com",
        "description": "Satellite internet provider building next-gen broadband satellites.",
        "address": "San Francisco, CA",
        "investment_round": "PRE-SEED",
        "quarter": "Q2",
        "year": "2024",
        "co_investors": "",
        "num_employees": 0,
        "first_time_founder": False,
        "investment_memo_link": "",
    }

    from html_slide_generator import HTMLSlideGenerator

    gen = HTMLSlideGenerator()
    pdf_bytes = gen.create_slide(
        company_data=company_data,
        headshot_path=str(headshot_path),
        logo_path=str(logo_path),
        map_path=str(map_path),
    )

    out_pdf.write_bytes(pdf_bytes)
    print(f"✓ Wrote {out_pdf} ({len(pdf_bytes)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

