import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import (
    ProfileMutationResponse,
    ProfileResponse,
    ProfileUpdate,
    ThemePreferenceMutationResponse,
    ThemePreferenceResponse,
    ThemePreferenceUpdate,
)

router = APIRouter(prefix="/profile", tags=["Profile"])
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_DIRECTORY = Path(__file__).resolve().parents[3] / "private_uploads" / "profile_photos"


def profile_data(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role,
            "profile_photo_available": bool(user.profile_photo_filename)}


def mutation_data(user: User) -> dict:
    return {**profile_data(user), "access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


def theme_data(user: User) -> dict:
    return {"theme": user.theme_preference}


def theme_mutation_data(user: User) -> dict:
    return {**theme_data(user), "access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


def safe_photo_path(filename: str) -> Path:
    if Path(filename).name != filename or not filename.startswith("profile-"):
        raise HTTPException(status_code=404, detail="Profile photo not found")
    path = (PHOTO_DIRECTORY / filename).resolve()
    if path.parent != PHOTO_DIRECTORY.resolve():
        raise HTTPException(status_code=404, detail="Profile photo not found")
    return path


@router.get("", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user)):
    return profile_data(user)


@router.get("/theme", response_model=ThemePreferenceResponse)
def get_theme_preference(user: User = Depends(get_current_user)):
    return theme_data(user)


@router.put("/theme", response_model=ThemePreferenceMutationResponse)
def update_theme_preference(data: ThemePreferenceUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.theme_preference = data.theme
    db.commit()
    db.refresh(user)
    return theme_mutation_data(user)


@router.patch("", response_model=ProfileMutationResponse)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    email = str(data.email).lower()
    collision = db.scalar(select(User).where(User.email == email, User.id != user.id))
    if collision:
        raise HTTPException(status_code=409, detail="Email is already registered")
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be blank")
    user.name = name
    user.email = email
    db.commit()
    db.refresh(user)
    return mutation_data(user)


@router.get("/photo")
def get_profile_photo(user: User = Depends(get_current_user)):
    if not user.profile_photo_filename:
        raise HTTPException(status_code=404, detail="No profile photo is set")
    path = safe_photo_path(user.profile_photo_filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Profile photo not found")
    content_type = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower())
    if content_type is None:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    return Response(path.read_bytes(), media_type=content_type, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/photo", response_model=ProfileMutationResponse)
async def upload_profile_photo(file: UploadFile = File(...), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    payload = await file.read(MAX_PHOTO_BYTES + 1)
    if len(payload) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Profile photos must be 5 MB or smaller")
    if payload.startswith(b"\xff\xd8\xff"):
        extension = ".jpg"
    elif payload.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = ".png"
    elif len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        extension = ".webp"
    else:
        raise HTTPException(status_code=415, detail="Upload a valid JPEG, PNG, or WebP image")

    PHOTO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    filename = f"profile-{uuid.uuid4().hex}{extension}"
    path = safe_photo_path(filename)
    old_filename = user.profile_photo_filename
    path.write_bytes(payload)
    try:
        user.profile_photo_filename = filename
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    if old_filename and old_filename != filename:
        safe_photo_path(old_filename).unlink(missing_ok=True)
    return mutation_data(user)


@router.delete("/photo", response_model=ProfileMutationResponse)
def remove_profile_photo(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    old_filename = user.profile_photo_filename
    user.profile_photo_filename = None
    db.commit()
    db.refresh(user)
    if old_filename:
        safe_photo_path(old_filename).unlink(missing_ok=True)
    return mutation_data(user)
