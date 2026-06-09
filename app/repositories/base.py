from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, record_id: int) -> ModelType | None:
        return await self.session.get(self.model, record_id)

    async def get_by(self, **kwargs: Any) -> ModelType | None:
        stmt = select(self.model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters: Any,
    ) -> list[ModelType]:
        stmt = select(self.model).filter_by(**filters).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **data: Any) -> ModelType:
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **data: Any) -> ModelType:
        for key, value in data.items():
            setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self, **filters: Any) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()
