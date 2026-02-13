"""
Sync a Google Drive PDF (master slides) into Canva.

This is useful for backfilling Canva with ALL slides at once:
1) Download the master PDF from Google Drive (by file ID or by name in folder)
2) Import it into Canva as a multi-page design (Design Import API)
3) Move the created design into a destination Canva folder (optional)

Requirements:
- Google Drive OAuth configured (token.json or GOOGLE_DRIVE_CREDENTIALS_JSON)
- Canva OAuth configured (CANVA_CLIENT_ID/SECRET + tokens)
- If moving to a Canva folder, OAuth must include folder scopes and
  CANVA_DESTINATION_FOLDER_ID must be set.
"""

import os

from google_drive_integration import GoogleDriveIntegration
from canva_integration import CanvaIntegration


def _resolve_drive_folder_id(drive: GoogleDriveIntegration) -> str:
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if folder_id:
        return folder_id
    folder_name = os.getenv("GOOGLE_DRIVE_FOLDER_NAME") or "Slauson Deck (Portco Slides)"
    found = drive.find_folder_id_by_name(folder_name)
    return found or ""


def _resolve_drive_pdf_file_id(drive: GoogleDriveIntegration, folder_id: str) -> str:
    file_id = os.getenv("GOOGLE_DRIVE_STATIC_FILE_ID")
    if file_id:
        return file_id
    filename = os.getenv("GOOGLE_DRIVE_STATIC_FILE_NAME") or "Portfolio Slides.pdf"
    found = drive.find_file_id_by_name(filename, parent_folder_id=folder_id, fallback_global=False)
    return found or ""


def main() -> None:
    print("== Sync Drive PDF → Canva ==")
    print()

    drive = GoogleDriveIntegration()
    folder_id = _resolve_drive_folder_id(drive)
    file_id = _resolve_drive_pdf_file_id(drive, folder_id)

    if not file_id:
        raise SystemExit(
            "Could not find the Drive PDF. Set GOOGLE_DRIVE_STATIC_FILE_ID or "
            "ensure GOOGLE_DRIVE_STATIC_FILE_NAME exists in your Drive folder."
        )

    print(f"Downloading Drive PDF: {file_id}")
    pdf_bytes = drive.download_file(file_id)
    print(f"✓ Downloaded {len(pdf_bytes)} bytes")

    filename = os.getenv("CANVA_IMPORT_FILENAME") or "Portfolio Slides.pdf"

    canva = CanvaIntegration()
    print("Importing PDF into Canva (this creates a new design)...")
    job_id = canva.upload_pdf_asset(pdf_bytes, filename=filename)
    status = canva.wait_for_import_completion(job_id, max_wait_seconds=180, poll_interval=2)

    if status.get("status") != "success":
        raise SystemExit(f"Import did not succeed. Status: {status}")

    design_id = status.get("design_id")
    design_url = status.get("design_url") or (f"https://www.canva.com/design/{design_id}/edit" if design_id else None)

    print()
    print("✓ Import complete")
    print(f"  design_id: {design_id}")
    print(f"  edit_url:  {design_url}")

    if os.getenv("CANVA_DESTINATION_FOLDER_ID"):
        print(f"  moved_to_folder: {os.getenv('CANVA_DESTINATION_FOLDER_ID')}")
    else:
        print("  moved_to_folder: (not set) — set CANVA_DESTINATION_FOLDER_ID to auto-move")


if __name__ == "__main__":
    main()

