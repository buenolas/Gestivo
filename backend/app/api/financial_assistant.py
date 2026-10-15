from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_plan_feature
from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.user import User
from app.schemas.financial_assistant import FinancialAssistantRequest
from app.schemas.financial_assistant import FinancialAssistantResponse
from app.services.assistant_usage import AssistantDailyLimitError
from app.services.assistant_usage import AssistantPlanUnavailableError
from app.services.assistant_usage import consume_assistant_interaction
from app.services.assistant_usage import ensure_assistant_interaction_available
from app.services.financial_assistant import FinancialAssistantError
from app.services.financial_assistant import answer_financial_question

router = APIRouter(
    prefix="/assistant",
    tags=["assistant"],
    dependencies=[Depends(require_plan_feature("assistant"))],
)


@router.post("/chat", response_model=FinancialAssistantResponse)
def chat(
    request: FinancialAssistantRequest,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialAssistantResponse:
    try:
        ensure_assistant_interaction_available(db, current_user)
        answer = answer_financial_question(db, current_user, request.messages)
        consume_assistant_interaction(db, current_user)
    except AssistantDailyLimitError as error:
        raise HTTPException(
            status_code=429,
            detail=str(error),
        ) from error
    except AssistantPlanUnavailableError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error
    except FinancialAssistantError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message,
        ) from error
    return FinancialAssistantResponse(answer=answer)
