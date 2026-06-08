from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import Response
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.import_batch import ImportBatch
from app.models.user import User
from app.schemas.import_batch import ImportColumnMapping
from app.schemas.import_batch import ImportBatchResponse
from app.schemas.import_batch import ImportConfirmationResponse
from app.schemas.import_batch import ImportValidationResponse
from app.services.import_batch import ImportBatchValidationError
from app.services.import_batch import CSV_TEMPLATE_FILENAME
from app.services.import_batch import build_import_template_csv
from app.services.import_batch import confirm_import_batch
from app.services.import_batch import create_import_batch
from app.services.import_batch import get_import_batch
from app.services.import_batch import validate_import_batch

router = APIRouter(prefix="/imports/financial-transactions", tags=["imports"])


def _raise_validation_error(error: ImportBatchValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


def _get_user_import_batch_or_404(
    db: Session,
    current_user: User,
    batch_id: UUID,
) -> ImportBatch:
    batch = get_import_batch(db, current_user, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lote de importacao nao encontrado",
        )
    return batch


@router.get("/template.csv")
def download_import_template_csv(
    current_user: User = Depends(require_valid_subscription),
) -> Response:
    del current_user
    return Response(
        content=build_import_template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{CSV_TEMPLATE_FILENAME}"',
        },
    )


@router.post(
    "/upload",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_import_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> ImportBatch:
    content = await file.read()
    try:
        return create_import_batch(
            db=db,
            user=current_user,
            filename=file.filename or "import",
            content=content,
        )
    except ImportBatchValidationError as error:
        _raise_validation_error(error)


@router.get("/{batch_id}", response_model=ImportBatchResponse)
def get_user_import_batch(
    batch_id: UUID,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> ImportBatch:
    return _get_user_import_batch_or_404(db, current_user, batch_id)


@router.post("/{batch_id}/validate", response_model=ImportValidationResponse)
def validate_user_import_batch(
    batch_id: UUID,
    mapping: ImportColumnMapping,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> ImportBatch:
    batch = _get_user_import_batch_or_404(db, current_user, batch_id)
    try:
        return validate_import_batch(db, current_user, batch, mapping)
    except ImportBatchValidationError as error:
        _raise_validation_error(error)


@router.post("/{batch_id}/confirm", response_model=ImportConfirmationResponse)
def confirm_user_import_batch(
    batch_id: UUID,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> ImportConfirmationResponse:
    batch = _get_user_import_batch_or_404(db, current_user, batch_id)
    try:
        confirmed_batch, created_transaction_ids = confirm_import_batch(
            db,
            current_user,
            batch,
        )
    except ImportBatchValidationError as error:
        _raise_validation_error(error)
    return ImportConfirmationResponse(
        batch=confirmed_batch,
        created_transaction_ids=created_transaction_ids,
    )
