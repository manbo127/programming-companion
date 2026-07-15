"""间隔复习计划与到期提醒。"""
from datetime import datetime, timedelta, timezone

from companion.extensions import db
from companion.models import ReviewPlan
from companion.repositories.reminder_repository import ReminderRepository


class ReviewPlanService:
    INTERVAL_DAYS = (1, 3, 7, 14, 30)

    @classmethod
    def observe(cls, client_id: str, topic: str | None, *, had_error: bool, positive: bool) -> ReviewPlan | None:
        if not topic:
            return None
        now = datetime.now(timezone.utc)
        plan = (
            db.session.query(ReviewPlan)
            .filter_by(client_id=client_id, topic=topic)
            .first()
        )
        if plan is None:
            first_delay = 1 if had_error else 3
            plan = ReviewPlan(
                client_id=client_id,
                topic=topic,
                reason="error" if had_error else ("progress" if positive else "practice"),
                interval_index=0,
                next_review_at=now + timedelta(days=first_delay),
                status="active",
                created_at=now,
                updated_at=now,
            )
            db.session.add(plan)
        elif had_error:
            plan.reason = "error"
            plan.interval_index = 0
            proposed = now + timedelta(days=1)
            if cls._as_aware(plan.next_review_at) > proposed:
                plan.next_review_at = proposed
            plan.status = "active"
            plan.updated_at = now
        db.session.flush()
        return plan

    @classmethod
    def materialize_due(cls, client_id: str) -> list:
        now = datetime.now(timezone.utc)
        plans = (
            db.session.query(ReviewPlan)
            .filter_by(client_id=client_id, status="active")
            .filter(ReviewPlan.next_review_at <= now)
            .order_by(ReviewPlan.next_review_at.asc())
            .all()
        )
        created = []
        for plan in plans:
            cycle = plan.next_review_at.strftime("%Y%m%d")
            reminder = ReminderRepository.create_if_new(
                client_id=client_id,
                dedupe_key=f"review:{plan.id}:{plan.interval_index}:{cycle}",
                reminder_type="scheduled_review",
                content=f"到了复习“{plan.topic}”的时间。先回忆核心概念，再做一道小练习吧。",
            )
            if reminder:
                created.append(reminder)
        db.session.flush()
        return created

    @classmethod
    def complete(cls, plan: ReviewPlan) -> ReviewPlan:
        now = datetime.now(timezone.utc)
        plan.last_reviewed_at = now
        plan.interval_index = min(plan.interval_index + 1, len(cls.INTERVAL_DAYS) - 1)
        plan.next_review_at = now + timedelta(days=cls.INTERVAL_DAYS[plan.interval_index])
        plan.reason = "reviewed"
        plan.status = "active"
        plan.updated_at = now
        db.session.flush()
        return plan

    @staticmethod
    def list_active(client_id: str) -> list[ReviewPlan]:
        return (
            db.session.query(ReviewPlan)
            .filter_by(client_id=client_id, status="active")
            .order_by(ReviewPlan.next_review_at.asc())
            .all()
        )

    @staticmethod
    def get(client_id: str, plan_id: int) -> ReviewPlan | None:
        return db.session.query(ReviewPlan).filter_by(id=plan_id, client_id=client_id).first()

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
