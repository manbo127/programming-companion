"""
学习者画像 Repository
"""
from typing import Optional
from datetime import datetime, timezone
from companion.extensions import db
from companion.models import Client, LearnerProfile


class ProfileRepository:
    """学习者画像存储操作。"""

    @staticmethod
    def get_or_create_client(client_id: str) -> Client:
        client = db.session.get(Client, client_id)
        if client is None:
            client = Client(id=client_id)
            db.session.add(client)
            db.session.flush()
        client.last_seen_at = datetime.now(timezone.utc)
        return client

    @staticmethod
    def get_profile(client_id: str) -> Optional[LearnerProfile]:
        return db.session.get(LearnerProfile, client_id)

    @staticmethod
    def get_or_create_profile(client_id: str) -> LearnerProfile:
        profile = db.session.get(LearnerProfile, client_id)
        if profile is None:
            profile = LearnerProfile(client_id=client_id)
            db.session.add(profile)
            db.session.flush()
        return profile

    @staticmethod
    def update_profile(profile: LearnerProfile, **kwargs) -> LearnerProfile:
        for k, v in kwargs.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        profile.updated_at = datetime.now(timezone.utc)
        db.session.flush()
        return profile
