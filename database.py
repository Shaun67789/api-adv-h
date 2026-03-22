import os
import uuid
import secrets
from datetime import datetime, date, time as dt_time
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Date, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mediaapi.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String)
    plan = Column(String, default="free")  # free, pro, unlimited
    max_requests = Column(Integer, default=100)
    used_requests = Column(Integer, default=0)
    daily_requests = Column(Integer, default=0)
    last_reset = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    note = Column(Text, default="")


class Media(Base):
    __tablename__ = "media_library"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    platform = Column(String, index=True)
    url = Column(Text)
    direct_url = Column(Text)
    thumbnail = Column(Text)
    media_type = Column(String)  # video/audio
    quality = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key = Column(String, index=True)
    platform = Column(String)
    url = Column(Text)
    media_type = Column(String)
    status = Column(String)
    error_msg = Column(Text, default="")
    ip_address = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def generate_api_key() -> str:
    return "mapi_" + secrets.token_urlsafe(32)


def create_api_key(name: str, email: str, plan: str = "free", max_requests: int = None, note: str = "") -> APIKey:
    db = SessionLocal()
    try:
        limits = {"free": int(os.getenv("MAX_FREE_REQUESTS", "100")), "pro": 1000, "unlimited": 999999}
        if max_requests is None:
            max_requests = limits.get(plan, 100)
        key = APIKey(
            id=str(uuid.uuid4()),
            key=generate_api_key(),
            name=name, email=email, plan=plan,
            max_requests=max_requests, note=note,
        )
        db.add(key)
        db.commit()
        db.refresh(key)
        return key
    finally:
        db.close()


def validate_api_key(api_key: str):
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == True).first()
        if not key:
            return None, "Invalid or inactive API key"
        today = date.today()
        if key.last_reset != today:
            key.daily_requests = 0
            key.last_reset = today
            db.commit()
        if key.plan != "unlimited" and key.daily_requests >= key.max_requests:
            return None, f"Daily limit of {key.max_requests} requests exceeded. Upgrade your plan."
        return key, None
    finally:
        db.close()


def save_media(title: str, platform: str, url: str, direct_url: str, thumbnail: str, media_type: str, quality: str):
    db = SessionLocal()
    try:
        # Check if URL already exists to avoid duplicates
        existing = db.query(Media).filter(Media.url == url, Media.media_type == media_type, Media.quality == quality).first()
        if existing:
            existing.direct_url = direct_url
            existing.created_at = datetime.utcnow()
            db.commit()
            return existing
        
        media = Media(
            id=str(uuid.uuid4()),
            title=title, platform=platform, url=url,
            direct_url=direct_url, thumbnail=thumbnail,
            media_type=media_type, quality=quality
        )
        db.add(media)
        db.commit()
        db.refresh(media)
        return media
    finally:
        db.close()


def get_library(limit: int = 50, platform: str = None):
    db = SessionLocal()
    try:
        q = db.query(Media).order_by(Media.created_at.desc())
        if platform:
            q = q.filter(Media.platform == platform)
        return q.limit(limit).all()
    finally:
        db.close()


def increment_usage(api_key: str, platform: str, url: str, media_type: str, status: str, error_msg: str = "", ip: str = ""):
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == api_key).first()
        if key:
            key.used_requests += 1
            key.daily_requests += 1
            db.commit()
        log = RequestLog(
            id=str(uuid.uuid4()),
            api_key=api_key,
            platform=platform, url=(url or "")[:500],
            media_type=media_type, status=status,
            error_msg=(error_msg or "")[:500],
            ip_address=ip,
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


def get_all_keys():
    db = SessionLocal()
    try:
        return db.query(APIKey).order_by(APIKey.created_at.desc()).all()
    finally:
        db.close()


def get_key_by_value(key_val: str):
    db = SessionLocal()
    try:
        return db.query(APIKey).filter(APIKey.key == key_val).first()
    finally:
        db.close()


def revoke_key(key_val: str) -> bool:
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == key_val).first()
        if key:
            key.is_active = False
            db.commit()
            return True
        return False
    finally:
        db.close()


def delete_key(key_val: str) -> bool:
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == key_val).first()
        if key:
            db.delete(key)
            db.commit()
            return True
        return False
    finally:
        db.close()


def get_logs(limit: int = 100, api_key: str = None):
    db = SessionLocal()
    try:
        q = db.query(RequestLog).order_by(RequestLog.timestamp.desc())
        if api_key:
            q = q.filter(RequestLog.api_key == api_key)
        return q.limit(limit).all()
    finally:
        db.close()


def get_stats() -> dict:
    db = SessionLocal()
    try:
        total_keys = db.query(APIKey).count()
        active_keys = db.query(APIKey).filter(APIKey.is_active == True).count()
        total_requests = db.query(RequestLog).count()
        today_start = datetime.combine(date.today(), dt_time.min)
        today_requests = db.query(RequestLog).filter(RequestLog.timestamp >= today_start).count()
        success = db.query(RequestLog).filter(RequestLog.status == "success").count()
        return {
            "total_keys": total_keys, "active_keys": active_keys,
            "total_requests": total_requests, "today_requests": today_requests,
            "success_requests": success, "error_requests": total_requests - success,
        }
    finally:
        db.close()


def update_key(key_val: str, **kwargs) -> bool:
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key == key_val).first()
        if not key:
            return False
        for field, value in kwargs.items():
            if hasattr(key, field):
                setattr(key, field, value)
        db.commit()
        return True
    finally:
        db.close()
