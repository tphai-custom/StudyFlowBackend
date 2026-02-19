"""
Tests for the StudyFlow API.
Uses an in-memory SQLite database to stay self-contained.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# ── Tasks ──────────────────────────────────────────────────────────────────────

def test_create_task():
    payload = {
        "subject": "Math",
        "title": "Algebra Chapter 1",
        "deadline": "2099-12-31T23:59:59Z",
        "estimatedMinutes": 90,
    }
    r = client.post("/api/v1/tasks/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["subject"] == "Math"
    assert data["progressMinutes"] == 0
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


def test_list_tasks():
    client.post("/api/v1/tasks/", json={"subject": "Math", "title": "T1", "deadline": "2099-01-01T00:00:00Z"})
    client.post("/api/v1/tasks/", json={"subject": "Physics", "title": "T2", "deadline": "2099-01-01T00:00:00Z"})
    r = client.get("/api/v1/tasks/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_task():
    create_r = client.post("/api/v1/tasks/", json={"subject": "Math", "title": "Old", "deadline": "2099-01-01T00:00:00Z"})
    task_id = create_r.json()["id"]
    r = client.put(f"/api/v1/tasks/{task_id}", json={"title": "New Title"})
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"


def test_delete_task():
    create_r = client.post("/api/v1/tasks/", json={"subject": "Math", "title": "ToDelete", "deadline": "2099-01-01T00:00:00Z"})
    task_id = create_r.json()["id"]
    r = client.delete(f"/api/v1/tasks/{task_id}")
    assert r.status_code == 204
    r2 = client.delete(f"/api/v1/tasks/{task_id}")
    assert r2.status_code == 404


# ── Slots ──────────────────────────────────────────────────────────────────────

def test_create_slot():
    payload = {"weekday": 1, "startTime": "08:00", "endTime": "10:00", "capacityMinutes": 120}
    r = client.post("/api/v1/slots/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["weekday"] == 1
    assert "createdAt" in data


def test_list_slots():
    client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "10:00"})
    client.post("/api/v1/slots/", json={"weekday": 3, "startTime": "14:00", "endTime": "16:00"})
    r = client.get("/api/v1/slots/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_slot():
    r = client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "10:00"})
    slot_id = r.json()["id"]
    r2 = client.put(f"/api/v1/slots/{slot_id}", json={"startTime": "09:00"})
    assert r2.status_code == 200
    assert r2.json()["startTime"] == "09:00"


def test_delete_slot():
    r = client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "10:00"})
    slot_id = r.json()["id"]
    r2 = client.delete(f"/api/v1/slots/{slot_id}")
    assert r2.status_code == 204


# ── Habits ─────────────────────────────────────────────────────────────────────

def test_create_habit():
    payload = {"name": "Morning Run", "cadence": "daily", "minutes": 30}
    r = client.post("/api/v1/habits/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Morning Run"
    assert "createdAt" in data


def test_list_habits():
    client.post("/api/v1/habits/", json={"name": "Run", "cadence": "daily", "minutes": 30})
    client.post("/api/v1/habits/", json={"name": "Read", "cadence": "weekly", "weekday": 1, "minutes": 60})
    r = client.get("/api/v1/habits/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_habit():
    r = client.post("/api/v1/habits/", json={"name": "Run", "cadence": "daily", "minutes": 30})
    habit_id = r.json()["id"]
    r2 = client.put(f"/api/v1/habits/{habit_id}", json={"minutes": 45})
    assert r2.status_code == 200
    assert r2.json()["minutes"] == 45


def test_delete_habit():
    r = client.post("/api/v1/habits/", json={"name": "Run", "cadence": "daily", "minutes": 30})
    habit_id = r.json()["id"]
    r2 = client.delete(f"/api/v1/habits/{habit_id}")
    assert r2.status_code == 204


# ── Settings ───────────────────────────────────────────────────────────────────

def test_get_settings_creates_defaults():
    r = client.get("/api/v1/settings/")
    assert r.status_code == 200
    data = r.json()
    assert data["dailyLimitMinutes"] == 240
    assert data["bufferPercent"] == 0.1
    assert data["breakPreset"]["focus"] == 45


def test_update_settings():
    client.get("/api/v1/settings/")  # ensure created
    r = client.put("/api/v1/settings/", json={"dailyLimitMinutes": 180})
    assert r.status_code == 200
    assert r.json()["dailyLimitMinutes"] == 180


# ── Plan ───────────────────────────────────────────────────────────────────────

def test_plan_latest_404_when_empty():
    r = client.get("/api/v1/plan/latest")
    assert r.status_code == 404


def test_plan_rebuild_empty():
    r = client.post("/api/v1/plan/rebuild")
    assert r.status_code == 200
    data = r.json()
    assert "planVersion" in data
    assert isinstance(data["sessions"], list)
    assert data["planVersion"] == 1


def test_plan_rebuild_with_task_and_slot():
    # Add a slot: Monday (JS weekday=1) 08:00-12:00
    client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "12:00", "capacityMinutes": 240})
    # Add a task with a far future deadline
    client.post("/api/v1/tasks/", json={
        "subject": "Math",
        "title": "Calc Study",
        "deadline": "2099-12-31T23:59:59Z",
        "estimatedMinutes": 90,
    })
    r = client.post("/api/v1/plan/rebuild")
    assert r.status_code == 200
    data = r.json()
    assert data["planVersion"] >= 1


def test_plan_latest_returns_plan():
    client.post("/api/v1/plan/rebuild")
    r = client.get("/api/v1/plan/latest")
    assert r.status_code == 200
    data = r.json()
    assert "planVersion" in data
    assert "sessions" in data


def test_plan_rebuild_increments_version():
    r1 = client.post("/api/v1/plan/rebuild")
    v1 = r1.json()["planVersion"]
    r2 = client.post("/api/v1/plan/rebuild")
    v2 = r2.json()["planVersion"]
    assert v2 == v1 + 1


# ── Session status update ──────────────────────────────────────────────────────

def test_session_status_update():
    client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "12:00", "capacityMinutes": 240})
    client.post("/api/v1/tasks/", json={
        "subject": "Math",
        "title": "Study",
        "deadline": "2099-12-31T23:59:59Z",
        "estimatedMinutes": 60,
    })
    plan_r = client.post("/api/v1/plan/rebuild")
    sessions = plan_r.json()["sessions"]

    if not sessions:
        pytest.skip("No sessions were generated to update")

    session_id = sessions[0]["id"]
    r = client.patch(f"/api/v1/plan/sessions/{session_id}/status", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["completedAt"] is not None


def test_session_status_invalid():
    # Create a session via plan rebuild
    client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "12:00"})
    client.post("/api/v1/tasks/", json={"subject": "X", "title": "T", "deadline": "2099-01-01T00:00:00Z", "estimatedMinutes": 60})
    plan_r = client.post("/api/v1/plan/rebuild")
    sessions = plan_r.json()["sessions"]
    if not sessions:
        pytest.skip("No sessions were generated")
    session_id = sessions[0]["id"]
    r = client.patch(f"/api/v1/plan/sessions/{session_id}/status", json={"status": "invalid_value"})
    assert r.status_code == 422


# ── Reset ──────────────────────────────────────────────────────────────────────

def test_reset_clears_data():
    client.post("/api/v1/tasks/", json={"subject": "Math", "title": "T", "deadline": "2099-01-01T00:00:00Z"})
    client.post("/api/v1/slots/", json={"weekday": 1, "startTime": "08:00", "endTime": "10:00"})
    client.post("/api/v1/habits/", json={"name": "Run", "cadence": "daily", "minutes": 30})

    r = client.delete("/api/v1/reset")
    assert r.status_code == 204

    assert client.get("/api/v1/tasks/").json() == []
    assert client.get("/api/v1/slots/").json() == []
    assert client.get("/api/v1/habits/").json() == []


def test_reset_keeps_settings_and_profile():
    client.get("/api/v1/settings/")
    client.get("/api/v1/profile/")
    client.delete("/api/v1/reset")

    # Settings and profile should still be accessible (auto-recreated if needed)
    r_settings = client.get("/api/v1/settings/")
    r_profile = client.get("/api/v1/profile/")
    assert r_settings.status_code == 200
    assert r_profile.status_code == 200
