from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from auth import require_admin
from database import (
    create_api_key, get_all_keys, get_key_by_value,
    revoke_key, delete_key, get_logs, get_stats, update_key,
)

router = APIRouter()


class CreateKeyBody(BaseModel):
    name: str
    email: str
    plan: str = "free"
    max_requests: Optional[int] = None
    note: str = ""


class UpdateKeyBody(BaseModel):
    plan: Optional[str] = None
    max_requests: Optional[int] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


def _key_dict(k):
    return {
        "key": k.key, "name": k.name, "email": k.email,
        "plan": k.plan, "max_requests": k.max_requests,
        "used_requests": k.used_requests, "daily_requests": k.daily_requests,
        "is_active": k.is_active, "note": k.note,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


@router.get("/stats")
async def admin_stats(admin=Depends(require_admin)):
    return get_stats()


@router.get("/keys")
async def list_keys(admin=Depends(require_admin)):
    keys = get_all_keys()
    return {"total": len(keys), "keys": [_key_dict(k) for k in keys]}


@router.post("/keys")
async def create_key(body: CreateKeyBody, admin=Depends(require_admin)):
    key = create_api_key(body.name, body.email, body.plan, body.max_requests, body.note)
    return {"message": "API key created", "key": _key_dict(key)}


@router.get("/keys/{key_val}")
async def get_key_details(key_val: str, admin=Depends(require_admin)):
    key = get_key_by_value(key_val)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    logs = get_logs(30, key_val)
    data = _key_dict(key)
    data["recent_logs"] = [
        {"platform": l.platform, "media_type": l.media_type,
         "status": l.status, "timestamp": l.timestamp.isoformat() if l.timestamp else None}
        for l in logs
    ]
    return data


@router.put("/keys/{key_val}")
async def update_key_endpoint(key_val: str, body: UpdateKeyBody, admin=Depends(require_admin)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not update_key(key_val, **updates):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Key updated"}


@router.delete("/keys/{key_val}/revoke")
async def revoke(key_val: str, admin=Depends(require_admin)):
    if not revoke_key(key_val):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Key revoked"}


@router.delete("/keys/{key_val}")
async def delete(key_val: str, admin=Depends(require_admin)):
    if not delete_key(key_val):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Key deleted"}


@router.get("/logs")
async def get_request_logs(
    limit: int = Query(100, ge=1, le=500),
    api_key: str = None,
    admin=Depends(require_admin),
):
    logs = get_logs(limit, api_key)
    return {
        "total": len(logs),
        "logs": [
            {
                "api_key": l.api_key[:12] + "***" if l.api_key else "",
                "platform": l.platform, "media_type": l.media_type,
                "url": (l.url[:80] + "...") if l.url and len(l.url) > 80 else l.url,
                "status": l.status, "error_msg": l.error_msg,
                "ip": l.ip_address,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            }
            for l in logs
        ],
    }
