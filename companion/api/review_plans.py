"""间隔复习计划 API。"""
from flask import Blueprint

from companion.api.bootstrap import _get_or_create_client
from companion.api.errors import api_error, api_success
from companion.extensions import db
from companion.services.review_plan import ReviewPlanService


bp = Blueprint("review_plans", __name__, url_prefix="/api/v1")


def _serialize(plan):
    return {
        "id": plan.id,
        "topic": plan.topic,
        "reason": plan.reason,
        "interval_index": plan.interval_index,
        "next_review_at": plan.next_review_at.isoformat() if plan.next_review_at else None,
        "last_reviewed_at": plan.last_reviewed_at.isoformat() if plan.last_reviewed_at else None,
        "status": plan.status,
    }


@bp.route("/review-plans", methods=["GET"])
def list_review_plans():
    client = _get_or_create_client()
    ReviewPlanService.materialize_due(client.id)
    db.session.commit()
    return api_success([_serialize(plan) for plan in ReviewPlanService.list_active(client.id)])


@bp.route("/review-plans/<int:plan_id>/complete", methods=["POST"])
def complete_review(plan_id: int):
    client = _get_or_create_client()
    plan = ReviewPlanService.get(client.id, plan_id)
    if plan is None:
        return api_error("NOT_FOUND", "复习计划不存在", 404)
    ReviewPlanService.complete(plan)
    db.session.commit()
    return api_success(_serialize(plan))
