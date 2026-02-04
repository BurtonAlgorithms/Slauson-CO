"""
Per-slide tracking store for the Google Drive master PDF.

We keep a durable mapping:
  notion_page_id -> { slide_job_id, page_index, updated_at }

This avoids relying on PDF text extraction (which doesn't work for image-based PDFs).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SlideJobIndexStoreConfig:
    drive_file_id: Optional[str]
    drive_file_name: str
    drive_folder_id: Optional[str]


class SlideJobIndexStore:
    MIME_TYPE = "application/json"

    def __init__(self, cfg: SlideJobIndexStoreConfig):
        self.cfg = cfg

    @staticmethod
    def from_env(drive_folder_id: Optional[str]) -> "SlideJobIndexStore":
        return SlideJobIndexStore(
            SlideJobIndexStoreConfig(
                drive_file_id=os.getenv("SLIDE_JOB_INDEX_DRIVE_FILE_ID") or None,
                drive_file_name=os.getenv("SLIDE_JOB_INDEX_DRIVE_FILE_NAME") or "slide_job_index.json",
                drive_folder_id=os.getenv("SLIDE_JOB_INDEX_DRIVE_FOLDER_ID") or drive_folder_id,
            )
        )

    def load(self, drive) -> Dict[str, Any]:
        """
        Load the index JSON from Drive (or return an empty structure).
        """
        # Resolve file id
        file_id = self.cfg.drive_file_id
        if not file_id:
            file_id = drive.find_file_id_by_name(
                self.cfg.drive_file_name,
                parent_folder_id=self.cfg.drive_folder_id,
                mime_type=self.MIME_TYPE,
            )
        if not file_id:
            return {"version": 1, "entries": {}}

        raw = drive.download_file(file_id)
        self.cfg.drive_file_id = file_id
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {"version": 1, "entries": {}}

    def save(self, drive, data: Dict[str, Any]) -> None:
        """
        Save the index JSON back to Drive.
        """
        data = dict(data or {})
        data.setdefault("version", 1)
        data["updated_at"] = time.time()

        payload = json.dumps(data, indent=2).encode("utf-8")

        file_id = self.cfg.drive_file_id
        if not file_id:
            file_id = drive.find_file_id_by_name(
                self.cfg.drive_file_name,
                parent_folder_id=self.cfg.drive_folder_id,
                mime_type=self.MIME_TYPE,
            )

        if file_id:
            drive.overwrite_file_bytes(file_id, payload, mime_type=self.MIME_TYPE)
            self.cfg.drive_file_id = file_id
        else:
            created_id = drive.upload_bytes(
                payload,
                filename=self.cfg.drive_file_name,
                mime_type=self.MIME_TYPE,
                folder_id=self.cfg.drive_folder_id,
                make_public_read=False,
            )
            self.cfg.drive_file_id = created_id

