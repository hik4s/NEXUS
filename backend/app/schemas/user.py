from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role_keys: list[str] = Field(default_factory=lambda: ["employee"], min_length=1, max_length=5)


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role_keys: list[str] | None = Field(default=None, min_length=1, max_length=5)
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
