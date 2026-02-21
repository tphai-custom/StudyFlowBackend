from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

UserRole = Literal["student", "parent", "admin"]


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6)
    role: UserRole = "student"
    last_name: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=64)
    date_of_birth: Optional[date] = None
    address: Optional[str] = Field(default=None, max_length=256)
    bio: Optional[str] = Field(default=None, max_length=512)
    hobbies: list[str] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("Username không được chứa khoảng trắng")
        return v.lower()


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    role: UserRole
    last_name: str
    first_name: str
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    hobbies: list[str] = Field(default_factory=list)
    link_code: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class UserUpdate(BaseModel):
    last_name: Optional[str] = Field(default=None, max_length=64)
    first_name: Optional[str] = Field(default=None, max_length=64)
    date_of_birth: Optional[date] = None
    address: Optional[str] = Field(default=None, max_length=256)
    bio: Optional[str] = Field(default=None, max_length=512)
    hobbies: Optional[list[str]] = None
