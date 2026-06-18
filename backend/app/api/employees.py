from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.employee import Employee
from app.models.financial_transaction import FinancialTransaction
from app.models.user import User
from app.schemas.employee import EmployeeCreate
from app.schemas.employee import EmployeeOptionResponse
from app.schemas.employee import EmployeeResponse
from app.schemas.employee import EmployeeUpdate
from app.schemas.employee import SalaryExpenseGenerationCreate
from app.schemas.employee import SalaryExpenseGenerationResponse
from app.services.employees import EmployeeValidationError
from app.services.employees import create_employee
from app.services.employees import get_employee
from app.services.employees import list_employees
from app.services.employees import update_employee
from app.services.payroll import generate_monthly_salary_expenses

router = APIRouter(prefix="/employees", tags=["employees"])


def _get_user_employee_or_404(
    db: Session,
    current_user: User,
    employee_id: UUID,
) -> Employee:
    employee = get_employee(db, current_user, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionario nao encontrado",
        )
    return employee


def _raise_validation_error(error: EmployeeValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get("", response_model=list[EmployeeResponse])
def list_user_employees(
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> list[Employee]:
    return list_employees(db, current_user)


@router.get("/options", response_model=list[EmployeeOptionResponse])
def list_employee_options(
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[Employee]:
    return list_employees(db, current_user)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_user_employee(
    employee_in: EmployeeCreate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> Employee:
    return create_employee(db, current_user, employee_in)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_user_employee(
    employee_id: UUID,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> Employee:
    return _get_user_employee_or_404(db, current_user, employee_id)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_user_employee(
    employee_id: UUID,
    employee_in: EmployeeUpdate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> Employee:
    employee = _get_user_employee_or_404(db, current_user, employee_id)
    try:
        return update_employee(db, employee, employee_in)
    except EmployeeValidationError as error:
        _raise_validation_error(error)


@router.post(
    "/salary-expenses/generate",
    response_model=SalaryExpenseGenerationResponse,
)
def generate_user_salary_expenses(
    generation_in: SalaryExpenseGenerationCreate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> SalaryExpenseGenerationResponse:
    transactions, skipped_count = generate_monthly_salary_expenses(
        db=db,
        user=current_user,
        reference_month=generation_in.reference_month,
        due_date=generation_in.due_date,
    )
    reference_month = generation_in.reference_month.replace(day=1)
    return SalaryExpenseGenerationResponse(
        reference_month=reference_month,
        created_count=len(transactions),
        skipped_count=skipped_count,
        transactions=transactions,
    )
