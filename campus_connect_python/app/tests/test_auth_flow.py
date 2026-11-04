import uuid

from fastapi.testclient import TestClient

from app.api.main import app
from app.core.database import SessionLocal, Base, engine
from app.db.models import User
from app.core.security import get_password_hash


client = TestClient(app)


def test_login_returns_token_for_default_user():
    db = SessionLocal()
    existing = db.query(User).filter(User.email == "director@campus.com").first()
    if existing is None:
        db.add(User(email="director@campus.com", full_name="Director Campus", password_hash=get_password_hash("admin123"), role="DIRECTIVO"))
        db.commit()
    db.close()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"
    assert payload["user"]["role"] == "DIRECTIVO"


def test_student_demo_account_can_only_read_its_portal():
    client.post("/api/v1/auth/seed")
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "student@campus.com", "password": "student123"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["role"] == "ESTUDIANTE"
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    portal_response = client.get("/api/v1/student/portal", headers=headers)

    assert portal_response.status_code == 200
    portal = portal_response.json()
    assert portal["student"]["full_name"] == login_response.json()["user"]["full_name"]
    assert portal["schedule"]["selected_day"] in portal["schedule"]["days"]
    assert isinstance(portal["tasks"], list)
    assert isinstance(portal["events"]["items"], list)
    assert client.get("/api/v1/dashboard", headers=headers).status_code == 403
    assert client.post("/api/v1/grades", json={}, headers=headers).status_code == 403

    teacher_login = client.post(
        "/api/v1/auth/login",
        data={"username": "teacher@campus.com", "password": "teacher123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    assert client.get("/api/v1/student/portal", headers=teacher_headers).status_code == 403


def test_student_portal_reads_schedule_tasks_and_events_from_its_course():
    client.post("/api/v1/auth/seed")
    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    director_headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}
    client.put(
        "/api/v1/courses/11/assignments/Matemáticas",
        json={"teacher_email": "teacher@campus.com"},
        headers=director_headers,
    )
    client.post("/api/v1/courses/schedule/generate", headers=director_headers)

    teacher_login = client.post(
        "/api/v1/auth/login",
        data={"username": "teacher@campus.com", "password": "teacher123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    unique_title = f"Tarea-{uuid.uuid4().hex[:8]}"
    task = client.post(
        "/api/v1/courses/11/items",
        json={
            "item_type": "TASK",
            "subject": "Matemáticas",
            "title": unique_title,
            "description": "Resolver los ejercicios asignados.",
            "date": "2026-11-20",
        },
        headers=teacher_headers,
    )
    assert task.status_code == 201
    event = client.post(
        "/api/v1/courses/11/items",
        json={
            "item_type": "EVENT",
            "subject": "Matemáticas",
            "title": "Evaluación de curso",
            "description": "Evaluación del tema actual.",
            "date": "2026-11-21",
        },
        headers=teacher_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        data={"username": "student@campus.com", "password": "student123"},
    )
    portal = client.get(
        "/api/v1/student/portal",
        headers={"Authorization": f"Bearer {student_login.json()['access_token']}"},
    )
    assert portal.status_code == 200
    payload = portal.json()
    assert any(item["title"] == unique_title for item in payload["tasks"])
    assert any(item["title"] == "Evaluación de curso" for item in payload["events"]["items"])
    assert any(item["subject"] == "Matemáticas" for item in payload["schedule"]["classes"])
