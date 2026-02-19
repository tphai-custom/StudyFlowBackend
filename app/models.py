from sqlalchemy import Column, String, Integer, Float, JSON, Text
from app.database import Base


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    deadline = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="Asia/Ho_Chi_Minh")
    difficulty = Column(Integer, nullable=False, default=3)
    durationEstimateMin = Column(Integer, nullable=False, default=30)
    durationEstimateMax = Column(Integer, nullable=False, default=60)
    durationUnit = Column(String, nullable=False, default="minutes")
    estimatedMinutes = Column(Integer, nullable=False, default=60)
    importance = Column(Integer, nullable=True)
    contentFocus = Column(String, nullable=True)
    successCriteria = Column(JSON, nullable=False, default=list)
    milestones = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    createdAt = Column(String, nullable=False)
    updatedAt = Column(String, nullable=False)
    progressMinutes = Column(Integer, nullable=False, default=0)


class SlotModel(Base):
    __tablename__ = "slots"

    id = Column(String, primary_key=True, index=True)
    weekday = Column(Integer, nullable=False)
    startTime = Column(String, nullable=False)
    endTime = Column(String, nullable=False)
    capacityMinutes = Column(Integer, nullable=False, default=0)
    source = Column(String, nullable=True, default="user")
    createdAt = Column(String, nullable=False)


class HabitModel(Base):
    __tablename__ = "habits"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cadence = Column(String, nullable=False, default="daily")
    weekday = Column(Integer, nullable=True)
    minutes = Column(Integer, nullable=False, default=30)
    preset = Column(String, nullable=True)
    preferredStart = Column(String, nullable=True)
    energyWindow = Column(String, nullable=True)
    createdAt = Column(String, nullable=False)


class SettingsModel(Base):
    __tablename__ = "settings"

    id = Column(String, primary_key=True, index=True)
    dailyLimitMinutes = Column(Integer, nullable=False, default=240)
    bufferPercent = Column(Float, nullable=False, default=0.1)
    breakPreset = Column(JSON, nullable=False)
    timezone = Column(String, nullable=False, default="Asia/Ho_Chi_Minh")
    lastUpdated = Column(String, nullable=False)


class ProfileModel(Base):
    __tablename__ = "profile"

    id = Column(String, primary_key=True, index=True)
    gradeLevel = Column(String, nullable=False, default="Lớp 10")
    goals = Column(JSON, nullable=False, default=list)
    weakSubjects = Column(JSON, nullable=False, default=list)
    strongSubjects = Column(JSON, nullable=False, default=list)
    learningPace = Column(String, nullable=False, default="balanced")
    energyPreferences = Column(JSON, nullable=False)
    dailyLimitPreference = Column(Integer, nullable=False, default=120)
    favoriteBreakPreset = Column(String, nullable=False, default="deep-work")
    timezone = Column(String, nullable=False, default="Asia/Ho_Chi_Minh")
    updatedAt = Column(String, nullable=False)


class FeedbackModel(Base):
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, index=True)
    label = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    submittedAt = Column(String, nullable=False)
    planVersion = Column(Integer, nullable=False, default=0)


class LibraryItemModel(Base):
    __tablename__ = "library"

    id = Column(String, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    level = Column(String, nullable=False, default="")
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False, default="")
    url = Column(String, nullable=True)
    tags = Column(JSON, nullable=False, default=list)


class PlanModel(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, index=True)
    planVersion = Column(Integer, nullable=False, default=1)
    unscheduledTasks = Column(JSON, nullable=False, default=list)
    suggestions = Column(JSON, nullable=False, default=list)
    generatedAt = Column(String, nullable=False)


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    taskId = Column(String, nullable=True)
    habitId = Column(String, nullable=True)
    source = Column(String, nullable=False, default="task")
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    plannedStart = Column(String, nullable=False)
    plannedEnd = Column(String, nullable=False)
    minutes = Column(Integer, nullable=False, default=0)
    bufferMinutes = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="pending")
    checklist = Column(JSON, nullable=True)
    successCriteria = Column(JSON, nullable=True)
    milestoneTitle = Column(String, nullable=True)
    completedAt = Column(String, nullable=True)
    planVersion = Column(Integer, nullable=False, default=1)
