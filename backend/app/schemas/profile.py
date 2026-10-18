from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    profile_photo_available: bool

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class ProfileMutationResponse(ProfileResponse):
    access_token: str
    token_type: str = "bearer"


class ThemePreferenceUpdate(BaseModel):
    theme: Literal["light", "dark", "system"]


class ThemePreferenceResponse(BaseModel):
    theme: Literal["light", "dark", "system"]


class ThemePreferenceMutationResponse(ThemePreferenceResponse):
    access_token: str
    token_type: str = "bearer"
