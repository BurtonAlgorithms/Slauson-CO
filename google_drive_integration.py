"""
Google Drive API integration for uploading PDFs and generating shareable links.
"""
import io
from typing import Optional
from config import Config
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import os
import json


class GoogleDriveIntegration:
    """Handle Google Drive API operations."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        """Initialize Google Drive client."""
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None
        
        # Priority 1: Check if we have token.json (for OAuth flow) - preferred for personal account
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
                # If expired, try to refresh
                if creds and creds.expired and creds.refresh_token:
                    try:
                        print("   Refreshing Google Drive OAuth token...")
                        creds.refresh(Request())
                        # Save refreshed token
                        with open('token.json', 'w') as token:
                            token.write(creds.to_json())
                        print("   ✓ Google Drive token refreshed")
                    except Exception as e:
                        print(f"   Warning: Could not refresh token: {e}")
                        print(f"   Token may be revoked. Please re-run: python setup_google_oauth.py")
                        # Don't use expired token, continue to next method
                        creds = None
                
                if creds and creds.valid:
                    self.credentials = creds
                    self.service = build('drive', 'v3', credentials=creds)
                    print("   ✓ Using Google Drive OAuth (token.json)")
                    return
                elif creds and not creds.valid:
                    print("   Warning: Google Drive token.json exists but is invalid")
            except Exception as e:
                print(f"   Warning: Error loading token.json: {e}")
        
        # Priority 2: Try OAuth credentials from environment variable
        if Config.GOOGLE_DRIVE_CREDENTIALS_JSON:
            try:
                creds_info = json.loads(Config.GOOGLE_DRIVE_CREDENTIALS_JSON)
                if creds_info.get('type') != 'service_account':
                    # OAuth credentials
                    creds = Credentials.from_authorized_user_info(creds_info, self.SCOPES)
                    # Refresh if expired
                    if creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                        except Exception as e:
                            print(f"   Warning: Could not refresh env token: {e}")
                            creds = None
                    
                    if creds and creds.valid:
                        self.credentials = creds
                        self.service = build('drive', 'v3', credentials=creds)
                        print("   ✓ Using Google Drive OAuth (environment variable)")
                        return
            except json.JSONDecodeError as e:
                print(f"   Warning: Invalid GOOGLE_DRIVE_CREDENTIALS_JSON: {e}")
            except Exception as e:
                print(f"   Warning: Error using GOOGLE_DRIVE_CREDENTIALS_JSON: {e}")
        
        # DO NOT fallback to service account - it doesn't have storage quota
        # Instead, raise error with clear instructions
        raise ValueError(
            "Google Drive OAuth credentials not configured or expired. "
            "Service accounts don't have storage quota. "
            "For personal Google Drive (hmikaeltewolde@gmail.com), you need to set up OAuth. "
            "Options:\n"
            "1. Run: python setup_google_oauth.py (if you have credentials.json)\n"
            "2. Set GOOGLE_DRIVE_CREDENTIALS_JSON environment variable with OAuth token JSON\n"
            "3. Ensure token.json exists and is valid"
        )
    
    def upload_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        folder_id: Optional[str] = None
    ) -> str:
        """
        Upload PDF to Google Drive and return shareable link.
        
        Args:
            pdf_bytes: PDF file bytes
            filename: Name for the file
            folder_id: Optional Google Drive folder ID to upload to
            
        Returns:
            Shareable link to the uploaded file
        """
        if not self.service:
            raise ValueError("Google Drive service not initialized")
        
        try:
            # Create file metadata
            file_metadata = {
                'name': filename,
            }
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            
            # Make file shareable (anyone with link can view)
            self.service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            # Get shareable link
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink, webContentLink'
            ).execute()
            
            # Prefer webViewLink (opens in Drive) over webContentLink (direct download)
            shareable_link = file.get('webViewLink') or file.get('webContentLink')
            
            if not shareable_link:
                # Fallback: construct link manually
                shareable_link = f"https://drive.google.com/file/d/{file_id}/view"
            
            return shareable_link
            
        except HttpError as error:
            raise Exception(f"Google Drive upload error: {error}")

    def download_file(self, file_id: str) -> bytes:
        """
        Download a file from Google Drive by file ID and return bytes.
        """
        if not self.service:
            raise ValueError("Google Drive service not initialized")
        try:
            request = self.service.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            buf.seek(0)
            return buf.read()
        except HttpError as error:
            raise Exception(f"Google Drive download error: {error}")

    def overwrite_pdf(self, file_id: str, pdf_bytes: bytes) -> str:
        """
        Overwrite an existing PDF file by file ID. Returns the webViewLink.
        """
        if not self.service:
            raise ValueError("Google Drive service not initialized")
        try:
            media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf', resumable=True)
            self.service.files().update(fileId=file_id, media_body=media, fields='id, webViewLink, webContentLink').execute()

            # Re-fetch links
            file = self.service.files().get(fileId=file_id, fields='webViewLink, webContentLink').execute()
            link = file.get('webViewLink') or file.get('webContentLink') or f"https://drive.google.com/file/d/{file_id}/view"
            return link
        except HttpError as error:
            raise Exception(f"Google Drive overwrite error: {error}")

    def find_file_id_by_name(self, filename: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Find the first file ID matching a given name (optionally within a folder).
        """
        if not self.service:
            raise ValueError("Google Drive service not initialized")
        q_parts = [f"name = '{filename}'", "mimeType = 'application/pdf'"]
        if parent_folder_id:
            q_parts.append(f"'{parent_folder_id}' in parents")
        query = " and ".join(q_parts)
        try:
            resp = self.service.files().list(
                q=query,
                spaces='drive',
                fields="files(id, name)",
                pageSize=1
            ).execute()
            files = resp.get("files", [])
            if files:
                return files[0]["id"]
            return None
        except HttpError as error:
            print(f"Warning: Google Drive search error: {error}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive by file ID.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not self.service:
            raise ValueError("Google Drive service not initialized")
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            print(f"✓ Deleted Google Drive file: {file_id}")
            return True
        except HttpError as e:
            print(f"⚠️  Error deleting Google Drive file {file_id}: {e}")
            return False
    
    def extract_file_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract file ID from Google Drive URL.
        
        Args:
            url: Google Drive URL (webViewLink or webContentLink)
            
        Returns:
            File ID or None if not found
        """
        import re
        # Try different URL formats
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',  # Standard format: /file/d/FILE_ID/view
            r'id=([a-zA-Z0-9_-]+)',  # Query param format: ?id=FILE_ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder
            parent_folder_id: Optional parent folder ID
            
        Returns:
            Folder ID
        """
        if not self.service:
            raise ValueError("Google Drive service not initialized")
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
        except HttpError as error:
            raise Exception(f"Google Drive folder creation error: {error}")

