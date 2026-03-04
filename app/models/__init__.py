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
from app.models.parent import ParentStudentLink, ParentSuggestion, ParentNote
from app.models.parent_settings_lock import ParentSettingsLock
from app.models.plan_override import PlanOverride
from app.models.exchange import ExchangeMessage
from app.models.assigned import (
    ParentAssignedTask,
    ParentAssignedHabit,
    HabitTick,
    ParentIdea,
    ParentSettings,
    ParentTaskItem,
    TaskUpdate,
)

__all__ = [
    "Task", "Habit", "FreeSlot", "PlanRecord",
    "Feedback", "AppSettings", "UserProfile", "LibraryItem", "ImportDraft",
    "User", "ParentStudentLink", "ParentSuggestion", "ParentNote", "ParentSettingsLock", "PlanOverride",
    "ExchangeMessage",
    "ParentAssignedTask", "ParentAssignedHabit", "HabitTick", "ParentIdea", "ParentSettings",
    "ParentTaskItem", "TaskUpdate",
]
