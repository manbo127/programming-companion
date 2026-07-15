"""学习事件聚合、知识点掌握度和趋势计算。"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json

from companion.repositories.learning_repository import LearningRepository


class LearningAnalyticsService:
    """将原始学习事件转为可解释的学习画像。"""

    @classmethod
    def overview(cls, client_id: str, *, days: int = 30) -> dict:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)
        events = LearningRepository.events_since(client_id, since, limit=500)

        error_types = Counter(e.error_type for e in events if e.error_type)
        languages = Counter(e.language for e in events if e.language and e.language != "unknown")
        topics = defaultdict(lambda: {"attempts": 0, "errors": 0, "positive": 0})
        scenes = Counter()
        emotions = Counter()

        for event in events:
            if event.topic:
                stats = topics[event.topic]
                stats["attempts"] += 1
                if event.error_type:
                    stats["errors"] += 1
                if event.event_type == "positive_progress":
                    stats["positive"] += 1
            try:
                metadata = json.loads(event.metadata_json or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
            if metadata.get("scene"):
                scenes[metadata["scene"]] += 1
            if metadata.get("emotion") and metadata["emotion"] != "neutral":
                emotions[metadata["emotion"]] += 1

        topic_progress = []
        for topic, stats in topics.items():
            score = cls._mastery_score(**stats)
            topic_progress.append({"topic": topic, **stats, "mastery_score": score})
        topic_progress.sort(key=lambda item: (-item["attempts"], item["mastery_score"], item["topic"]))

        active_days = len({event.created_at.date() for event in events if event.created_at})
        recent_cutoff = now - timedelta(days=7)
        previous_cutoff = now - timedelta(days=14)
        recent_errors = sum(1 for e in events if e.error_type and cls._as_aware(e.created_at) >= recent_cutoff)
        previous_errors = sum(
            1 for e in events
            if e.error_type and previous_cutoff <= cls._as_aware(e.created_at) < recent_cutoff
        )

        return {
            "window_days": days,
            "total_events": len(events),
            "active_days": active_days,
            "top_error_types": error_types.most_common(5),
            "recent_topics": [item["topic"] for item in topic_progress[:5]],
            "languages_used": [language for language, _ in languages.most_common()],
            "language_distribution": languages.most_common(),
            "scene_distribution": scenes.most_common(),
            "emotion_distribution": emotions.most_common(),
            "topic_progress": topic_progress[:8],
            "trend": {
                "recent_errors": recent_errors,
                "previous_errors": previous_errors,
                "direction": cls._trend_direction(recent_errors, previous_errors),
            },
        }

    @staticmethod
    def _mastery_score(*, attempts: int, errors: int, positive: int) -> int:
        score = 45 + min(attempts, 10) * 4 + positive * 8 - errors * 7
        return max(0, min(score, 100))

    @staticmethod
    def _trend_direction(recent: int, previous: int) -> str:
        if recent < previous:
            return "improving"
        if recent > previous:
            return "needs_attention"
        return "stable"

    @staticmethod
    def _as_aware(value: datetime | None) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
