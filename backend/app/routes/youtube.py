# AnCapTruyenLamVideo - YouTube OAuth Routes

import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from ..config import get_settings
from ..services.youtube_uploader import youtube_uploader

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.get("/status")
async def get_youtube_status():
    """Check YouTube authentication status."""
    is_authenticated = youtube_uploader.is_authenticated()
    return {
        "enabled": settings.youtube_enabled,
        "authenticated": is_authenticated,
        "privacy": settings.youtube_default_privacy
    }


@router.get("/auth/start")
async def start_youtube_auth(request: Request):
    """Start YouTube OAuth flow - returns auth URL."""
    try:
        # Get the callback URL based on request
        callback_url = str(request.url_for("youtube_oauth_callback"))

        auth_url = youtube_uploader.get_auth_url(callback_url)
        if not auth_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate auth URL. Check client_secrets.json exists."
            )

        return {"auth_url": auth_url}

    except Exception as e:
        logger.error(f"Error starting YouTube auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/callback", name="youtube_oauth_callback")
async def youtube_oauth_callback(code: str = None, error: str = None):
    """Handle YouTube OAuth callback."""
    if error:
        return HTMLResponse(content=f"""
            <html>
            <head><title>YouTube Auth Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">Authentication Failed</h1>
                <p>Error: {error}</p>
                <p>You can close this window.</p>
                <script>
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
        """)

    if not code:
        return HTMLResponse(content="""
            <html>
            <head><title>YouTube Auth Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">Authentication Failed</h1>
                <p>No authorization code received.</p>
                <p>You can close this window.</p>
            </body>
            </html>
        """)

    try:
        success = youtube_uploader.complete_auth(code)

        if success:
            return HTMLResponse(content="""
                <html>
                <head><title>YouTube Auth Success</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #27ae60;">Authentication Successful!</h1>
                    <p>YouTube account connected successfully.</p>
                    <p>You can close this window and return to the application.</p>
                    <script>
                        if (window.opener) {
                            window.opener.postMessage({type: 'youtube_auth_success'}, '*');
                        }
                        setTimeout(() => window.close(), 2000);
                    </script>
                </body>
                </html>
            """)
        else:
            raise Exception("Failed to complete authentication")

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return HTMLResponse(content=f"""
            <html>
            <head><title>YouTube Auth Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">Authentication Failed</h1>
                <p>Error: {str(e)}</p>
                <p>You can close this window.</p>
            </body>
            </html>
        """)


@router.post("/auth/revoke")
async def revoke_youtube_auth():
    """Revoke YouTube authentication."""
    try:
        youtube_uploader.revoke_credentials()
        return {"message": "YouTube credentials revoked"}
    except Exception as e:
        logger.error(f"Error revoking credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))
