"""
Persistent storage for Canva OAuth tokens.

Goal: once authorized, token refresh should "just work" without anyone manually running scripts
or updating environment variables.

Storage priority:
1) Google Drive file (durable across deployments/restarts)
2) Local file (canva_tokens.json) for local development
3) Environment variables as a fallback read source only
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CanvaTokenStoreConfig:
    # Google Drive-backed token file (recommended for production)
    drive_file_id: Optional[str]
    drive_file_name: str
    drive_parent_folder_id: Optional[str]

    # Local fallback
    local_path: str


class CanvaTokenStore:
    JSON_MIME_TYPE = "application/json"

    def __init__(self, cfg: CanvaTokenStoreConfig):
        self.cfg = cfg

    @staticmethod
    def from_env() -> "CanvaTokenStore":
        # If you set CANVA_TOKEN_STORE_DRIVE_FILE_ID, we use that exact file.
        # Otherwise, we can search/create by name in the Drive folder.
        drive_file_id = os.getenv("CANVA_TOKEN_STORE_DRIVE_FILE_ID") or None
        drive_file_name = os.getenv("CANVA_TOKEN_STORE_DRIVE_FILE_NAME") or "canva_tokens.json"

        # Prefer explicit token-folder override, else fall back to existing Drive folder config.
        drive_parent_folder_id = (
            os.getenv("CANVA_TOKEN_STORE_DRIVE_FOLDER_ID")
            or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
            or None
        )

        local_path = os.getenv("CANVA_TOKEN_FILE") or "canva_tokens.json"
        return CanvaTokenStore(
            CanvaTokenStoreConfig(
                drive_file_id=drive_file_id,
                drive_file_name=drive_file_name,
                drive_parent_folder_id=drive_parent_folder_id,
                local_path=local_path,
            )
        )

    def _drive_available(self) -> bool:
        # Import lazily so local environments without google deps can still run the rest of the app.
        try:
            from google_drive_integration import GoogleDriveIntegration  # noqa: F401

            return True
        except Exception:
            return False

    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load tokens from the best available store.
        """
        # 1) Drive
        if self._drive_available():
            try:
                from google_drive_integration import GoogleDriveIntegration

                drive = GoogleDriveIntegration()

                file_id = self.cfg.drive_file_id
                if not file_id and self.cfg.drive_file_name:
                    file_id = drive.find_file_id_by_name(
                        self.cfg.drive_file_name,
                        parent_folder_id=self.cfg.drive_parent_folder_id,
                        mime_type=self.JSON_MIME_TYPE,
                    )

                if file_id:
                    raw = drive.download_file(file_id)
                    tokens = json.loads(raw.decode("utf-8"))
                    # Cache file id for subsequent saves in this process
                    self.cfg.drive_file_id = file_id
                    if tokens.get("access_token") or tokens.get("refresh_token"):
                        print("✓ Loaded Canva OAuth tokens from Google Drive token store")
                        return tokens
            except Exception as e:
                print(f"Warning: could not load Canva tokens from Google Drive store: {e}")

        # 2) Local file
        try:
            if self.cfg.local_path and os.path.exists(self.cfg.local_path):
                with open(self.cfg.local_path, "r") as f:
                    tokens = json.load(f)
                if tokens.get("access_token") or tokens.get("refresh_token"):
                    print("✓ Loaded Canva OAuth tokens from local token file")
                    return tokens
        except Exception as e:
            print(f"Warning: could not load Canva tokens from local file: {e}")

        # 3) Env fallback (read-only)
        env_refresh_token = os.getenv("CANVA_REFRESH_TOKEN")
        env_access_token = os.getenv("CANVA_ACCESS_TOKEN")
        env_refreshed_at = os.getenv("CANVA_TOKEN_REFRESHED_AT")
        if env_refresh_token or env_access_token:
            tokens: Dict[str, Any] = {}
            if env_access_token:
                tokens["access_token"] = env_access_token
            if env_refresh_token:
                tokens["refresh_token"] = env_refresh_token
            if env_refreshed_at:
                try:
                    tokens["token_refreshed_at"] = float(env_refreshed_at)
                except Exception:
                    pass
            print("✓ Loaded Canva OAuth tokens from environment variables (fallback)")
            return tokens

        return None

    def save(self, tokens: Dict[str, Any]) -> None:
        """
        Persist tokens to all writable stores (Drive + local file).
        """
        data = json.dumps(tokens, indent=2).encode("utf-8")

        # 1) Drive store
        if self._drive_available():
            try:
                from google_drive_integration import GoogleDriveIntegration

                drive = GoogleDriveIntegration()

                file_id = self.cfg.drive_file_id
                if not file_id and self.cfg.drive_file_name:
                    file_id = drive.find_file_id_by_name(
                        self.cfg.drive_file_name,
                        parent_folder_id=self.cfg.drive_parent_folder_id,
                        mime_type=self.JSON_MIME_TYPE,
                    )

                if file_id:
                    drive.overwrite_file_bytes(file_id, data, mime_type=self.JSON_MIME_TYPE)
                    self.cfg.drive_file_id = file_id
                else:
                    created_id = drive.upload_bytes(
                        data,
                        filename=self.cfg.drive_file_name,
                        mime_type=self.JSON_MIME_TYPE,
                        folder_id=self.cfg.drive_parent_folder_id,
                        make_public_read=False,
                    )
                    self.cfg.drive_file_id = created_id

                print("✓ Saved Canva OAuth tokens to Google Drive token store")
            except Exception as e:
                print(f"Warning: could not save Canva tokens to Google Drive store: {e}")

        # 2) Local file store (best effort)
        try:
            if self.cfg.local_path:
                with open(self.cfg.local_path, "w") as f:
                    f.write(data.decode("utf-8"))
                print("✓ Saved Canva OAuth tokens to local token file")
        except Exception:
            # This is expected on some hosts with read-only or ephemeral FS
            pass

