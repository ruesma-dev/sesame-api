# application/use_cases/task_from_attendance_use_cases.py
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sesame_connector.application.interfaces.task_port import TaskPort
from sesame_connector.application.use_cases.daily_attendance_use_cases import DailyAttendanceUseCases
from sesame_connector.domain.models.task import Task


class TaskFromAttendanceUseCases:
    """
    Caso de uso: a partir de la asistencia diaria, crear tareas
    para los empleados que:
      - tengan fichaje de TRABAJO CERRADO en la fecha dada
      - hayan cumplido (o superado) su horario ese día.

    La hora de inicio de la tarea será el `out_at` del último
    fichaje de trabajo cerrado.
    """

    def __init__(self, attendance_uc: DailyAttendanceUseCases, task_port: TaskPort) -> None:
        self._attendance_uc = attendance_uc
        self._task_port = task_port

    def create_tasks_for_date(self, *, date_str: Optional[str] = None) -> List[Task]:
        """
        Orquesta:
          1) Calcula el resumen diario de asistencia.
          2) Filtra los empleados con fichaje cerrado que hayan cumplido horario.
          3) Crea una tarea por cada uno a través de TaskPort.

        Devuelve la lista de tareas creadas.
        """
        if not date_str:
            date_str = date.today().isoformat()

        summary = self._attendance_uc.build_status_for_date(date_str=date_str)

        tasks_to_create: List[Task] = []

        for row in summary.closed_entries:
            # Sólo nos interesan los que han cumplido horario
            if not row.met_schedule:
                continue

            # Por seguridad: si por algún motivo no hubiera out_at, ignoramos
            if row.out_at is None:
                continue

            description = (
                f"Tarea auto-generada tras cumplir su horario el {summary.date} "
                f"(trabajadas={row.hours_worked}h, objetivo={row.hours_to_work or '-'}h)"
            )

            task = Task(
                employee_id=row.employee_id,
                start_at=row.out_at,
                description=description,
                source="sesame_daily_attendance",
                metadata={
                    "employee_name": row.employee_name,
                    "employee_email": row.email,
                    "date": summary.date,
                    "seconds_worked": row.seconds_worked,
                    "seconds_to_work": row.seconds_to_work,
                    "seconds_diff": row.seconds_diff,
                },
            )
            tasks_to_create.append(task)

        if not tasks_to_create:
            return []

        # Aquí delegamos en infraestructura (BC, BBDD, etc.)
        created = self._task_port.bulk_create_tasks(tasks_to_create)
        return created

