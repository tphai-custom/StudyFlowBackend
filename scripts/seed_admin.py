"""Seed script: upsert the fixed admin account.

Fixed credentials (change only via this script or admin reset-password):
    username : admin  (login is case-insensitive — type "Admin" or "admin")
    password : Nopass1!
    role     : admin
    is_active: true

Usage (from project root):
    python scripts/seed_admin.py

No env vars required. The script is idempotent:
  - If 'admin' doesn't exist → create.
  - If it exists but role/is_active is wrong → fix in place.
  - If it exists and is already correct → no-op.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.user import User

# ── Fixed admin credentials ───────────────────────────────────────────────────
ADMIN_USERNAME = "admin"          # stored lowercase; login lowercases input
ADMIN_PASSWORD = "Nopass1!"
ADMIN_LAST_NAME = "Admin"
ADMIN_FIRST_NAME = ""


async def seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        existing: User | None = (
            await db.execute(select(User).where(User.username == ADMIN_USERNAME))
        ).scalar_one_or_none()

        if existing:
            changed = False
            if existing.role != "admin":
                existing.role = "admin"
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if changed:
                await db.commit()
                print(f"✓ Admin user '{ADMIN_USERNAME}' updated (role/is_active fixed).")
            else:
                print(f"✓ Admin user '{ADMIN_USERNAME}' already exists and is correct. Nothing to do.")
            return

        admin = User(
            id=str(uuid.uuid4()),
            username=ADMIN_USERNAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="admin",
            last_name=ADMIN_LAST_NAME,
            first_name=ADMIN_FIRST_NAME,
            hobbies=[],
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"✓ Admin user '{ADMIN_USERNAME}' created. Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
