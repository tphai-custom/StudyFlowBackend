"""Models package.

Import all models here so Alembic autogenerate can detect them.
"""
from app.models.task import Task
from app.models.habit import Habit
from app.models.free_slot import FreeSlot
from app.models.plan import PlanRecord
from app.models.feedback import Feedback
from app.models.settings import AppSettings
from app.models.profile import UserProfile
from app.models.library import LibraryItem
from app.models.import_draft import ImportDraft
from app.models.user import User
from app.models.parent import ParentStudentLink, ParentSuggestion

__all__ = [
    "Task", "Habit", "FreeSlot", "PlanRecord",
    "Feedback", "AppSettings", "UserProfile", "LibraryItem", "ImportDraft",
    "User", "ParentStudentLink", "ParentSuggestion",
]
