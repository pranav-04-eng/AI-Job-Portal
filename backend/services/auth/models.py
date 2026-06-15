from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from common.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="candidate")  # candidate | recruiter
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
