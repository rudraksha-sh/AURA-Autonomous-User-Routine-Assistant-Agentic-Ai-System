from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str = "user"
    profile_photo_available: bool = False
    email_verified: bool = True

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str | None = None
    requires_otp: bool = False
    challenge_id: str | None = None


class EmailCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class EmailRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(EmailCodeRequest):
    new_password: str = Field(min_length=8, max_length=100)


class LoginOtpRequest(BaseModel):
    challenge_id: str = Field(min_length=20, max_length=2000)
    code: str = Field(pattern=r"^\d{6}$")


class TwoFactorRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=100)
    code: str = Field(pattern=r"^\d{6}$")


class TwoFactorCodeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=100)
    action: str = Field(pattern=r"^(enable|disable)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
