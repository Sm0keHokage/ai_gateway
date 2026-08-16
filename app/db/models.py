import uuid
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from app.db.column_annotations import uuid_pk, int_pk, created_at, str_255


class ApiKey(Base):
    __tablename__ = "api_key"

    id: Mapped[uuid_pk]
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str_255]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[created_at]

    logs: Mapped[list["RequestLog"]] = relationship("RequestLog", back_populates="api_key")


class RequestLog(Base):
    __tablename__ = "request_log"

    id: Mapped[int_pk]
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("api_key.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[created_at]

    api_key: Mapped[Optional["ApiKey"]] = relationship("ApiKey", back_populates="logs")
