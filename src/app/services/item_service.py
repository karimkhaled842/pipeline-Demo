"""Item CRUD service layer."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.logging import get_logger
from src.app.models.models import Item
from src.app.schemas.schemas import ItemCreate, ItemUpdate

logger = get_logger(__name__)


async def get_item(db: AsyncSession, item_id: int) -> Item | None:
    """Fetch a single item by ID."""
    result = await db.execute(select(Item).options(selectinload(Item.owner)).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def list_items(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID | None = None,
    public_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Item], int]:
    """Return a paginated list of items, optionally filtered."""
    query = select(Item).options(selectinload(Item.owner))
    count_query = select(func.count()).select_from(Item)

    if owner_id:
        query = query.where(Item.owner_id == owner_id)
        count_query = count_query.where(Item.owner_id == owner_id)

    if public_only:
        query = query.where(Item.is_public == True)  # noqa: E712
        count_query = count_query.where(Item.is_public == True)  # noqa: E712

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.offset(skip).limit(limit))
    items = list(result.scalars().all())
    return items, total


async def create_item(db: AsyncSession, payload: ItemCreate, owner_id: uuid.UUID) -> Item:
    """Create and persist a new item."""
    item = Item(
        title=payload.title,
        description=payload.description,
        is_public=payload.is_public,
        owner_id=owner_id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    logger.info("item_created", item_id=item.id, owner_id=str(owner_id))
    return item


async def update_item(db: AsyncSession, item: Item, payload: ItemUpdate) -> Item:
    """Apply partial updates to an item."""
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.flush()
    await db.refresh(item)
    logger.info("item_updated", item_id=item.id)
    return item


async def delete_item(db: AsyncSession, item: Item) -> None:
    """Hard-delete an item."""
    await db.delete(item)
    await db.flush()
    logger.info("item_deleted", item_id=item.id)
