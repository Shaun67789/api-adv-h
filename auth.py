import os
from fastapi import Header, HTTPException, Request
from database import validate_api_key


async def require_api_key(request: Request, x_api_key: str = Header(None, alias="X-API-Key")):
    api_key = x_api_key or request.query_params.get("api_key")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Add header: X-API-Key or query param: ?api_key=YOUR_KEY"
        )
    key_obj, error = validate_api_key(api_key)
    if error:
        code = 429 if "limit" in error else 401
        raise HTTPException(status_code=code, detail=error)
    return key_obj


def require_admin(x_admin_key: str = Header(None, alias="X-Admin-Key")):
    admin_secret = os.getenv("ADMIN_SECRET", "2810")
    if x_admin_key != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    return True
