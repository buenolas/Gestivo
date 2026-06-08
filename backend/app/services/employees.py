import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate
from app.schemas.employee import EmployeeUpdate


class EmployeeValidationError(ValueError):
    pass


def list_employees(db: Session, user: User) -> list[Employee]:
    return list(
        db.scalars(
            select(Employee)
            .where(Employee.company_id == user.company_id)
            .order_by(Employee.name)
        )
    )


def get_employee(
    db: Session,
    user: User,
    employee_id: uuid.UUID,
) -> Employee | None:
    return db.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == user.company_id,
        )
    )


def create_employee(
    db: Session,
    user: User,
    employee_in: EmployeeCreate,
) -> Employee:
    employee = Employee(
        company_id=user.company_id,
        name=employee_in.name.strip(),
        position=_strip_optional_text(employee_in.position),
        salary_amount=employee_in.salary_amount,
        contract_start_date=employee_in.contract_start_date,
        contract_end_date=employee_in.contract_end_date,
        status=employee_in.status,
        notes=_strip_optional_text(employee_in.notes),
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(
    db: Session,
    employee: Employee,
    employee_in: EmployeeUpdate,
) -> Employee:
    next_start = employee_in.contract_start_date or employee.contract_start_date
    next_end = (
        employee_in.contract_end_date
        if "contract_end_date" in employee_in.model_fields_set
        else employee.contract_end_date
    )
    if next_end is not None and next_end < next_start:
        raise EmployeeValidationError("A data final do contrato deve ser posterior ao inicio")

    if employee_in.name is not None:
        employee.name = employee_in.name.strip()
    if "position" in employee_in.model_fields_set:
        employee.position = _strip_optional_text(employee_in.position)
    if employee_in.salary_amount is not None:
        employee.salary_amount = employee_in.salary_amount
    if employee_in.contract_start_date is not None:
        employee.contract_start_date = employee_in.contract_start_date
    if "contract_end_date" in employee_in.model_fields_set:
        employee.contract_end_date = employee_in.contract_end_date
    if employee_in.status is not None:
        employee.status = employee_in.status
    if "notes" in employee_in.model_fields_set:
        employee.notes = _strip_optional_text(employee_in.notes)

    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
