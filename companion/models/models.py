"""兼容导入入口，实际模型统一定义在 companion.models。"""
from companion.models import (
    Client,
    LearnerProfile,
    Conversation,
    Message,
    LearningEvent,
    Reminder,
)

__all__ = [
    "Client",
    "LearnerProfile",
    "Conversation",
    "Message",
    "LearningEvent",
    "Reminder",
]
