import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.order_imports import OrderImportBatch
from app.models.user import User
from app.platform.service import apply_pagination_headers, paginate_statement
from app.schemas.order_imports import CommitReviewRequest, CommitReviewResult, ImportBatchRead, ImportBatchSummary
from app.services.order_import_parser import MAX_BYTES
from app.services.order_import_service import commit_review, create_review, get_review, revalidate_review

router = APIRouter(prefix='/order-imports')
import_actor = require_permission('integrations:import')


@router.post('', response_model=ImportBatchRead)
def review_file(response: Response, file: UploadFile = File(...),
    actor: User = Depends(import_actor), db: Session = Depends(get_db)):
    # Read one byte beyond the limit to reject oversize content without reading it all.
    content = file.file.read(MAX_BYTES + 1)
    batch, created = create_review(db, actor, file.filename or 'orders.csv', content)
    response.status_code = 201 if created else 200
    return batch


@router.get('', response_model=list[ImportBatchSummary])
def list_reviews(response: Response, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    actor: User = Depends(import_actor), db: Session = Depends(get_db)):
    statement = select(OrderImportBatch).where(OrderImportBatch.company_id == actor.company_id).order_by(
        OrderImportBatch.created_at.desc(), OrderImportBatch.id)
    batches, meta = paginate_statement(db, statement, page=page, page_size=page_size)
    apply_pagination_headers(response, meta)
    return batches


@router.get('/{batch_id}', response_model=ImportBatchRead)
def review_detail(batch_id: UUID, actor: User = Depends(import_actor), db: Session = Depends(get_db)):
    return get_review(db, actor, batch_id)


@router.post('/{batch_id}/revalidate', response_model=ImportBatchRead)
def revalidate(batch_id: UUID, actor: User = Depends(import_actor), db: Session = Depends(get_db)):
    return revalidate_review(db, actor, batch_id)


@router.post('/{batch_id}/commit', response_model=CommitReviewResult,
    dependencies=[Depends(require_permission('sales:write'))])
def commit(batch_id: UUID, payload: CommitReviewRequest,
    actor: User = Depends(import_actor), db: Session = Depends(get_db)):
    return commit_review(db, actor, batch_id, payload.entry_ids)


def _safe_cell(value):
    text = str(value)
    # Leading whitespace must not hide a formula from spreadsheet applications.
    if text.startswith(('\t', '\r')) or text.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + text
    return text


@router.get('/{batch_id}/errors.csv')
def export_errors(batch_id: UUID, actor: User = Depends(import_actor), db: Session = Depends(get_db)):
    batch = get_review(db, actor, batch_id)
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['external_order_id', 'row', 'field', 'code', 'message'])
    for external_id, issues in [('', batch.unassigned_errors)] + [(e.external_order_id, e.errors) for e in batch.entries]:
        for issue in issues:
            writer.writerow([_safe_cell(value) for value in (
                external_id, issue['row'], issue.get('field') or '', issue['code'], issue['message'])])
    return Response(output.getvalue(), media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="order-import-{batch.id}-errors.csv"'})
