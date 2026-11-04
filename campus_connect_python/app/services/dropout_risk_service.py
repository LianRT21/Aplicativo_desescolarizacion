from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.domain.models import (
    Grade,
    ObserverCategory,
    RiskLevel,
    RiskReport,
    Student,
)


class DropoutRiskEvaluationService:
    """Deterministic evaluation engine for early school dropout risk."""

    def evaluate(self, student: Student) -> RiskReport:
        score = 0
        triggers: list[str] = []
        actions: list[str] = []

        attendance_score, attendance_triggers, attendance_actions = self._evaluate_attendance(student)
        score += attendance_score
        triggers.extend(attendance_triggers)
        actions.extend(attendance_actions)

        performance_score, performance_triggers, performance_actions = self._evaluate_performance(student)
        score += performance_score
        triggers.extend(performance_triggers)
        actions.extend(performance_actions)

        family_score, family_triggers, family_actions = self._evaluate_observer_and_family(student)
        score += family_score
        triggers.extend(family_triggers)
        actions.extend(family_actions)

        final_score = min(100, score)
        risk_level = self._risk_level_for(final_score)

        if risk_level == RiskLevel.RED:
            actions.extend(
                [
                    "Notificar de forma inmediata a directivos y acudiente.",
                    "Programar reunión de seguimiento con la familia y coordinador.",
                ]
            )

        return RiskReport(
            final_score=final_score,
            risk_level=risk_level,
            triggers=triggers,
            recommended_actions=sorted(set(actions)),
            should_notify_immediately=risk_level == RiskLevel.RED,
        )

    def _evaluate_attendance(self, student: Student):
        score = 0
        triggers: list[str] = []
        actions: list[str] = []

        if not student.attendance_records:
            return score, triggers, actions

        attendance_by_day = defaultdict(list)
        for record in student.attendance_records:
            attendance_by_day[record.date.weekday()].append(record)

        consecutive_absences = 0
        max_consecutive_absences = 0
        for record in sorted(student.attendance_records, key=lambda item: item.date):
            if not record.present:
                consecutive_absences += 1
                max_consecutive_absences = max(max_consecutive_absences, consecutive_absences)
            else:
                consecutive_absences = 0

        if max_consecutive_absences >= 3:
            score += 25
            triggers.append("Racha de inasistencias consecutivas de 3 o más días.")
            actions.append("Establecer seguimiento académico y familiar inmediato.")

        total_days = len(student.attendance_records)
        absent_days = sum(1 for record in student.attendance_records if not record.present)
        absence_percentage = (absent_days / total_days) * 100 if total_days else 0
        if absence_percentage >= 15:
            score += 20
            triggers.append("Porcentaje acumulado de inasistencias del 15% o más.")
            actions.append("Revisar la asistencia mensual y citar al acudiente.")

        day_recurrence = 0
        for records in attendance_by_day.values():
            if sum(1 for item in records if not item.present) >= 2:
                day_recurrence += 1
        if day_recurrence > 0:
            score += 10
            triggers.append("Reincidencia de inasistencias en días específicos del calendario.")
            actions.append("Diseñar plan de acompañamiento por días de mayor riesgo.")

        return score, triggers, actions

    def _evaluate_performance(self, student: Student):
        score = 0
        triggers: list[str] = []
        actions: list[str] = []

        if not student.grades:
            return score, triggers, actions

        failed_subjects = sum(1 for grade in student.grades if grade.value < 3.0)
        if failed_subjects >= 3:
            score += 25
            triggers.append("Tres o más materias con rendimiento bajo o reprobadas.")
            actions.append("Solicitar apoyo académico interdisciplinario para las materias en riesgo.")

        subject_periods: dict[str, dict[str, list[Grade]]] = defaultdict(lambda: defaultdict(list))
        for grade in student.grades:
            subject_periods[grade.subject][grade.period].append(grade)

        average_by_subject: dict[str, dict[str, float]] = {}
        for subject, periods in subject_periods.items():
            average_by_subject[subject] = {}
            for period, grades in periods.items():
                average_by_subject[subject][period] = sum(item.value for item in grades) / len(grades)

        if average_by_subject:
            period_values: list[float] = []
            for subject in average_by_subject:
                if len(average_by_subject[subject]) >= 2:
                    values = sorted(average_by_subject[subject].items())
                    previous = values[-2][1]
                    current = values[-1][1]
                    drop = previous - current
                    if drop > 0 and (drop / previous) >= 0.20:
                        period_values.append(drop)

            if period_values:
                score += 15
                triggers.append("Caída abrupta del promedio respecto al corte anterior.")
                actions.append("Activar intervención pedagógica para recuperar el rendimiento perdido.")

        return score, triggers, actions

    def _evaluate_observer_and_family(self, student: Student):
        score = 0
        triggers: list[str] = []
        actions: list[str] = []

        family_annotations = [
            record for record in student.observer_records if record.category == ObserverCategory.FAMILIAR
        ]
        if family_annotations:
            score += 25
            triggers.append("Se registraron anotaciones familiares o del entorno con impacto en el estudiante.")
            actions.append("Programar apoyo con orientación familiar y seguimiento del entorno escolar.")

        if student.warnings_this_month > 0:
            score += 15
            triggers.append("Se registraron llamados de atención durante el mes actual.")
            actions.append("Convocar revisión de conducta y acompañamiento disciplinario.")

        if student.absent_parent_meetings > 0:
            score += 10
            triggers.append("El acudiente ha faltado a citaciones o reuniones de seguimiento.")
            actions.append("Reprogramar la cita con el acudiente y reforzar la comunicación.")

        return score, triggers, actions

    def _risk_level_for(self, score: int) -> RiskLevel:
        if score >= 60:
            return RiskLevel.RED
        if score >= 35:
            return RiskLevel.YELLOW
        return RiskLevel.GREEN
