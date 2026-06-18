from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.moderation import ModerationQueue


class ModerationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def claim_next(
        self, moderator_id: str, queue_priority: Optional[int] = None
    ) -> Optional[ModerationQueue]:
        """Atomically claim the next PENDING ticket using SELECT FOR UPDATE SKIP LOCKED."""
        filters = [ModerationQueue.status == "PENDING"]
        if queue_priority is not None:
            filters.append(ModerationQueue.queue_priority == queue_priority)

        # SELECT FOR UPDATE SKIP LOCKED — row-level lock, skip locked rows
        stmt = (
            update(ModerationQueue)
            .where(*filters)
            .order_by(
                ModerationQueue.queue_priority.asc(),
                ModerationQueue.date_updated.asc(),
            )
            .limit(1)
            .values(
                status="IN_REVIEW",
                moderator_id=moderator_id,
                date_updated=datetime.utcnow(),
            )
            .returning(ModerationQueue)
        )

        # PostgreSQL does not support UPDATE ... RETURNING with FOR UPDATE SKIP LOCKED
        # directly. Use a CTE approach: lock the row first, then update.
        from sqlalchemy import text

        result = await self.session.execute(
            text(
                """
                WITH locked AS (
                    SELECT id FROM moderation_queue
                    WHERE status = :status
                    AND (:priority IS NULL OR queue_priority = :priority)
                    ORDER BY queue_priority ASC, date_updated ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE moderation_queue
                SET status = 'IN_REVIEW', moderator_id = :moderator_id, date_updated = now()
                WHERE id = (SELECT id FROM locked)
                RETURNING *
                """
            ),
            {"status": "PENDING", "priority": queue_priority, "moderator_id": moderator_id},
        )

        row = result.mappings().first()
        if row is None:
            return None

        # Reload as ORM object
        ticket = await self.session.get(ModerationQueue, row["id"])
        return ticket

    async def get_ticket(self, product_id: str) -> Optional[ModerationQueue]:
        result = await self.session.execute(
            self.session.query(ModerationQueue)
            .filter(ModerationQueue.product_id == product_id)
            .statement
        )
        return result.scalars().first()

    async def upsert_ticket(self, card_data: dict) -> ModerationQueue:
        """Insert or update a moderation card in the DB."""
        existing = await self.session.execute(
            self.session.query(ModerationQueue)
            .filter(ModerationQueue.product_id == card_data["product_id"])
            .statement
        )
        ticket = existing.scalars().first()

        if ticket is None:
            ticket = ModerationQueue(
                product_id=card_data["product_id"],
                seller_id=card_data.get("seller_id"),
                status=card_data.get("status", "PENDING"),
                queue_priority=card_data.get("queue_priority", 1),
                json_before=card_data.get("json_before"),
                json_after=card_data.get("json_after"),
                blocking_reason_id=card_data.get("blocking_reason_id"),
                moderator_id=card_data.get("moderator_id"),
                moderator_comment=card_data.get("moderator_comment"),
                field_reports=card_data.get("field_reports", []),
                date_created=card_data.get("date_created", datetime.utcnow()),
                date_updated=card_data.get("date_updated", datetime.utcnow()),
                date_moderation=card_data.get("date_moderation"),
                blocking_history=card_data.get("blocking_history"),
            )
            self.session.add(ticket)
        else:
            for key in (
                "status", "queue_priority", "json_before", "json_after",
                "blocking_reason_id", "moderator_id", "moderator_comment",
                "field_reports", "date_updated", "date_moderation", "blocking_history",
            ):
                if key in card_data:
                    setattr(ticket, key, card_data[key])

        await self.session.flush()
        return ticket

    async def delete_ticket(self, product_id: str) -> None:
        existing = await self.session.execute(
            self.session.query(ModerationQueue)
            .filter(ModerationQueue.product_id == product_id)
            .statement
        )
        ticket = existing.scalars().first()
        if ticket:
            await self.session.delete(ticket)
            await self.session.flush()

    async def has_pending_or_review(self, product_id: str) -> bool:
        result = await self.session.execute(
            self.session.query(ModerationQueue)
            .filter(
                ModerationQueue.product_id == product_id,
                ModerationQueue.status.in_(["PENDING", "IN_REVIEW"]),
            )
            .statement
        )
        return result.scalars().first() is not None
