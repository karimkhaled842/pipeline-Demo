"""Item endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.app.api.v1.deps import CurrentUser, DbSession, Pagination
from src.app.core.logging import get_logger
from src.app.schemas.schemas import ItemCreate, ItemResponse, ItemUpdate, PaginatedResponse
from src.app.services import item_service

logger = get_logger(__name__)
router = APIRouter(prefix="/items", tags=["items"])


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="List items",
)
async def list_items(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    public_only: bool = False,
) -> PaginatedResponse:
    """List items owned by the current user (or all public items)."""
    owner_id = None if public_only else current_user.id
    items, total = await item_service.list_items(
        db,
        owner_id=owner_id,
        public_only=public_only,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=[ItemResponse.model_validate(i) for i in items],
    )


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
)
async def create_item(
    payload: ItemCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ItemResponse:
    """Create a new item owned by the authenticated user."""
    item = await item_service.create_item(db, payload, owner_id=current_user.id)
    return ItemResponse.model_validate(item)


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get an item by ID",
)
async def get_item(
    item_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ItemResponse:
    """Return a single item. Owner or superuser only (unless item is public)."""
    item = await item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not item.is_public and item.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return ItemResponse.model_validate(item)


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update an item",
)
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ItemResponse:
    """Update item fields. Owner or superuser only."""
    item = await item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    updated = await item_service.update_item(db, item, payload)
    return ItemResponse.model_validate(updated)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(
    item_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete an item. Owner or superuser only."""
    item = await item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    await item_service.delete_item(db, item)
