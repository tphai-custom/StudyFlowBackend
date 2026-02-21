from __future__ import annotations

import random
import string
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserRegister, UserUpdate


def _generate_link_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=7))


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def create_user(db: AsyncSession, payload: UserRegister) -> User:
    link_code = _generate_link_code() if payload.role == "student" else None
    user = User(
        id=str(uuid.uuid4()),
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        last_name=payload.last_name,
        first_name=payload.first_name,
        date_of_birth=payload.date_of_birth,
        address=payload.address,
        bio=payload.bio,
        hobbies=payload.hobbies,
        link_code=link_code,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def set_active(db: AsyncSession, user: User, active: bool) -> User:
    user.is_active = active
    await db.flush()
    await db.refresh(user)
    return user


async def reset_password(db: AsyncSession, user: User, new_password: str) -> User:
    user.hashed_password = hash_password(new_password)
    await db.flush()
    await db.refresh(user)
    return user


async def rotate_link_code(db: AsyncSession, user: User) -> User:
    """Generate a fresh 7-char link code for a student, invalidating the old one."""
    user.link_code = _generate_link_code()
    await db.flush()
    return user
