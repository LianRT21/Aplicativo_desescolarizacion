from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_risk_evaluation_endpoint_returns_red_alert():
    payload = {
        "id": "stu-001",
        "full_name": "Ana Gómez",
        "document_number": "1012345678",
        "grade": "11A",
        "status": "ACTIVE",
        "attendance_records": [
            {"student_id": "stu-001", "date": "2026-09-01", "present": False},
            {"student_id": "stu-001", "date": "2026-09-02", "present": False},
            {"student_id": "stu-001", "date": "2026-09-03", "present": False},
            {"student_id": "stu-001", "date": "2026-09-04", "present": False},
            {"student_id": "stu-001", "date": "2026-09-05", "present": True},
            {"student_id": "stu-001", "date": "2026-09-06", "present": False},
        ],
        "grades": [
            {"student_id": "stu-001", "subject": "Matemáticas", "period": "Corte 1", "value": 2.8},
            {"student_id": "stu-001", "subject": "Física", "period": "Corte 1", "value": 3.2},
            {"student_id": "stu-001", "subject": "Química", "period": "Corte 1", "value": 2.7},
            {"student_id": "stu-001", "subject": "Español", "period": "Corte 1", "value": 3.5},
            {"student_id": "stu-001", "subject": "Matemáticas", "period": "Corte 2", "value": 2.1},
            {"student_id": "stu-001", "subject": "Física", "period": "Corte 2", "value": 2.6},
            {"student_id": "stu-001", "subject": "Química", "period": "Corte 2", "value": 2.3},
            {"student_id": "stu-001", "subject": "Español", "period": "Corte 2", "value": 3.0},
        ],
        "observer_records": [
            {
                "student_id": "stu-001",
                "category": "Familiar/Entorno",
                "description": "Inasistencia del acudiente a la citación.",
                "severity": "MEDIUM",
            },
            {
                "student_id": "stu-001",
                "category": "Convivencial",
                "description": "Convivencia conflictiva con pares.",
                "severity": "MEDIUM",
            },
        ],
        "absent_parent_meetings": 2,
        "warnings_this_month": 3,
    }

    response = client.post("/api/v1/risk/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "ROJO"
    assert body["final_score"] >= 60
    assert body["should_notify_immediately"] is True
    assert body["triggers"]
    assert body["recommended_actions"]
