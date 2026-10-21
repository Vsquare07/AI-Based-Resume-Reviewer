from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_hash = Column(String(64), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    candidate_name = Column(String(255), nullable=True, default="Candidate")
    job_title = Column(String(255), index=True, nullable=False)
    result_json = Column(Text, nullable=False)
    score = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("file_hash", "job_title", name="uq_file_hash_job_title"),
    )
