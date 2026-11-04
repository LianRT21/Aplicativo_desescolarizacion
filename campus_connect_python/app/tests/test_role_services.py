from datetime import date

from app.core.security import AuthContext, UserRole
from app.domain.models import Attendance, Grade, ObserverCategory, ObserverRecord, Student, StudentStatus
from app.services.attendance_service import AttendanceService
from app.services.grade_service import GradeService
from app.services.observer_service import ObserverService


def test_attendance_service_allows_teacher_to_register():
    service = AttendanceService()
    auth = AuthContext(user_id="doc-1", role=UserRole.DOCENTE)
    attendance = Attendance(student_id="stu-1", date=date(2026, 9, 1), present=False)

    result = service.register_attendance(attendance, auth)

    assert result.student_id == "stu-1"
    assert result.present is False


def test_grade_service_allows_parent_to_list_grades():
    service = GradeService()
    auth = AuthContext(user_id="stu-1", role=UserRole.ACUDIENTE)
    service.register_grade(Grade(student_id="stu-1", subject="Matemáticas", period="Corte 1", value=4.5), AuthContext(user_id="doc-1", role=UserRole.DOCENTE))

    grades = service.list_grades("stu-1", auth)

    assert len(grades) == 1
    assert grades[0].subject == "Matemáticas"


def test_observer_service_allows_director_to_add_record():
    service = ObserverService()
    auth = AuthContext(user_id="dir-1", role=UserRole.DIRECTIVO)
    record = ObserverRecord(student_id="stu-2", category=ObserverCategory.FAMILIAR, description="Falta de apoyo domiciliario")

    result = service.add_observation(record, auth)

    assert result.student_id == "stu-2"
    assert result.category == ObserverCategory.FAMILIAR
