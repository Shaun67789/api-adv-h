import asyncio
import os
import re
from typing import Optional
import yt_dlp

COOKIES_FILE = "cookies.txt"

PLATFORM_PATTERNS = {
    "youtube": r"(youtube\.com|youtu\.be)",
    "instagram": r"instagram\.com",
    "tiktok": r"tiktok\.com",
    "twitter": r"(twitter\.com|x\.com)",
    "facebook": r"(facebook\.com|fb\.watch)",
    "reddit": r"reddit\.com",
    "vimeo": r"vimeo\.com",
    "soundcloud": r"soundcloud\.com",
    "dailymotion": r"dailymotion\.com",
    "twitch": r"twitch\.tv",
    "pinterest": r"pinterest\.",
    "bilibili": r"bilibili\.com",
    "rumble": r"rumble\.com",
    "odysee": r"odysee\.com",
    "linkedin": r"linkedin\.com",
}


def detect_platform(url: str) -> str:
    for platform, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "unknown"


def _build_opts(extra: dict = None) -> dict:
    opts = {"quiet": True, "no_warnings": True, "extract_flat": False, "noplaylist": True}
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    if extra:
        opts.update(extra)
    return opts


def _extract(url: str, opts: dict = None) -> dict:
    with yt_dlp.YoutubeDL(_build_opts(opts)) as ydl:
        return ydl.extract_info(url, download=False)


def _clean_fmt(f: dict) -> dict:
    return {
        "format_id": f.get("format_id"),
        "ext": f.get("ext"),
        "resolution": f.get("resolution") or f.get("format_note"),
        "fps": f.get("fps"),
        "vcodec": f.get("vcodec"),
        "acodec": f.get("acodec"),
        "filesize": f.get("filesize") or f.get("filesize_approx"),
        "has_video": f.get("vcodec") not in (None, "none"),
        "has_audio": f.get("acodec") not in (None, "none"),
    }


async def get_info(url: str) -> dict:
    info = await asyncio.to_thread(_extract, url)
    fmts = info.get("formats", [])
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": (info.get("description") or "")[:500],
        "thumbnail": info.get("thumbnail"),
        "thumbnails": [t.get("url") for t in (info.get("thumbnails") or [])[-5:]],
        "duration": info.get("duration"),
        "duration_string": info.get("duration_string"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "channel": info.get("uploader") or info.get("channel"),
        "channel_url": info.get("uploader_url") or info.get("channel_url"),
        "upload_date": info.get("upload_date"),
        "webpage_url": info.get("webpage_url") or url,
        "platform": detect_platform(url),
        "extractor": info.get("extractor"),
        "available_formats": len(fmts),
        "formats": [_clean_fmt(f) for f in fmts[:20]],
        "tags": (info.get("tags") or [])[:10],
    }


async def get_thumbnail(url: str) -> dict:
    info = await asyncio.to_thread(_extract, url)
    thumbs = info.get("thumbnails") or []
    return {
        "title": info.get("title"),
        "platform": detect_platform(url),
        "thumbnail": info.get("thumbnail"),
        "thumbnails": [{"url": t.get("url"), "width": t.get("width"), "height": t.get("height")} for t in thumbs],
    }


QUALITY_MAP = {
    "144p":  "bestvideo[height<=144]+bestaudio/best[height<=144]/best",
    "240p":  "bestvideo[height<=240]+bestaudio/best[height<=240]/best",
    "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
    "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
    "best":  "bestvideo+bestaudio/best",
}


async def get_direct_url(url: str, media_type: str = "video", quality: str = "best") -> dict:
    fmt = "bestaudio/best" if media_type == "audio" else QUALITY_MAP.get(quality, "bestvideo+bestaudio/best")
    info = await asyncio.to_thread(_extract, url, {"format": fmt})
    fmts = info.get("formats", [])
    requested = info.get("requested_formats", [])
    if requested:
        direct_url = requested[0].get("url")
        ext = requested[0].get("ext", "mp4")
    elif fmts:
        direct_url = fmts[-1].get("url")
        ext = fmts[-1].get("ext", "mp4")
    else:
        direct_url = info.get("url")
        ext = info.get("ext", "mp4")
    return {
        "title": info.get("title"),
        "platform": detect_platform(url),
        "media_type": media_type,
        "quality": quality,
        "direct_url": direct_url,
        "ext": ext,
        "filesize": info.get("filesize"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "note": "Direct CDN URL — may expire. Use promptly or proxy through your app.",
    }


async def get_formats(url: str) -> dict:
    info = await asyncio.to_thread(_extract, url)
    fmts = info.get("formats", [])
    video_fmts = [_clean_fmt(f) for f in fmts if f.get("vcodec") not in (None, "none")]
    audio_fmts = [_clean_fmt(f) for f in fmts if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")]
    return {
        "title": info.get("title"),
        "platform": detect_platform(url),
        "total_formats": len(fmts),
        "video_formats": video_fmts,
        "audio_formats": audio_fmts,
    }


async def get_playlist(url: str, max_items: int = 20) -> dict:
    def _extract_pl():
        opts = _build_opts({"extract_flat": True, "noplaylist": False, "playlistend": max_items})
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    info = await asyncio.to_thread(_extract_pl)
    entries = info.get("entries") or []
    items = [
        {"id": e.get("id"), "title": e.get("title"),
         "url": e.get("url") or e.get("webpage_url"),
         "thumbnail": e.get("thumbnail"), "duration": e.get("duration")}
        for e in entries[:max_items] if e
    ]
    return {
        "playlist_title": info.get("title"),
        "playlist_id": info.get("id"),
        "channel": info.get("uploader") or info.get("channel"),
        "total_items": len(entries),
        "returned_items": len(items),
        "items": items,
        "platform": detect_platform(url),
    }
