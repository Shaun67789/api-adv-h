from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from auth import require_api_key
from database import increment_usage, create_api_key, get_logs, save_media, get_library
import downloader

router = APIRouter()


def get_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")


class PublicKeyRequest(BaseModel):
    name: str
    email: str


@router.post("/keys/create")
async def public_create_key(body: PublicKeyRequest):
    """Public endpoint — anyone can create a free API key"""
    key = create_api_key(body.name, body.email, "free")
    return {
        "success": True,
        "message": "Your free API key has been created!",
        "data": {
            "key": key.key, "name": key.name,
            "plan": key.plan, "daily_limit": key.max_requests,
        },
    }


@router.get("/info")
async def get_info(
    url: str = Query(..., description="Any supported media URL"),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Get full metadata for any media URL"""
    try:
        data = await downloader.get_info(url)
        increment_usage(key.key, data.get("platform", "unknown"), url, "info", "success", ip=get_ip(request))
        return {"success": True, "data": data}
    except Exception as e:
        plat = downloader.detect_platform(url)
        increment_usage(key.key, plat, url, "info", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download")
async def download_media(
    url: str = Query(..., description="Media URL"),
    type: str = Query("video", description="video | audio | thumbnail"),
    quality: str = Query("best", description="best | 1080p | 720p | 480p | 360p | 240p | 144p"),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Universal download — returns direct CDN URL"""
    try:
        if type == "thumbnail":
            data = await downloader.get_thumbnail(url)
        else:
            data = await downloader.get_direct_url(url, type, quality)
        
        plat = data.get("platform", downloader.detect_platform(url))
        increment_usage(key.key, plat, url, type, "success", ip=get_ip(request))
        
        # Save to Library
        if type != "thumbnail":
            save_media(
                title=data.get("title", "Unknown"),
                platform=plat,
                url=url,
                direct_url=data.get("direct_url"),
                thumbnail=data.get("thumbnail"),
                media_type=type,
                quality=quality
            )
            
        return {"success": True, "data": data}
    except Exception as e:
        increment_usage(key.key, downloader.detect_platform(url), url, type, "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/video")
async def get_video(
    url: str = Query(...),
    quality: str = Query("best", description="best | 1080p | 720p | 480p | 360p | 240p"),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Get direct video URL"""
    try:
        data = await downloader.get_direct_url(url, "video", quality)
        plat = data.get("platform")
        increment_usage(key.key, plat, url, "video", "success", ip=get_ip(request))
        
        # Save to Library
        save_media(
            title=data.get("title", "Unknown"),
            platform=plat,
            url=url,
            direct_url=data.get("direct_url"),
            thumbnail=data.get("thumbnail"),
            media_type="video",
            quality=quality
        )
        
        return {"success": True, "data": data}
    except Exception as e:
        increment_usage(key.key, downloader.detect_platform(url), url, "video", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audio")
async def get_audio(
    url: str = Query(...),
    format: str = Query("mp3", description="mp3 | m4a | ogg | wav"),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Get direct audio URL"""
    try:
        data = await downloader.get_direct_url(url, "audio")
        data["requested_format"] = format
        plat = data.get("platform")
        increment_usage(key.key, plat, url, "audio", "success", ip=get_ip(request))
        
        # Save to Library
        save_media(
            title=data.get("title", "Unknown"),
            platform=plat,
            url=url,
            direct_url=data.get("direct_url"),
            thumbnail=data.get("thumbnail"),
            media_type="audio",
            quality="best"
        )
        
        return {"success": True, "data": data}
    except Exception as e:
        increment_usage(key.key, downloader.detect_platform(url), url, "audio", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/thumbnail")
async def get_thumbnail(
    url: str = Query(...),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Get all available thumbnail URLs"""
    try:
        data = await downloader.get_thumbnail(url)
        increment_usage(key.key, data.get("platform"), url, "thumbnail", "success", ip=get_ip(request))
        return {"success": True, "data": data}
    except Exception as e:
        increment_usage(key.key, downloader.detect_platform(url), url, "thumbnail", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/formats")
async def get_formats(
    url: str = Query(...),
    request: Request = None,
    key=Depends(require_api_key),
):
    """List all available formats for a URL"""
    try:
        data = await downloader.get_formats(url)
        increment_usage(key.key, data.get("platform"), url, "formats", "success", ip=get_ip(request))
        return {"success": True, "data": data}
    except Exception as e:
        increment_usage(key.key, downloader.detect_platform(url), url, "formats", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/playlist")
async def get_playlist(
    url: str = Query(...),
    max_items: int = Query(20, ge=1, le=50),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Get playlist items (YouTube playlists, channels, etc.)"""
    try:
        data = await downloader.get_playlist(url, max_items)
        increment_usage(key.key, data.get("platform"), url, "playlist", "success", ip=get_ip(request))
        return {"success": True, "data": data}
    except Exception as e:
        increment_usage(key.key, downloader.detect_platform(url), url, "playlist", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/universal")
async def universal_api(
    url: str = Query(..., description="Any supported media URL"),
    request: Request = None,
    key=Depends(require_api_key),
):
    """Universal API: Returns metadata + direct video & audio links in one call"""
    try:
        # 1. Get Metadata
        info = await downloader.get_info(url)
        
        # 2. Get Best Video Link
        video = await downloader.get_direct_url(url, "video", "best")
        
        # 3. Get Best Audio Link
        audio = await downloader.get_direct_url(url, "audio")
        
        plat = info.get("platform", "unknown")
        
        # Save to Library (Video version)
        save_media(
            title=info.get("title", "Unknown"),
            platform=plat,
            url=url,
            direct_url=video.get("direct_url"),
            thumbnail=info.get("thumbnail"),
            media_type="video",
            quality="best"
        )
        
        data = {
            "metadata": info,
            "download": {
                "video": video,
                "audio": audio
            }
        }
        
        increment_usage(key.key, plat, url, "universal", "success", ip=get_ip(request))
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        plat = downloader.detect_platform(url)
        increment_usage(key.key, plat, url, "universal", "error", str(e), ip=get_ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/library")
async def browse_library(
    limit: int = Query(50, ge=1, le=200),
    platform: str = Query(None),
    key=Depends(require_api_key),
):
    """Browse the 'Database' — recently processed media"""
    items = get_library(limit, platform)
    return {
        "success": True,
        "total": len(items),
        "data": [
            {
                "title": i.title, "platform": i.platform,
                "url": i.url, "direct_url": i.direct_url,
                "thumbnail": i.thumbnail, "media_type": i.media_type,
                "quality": i.quality, "created_at": i.created_at.isoformat() if i.created_at else None
            } for i in items
        ]
    }


@router.get("/usage")
async def get_usage(key=Depends(require_api_key)):
    """Get API key usage stats"""
    return {
        "success": True,
        "data": {
            "key_preview": key.key[:10] + "..." + key.key[-5:],
            "name": key.name, "email": key.email,
            "plan": key.plan, "is_active": key.is_active,
            "daily_used": key.daily_requests,
            "daily_limit": key.max_requests,
            "total_used": key.used_requests,
            "remaining_today": max(0, key.max_requests - key.daily_requests),
        },
    }


@router.get("/logs/my")
async def my_logs(limit: int = Query(20, ge=1, le=100), key=Depends(require_api_key)):
    """Get your recent request history"""
    logs = get_logs(limit, key.key)
    return {
        "success": True,
        "data": [
            {"platform": l.platform, "media_type": l.media_type,
             "status": l.status, "timestamp": l.timestamp.isoformat() if l.timestamp else None}
            for l in logs
        ],
    }
