from pathlib import Path

import base64
import binascii
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from api.settings import api_settings


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def upload_file(file_path: Path, filename: str, folder_id: str, mimetype: str = "text/csv") -> dict:
    """
    Generic file upload to Google Drive.
    
    Args:
        file_path: Path to the file to upload
        filename: Name for the file in Drive
        folder_id: Google Drive folder ID
        mimetype: MIME type of the file
    
    Returns:
        Dict with file id and webViewLink
    """
    credentials = None
    if api_settings.google_service_account_json_base64:
        try:
            decoded = base64.b64decode(
                api_settings.google_service_account_json_base64
            ).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 invalido (base64)."
            ) from exc
        try:
            info = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 invalido (JSON)."
            ) from exc
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    else:
        raise RuntimeError(
            "Google Drive credentials missing. "
            "Set GOOGLE_SERVICE_ACCOUNT_JSON_BASE64."
        )
    service = build("drive", "v3", credentials=credentials)

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    media = MediaFileUpload(str(file_path), mimetype=mimetype)

    return (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )


def upload_pdf(file_path: Path, filename: str) -> dict:
    """Upload PDF to default Google Drive folder"""
    return upload_file(
        file_path=file_path,
        filename=filename,
        folder_id=api_settings.google_drive_folder_id,
        mimetype="application/pdf"
    )
