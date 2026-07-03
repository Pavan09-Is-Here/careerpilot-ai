from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id, get_settings
from app.core.database import get_db
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCategory,
    NotificationDeliverResponse,
    NotificationPageResponse,
    NotificationResponse,
    NotificationStatus,
)
from app.services.notification import (
    NotificationServiceError,
    deliver_pending,
    get_notification_or_404,
    list_notifications,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("", response_model=NotificationPageResponse)
def list_notification_records(
    category: NotificationCategory | None = Query(default=None),
    status: NotificationStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    return list_notifications(
        database,
        candidate_profile_id=profile_id,
        category=category,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/deliver", response_model=NotificationDeliverResponse)
def deliver_pending_notifications(
    database: Session = Depends(get_db),
    _profile_id: int = Depends(get_current_profile_id),
) -> dict[str, int]:
    return deliver_pending(database, get_settings())


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Notification:
    try:
        return get_notification_or_404(notification_id, database, profile_id)
    except NotificationServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc
