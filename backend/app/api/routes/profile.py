import uuid
from pathlib import Path

from datetime import datetime, timezone

import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, hash_password, require_admin, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import (
    ProfileMutationResponse,
    ProfileResponse,
    ProfileUpdate,
    ThemePreferenceMutationResponse,
    ThemePreferenceResponse,
    ThemePreferenceUpdate,
    AppearancePreferences,
    AppearancePreferenceMutationResponse,
    AIPlanningPreference,
    AIPlanningPreferenceMutationResponse,
    PasswordChange,
    PasswordChangeResponse,
)
from app.schemas.account import AccountDeleteRequest
from app.services.account_service import delete_user_account, export_user_data, export_user_data_csv

router = APIRouter(prefix="/profile", tags=["Profile"])
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_DIRECTORY = Path(__file__).resolve().parents[3] / "private_uploads" / "profile_photos"


def profile_data(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role,
            "profile_photo_available": bool(user.profile_photo_filename)}


def mutation_data(user: User) -> dict:
    return {**profile_data(user), "access_token": create_access_token({"sub": str(user.id), "ver": user.token_version}), "token_type": "bearer"}


def theme_data(user: User) -> dict:
    return {"theme": user.theme_preference}


def theme_mutation_data(user: User) -> dict:
    return {**theme_data(user), "access_token": create_access_token({"sub": str(user.id), "ver": user.token_version}), "token_type": "bearer"}


def appearance_data(user: User) -> dict:
    return {"theme": user.theme_preference, "accent_color": user.accent_color, "density": user.density, "font_size": user.font_size}


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


@router.get("/appearance", response_model=AppearancePreferences)
def get_appearance_preferences(user: User = Depends(get_current_user)):
    return appearance_data(user)


@router.put("/appearance", response_model=AppearancePreferenceMutationResponse)
def update_appearance_preferences(data: AppearancePreferences, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.theme_preference = data.theme
    user.accent_color = data.accent_color
    user.density = data.density
    user.font_size = data.font_size
    db.commit()
    db.refresh(user)
    return {**appearance_data(user), "access_token": create_access_token({"sub": str(user.id), "ver": user.token_version}), "token_type": "bearer"}


@router.get("/ai-planning", response_model=AIPlanningPreference)
def get_ai_planning_preference(user: User = Depends(get_current_user)):
    return {"use_ai_planning": user.use_ai_planning}


@router.put("/ai-planning", response_model=AIPlanningPreferenceMutationResponse)
def update_ai_planning_preference(data: AIPlanningPreference, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.use_ai_planning = data.use_ai_planning
    db.commit()
    db.refresh(user)
    return {"use_ai_planning": user.use_ai_planning, "access_token": create_access_token({"sub": str(user.id), "ver": user.token_version}), "token_type": "bearer"}


@router.put("/password", response_model=PasswordChangeResponse)
def change_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Choose a password different from your current one")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": create_access_token({"sub": str(user.id), "ver": user.token_version}), "token_type": "bearer"}


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


@router.get("/export")
def export_account_data(format: str = Query(default="json", pattern="^(json|csv)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = export_user_data(db, user.id)
    if format == "csv":
        return Response(
            content=export_user_data_csv(data),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="aura-export.csv"'},
        )
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="aura-export.json"'},
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(data: AccountDeleteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filename = delete_user_account(db, user.id)
    if filename:
        try:
            safe_photo_path(filename).unlink(missing_ok=True)
        except OSError:
            pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)
