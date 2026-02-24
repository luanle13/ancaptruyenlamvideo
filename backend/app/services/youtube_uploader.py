# AnCapTruyenLamVideo - YouTube Upload Service

import asyncio
import logging
import os
import json
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    """Service for uploading videos to YouTube."""

    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.youtube = None
        self._pending_flow: Optional[Flow] = None
        self._callback_url: Optional[str] = None

    def _get_credentials_path(self) -> Path:
        """Get path to credentials file."""
        return Path(settings.youtube_credentials_file)

    def _get_client_secrets_path(self) -> Path:
        """Get path to client secrets file."""
        return Path(settings.youtube_client_secrets_file)

    def is_authenticated(self) -> bool:
        """Check if YouTube credentials are valid."""
        creds_path = self._get_credentials_path()
        if not creds_path.exists():
            return False

        try:
            self.credentials = Credentials.from_authorized_user_file(str(creds_path), SCOPES)
            if self.credentials and self.credentials.valid:
                return True
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                self._save_credentials()
                return True
        except Exception as e:
            logger.error(f"Error checking credentials: {e}")

        return False

    def _save_credentials(self):
        """Save credentials to file."""
        if self.credentials:
            creds_path = self._get_credentials_path()
            with open(creds_path, "w") as f:
                f.write(self.credentials.to_json())

    def authenticate_interactive(self) -> bool:
        """
        Run interactive OAuth flow to authenticate.
        This needs to be run once to get credentials.
        Returns True if successful.
        """
        client_secrets_path = self._get_client_secrets_path()
        if not client_secrets_path.exists():
            logger.error(f"Client secrets file not found: {client_secrets_path}")
            logger.error("Please download client_secrets.json from Google Cloud Console")
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path),
                SCOPES
            )
            self.credentials = flow.run_local_server(port=8080)
            self._save_credentials()
            logger.info("YouTube authentication successful")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def get_auth_url(self, callback_url: str) -> Optional[str]:
        """
        Generate OAuth URL for web-based authentication.
        Returns the URL to redirect the user to.
        """
        client_secrets_path = self._get_client_secrets_path()
        if not client_secrets_path.exists():
            logger.error(f"Client secrets file not found: {client_secrets_path}")
            return None

        try:
            self._callback_url = callback_url
            self._pending_flow = Flow.from_client_secrets_file(
                str(client_secrets_path),
                scopes=SCOPES,
                redirect_uri=callback_url
            )

            auth_url, _ = self._pending_flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent"
            )

            logger.info(f"Generated YouTube auth URL: {auth_url[:50]}...")
            return auth_url

        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            return None

    def complete_auth(self, code: str) -> bool:
        """
        Complete OAuth flow with authorization code.
        Called after user grants permission.
        """
        if not self._pending_flow:
            # Try to recreate flow if it was lost (e.g., server restart)
            client_secrets_path = self._get_client_secrets_path()
            if not client_secrets_path.exists():
                logger.error("No pending flow and no client secrets")
                return False

            # We need the callback URL - try to get it from config or use default
            callback_url = self._callback_url or "http://localhost:8000/api/youtube/auth/callback"
            self._pending_flow = Flow.from_client_secrets_file(
                str(client_secrets_path),
                scopes=SCOPES,
                redirect_uri=callback_url
            )

        try:
            self._pending_flow.fetch_token(code=code)
            self.credentials = self._pending_flow.credentials
            self._save_credentials()
            self._pending_flow = None
            logger.info("YouTube web authentication successful")
            return True

        except Exception as e:
            logger.error(f"Error completing auth: {e}")
            return False

    def revoke_credentials(self):
        """Revoke and delete stored credentials."""
        creds_path = self._get_credentials_path()
        if creds_path.exists():
            creds_path.unlink()
            logger.info("YouTube credentials revoked")
        self.credentials = None
        self.youtube = None

    def _get_youtube_service(self):
        """Get authenticated YouTube service."""
        if not self.is_authenticated():
            raise Exception("Not authenticated. Run authenticate_interactive() first.")

        if not self.youtube:
            self.youtube = build("youtube", "v3", credentials=self.credentials)

        return self.youtube

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list[str] = None,
        category_id: str = None,
        privacy_status: str = None
    ) -> Optional[str]:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (default: 22 - People & Blogs)
            privacy_status: private, unlisted, or public

        Returns:
            YouTube video ID if successful, None otherwise
        """
        if not settings.youtube_enabled:
            logger.info("YouTube upload is disabled")
            return None

        if not Path(video_path).exists():
            logger.error(f"Video file not found: {video_path}")
            return None

        if not self.is_authenticated():
            logger.error("YouTube not authenticated. Please run authentication first.")
            return None

        # Default values
        category_id = category_id or settings.youtube_default_category
        privacy_status = privacy_status or settings.youtube_default_privacy
        tags = tags or []

        # Truncate title if too long (YouTube limit is 100 chars)
        if len(title) > 100:
            title = title[:97] + "..."

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            }
        }

        # Run upload in thread pool to avoid blocking
        try:
            video_id = await asyncio.get_event_loop().run_in_executor(
                None,
                self._upload_video_sync,
                video_path,
                body
            )
            return video_id
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    def _upload_video_sync(self, video_path: str, body: dict) -> Optional[str]:
        """Synchronous video upload (run in thread pool)."""
        try:
            youtube = self._get_youtube_service()

            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024  # 1MB chunks
            )

            request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"YouTube upload progress: {progress}%")

            video_id = response.get("id")
            logger.info(f"YouTube upload complete: https://youtube.com/watch?v={video_id}")
            return video_id

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None


# Singleton instance
youtube_uploader = YouTubeUploader()


# CLI helper for initial authentication
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        print("Starting YouTube authentication...")
        if youtube_uploader.authenticate_interactive():
            print("Authentication successful! Credentials saved.")
        else:
            print("Authentication failed.")
    else:
        print("Usage: python -m app.services.youtube_uploader auth")
