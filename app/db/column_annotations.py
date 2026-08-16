import uuid
from datetime import datetime
from typing import Annotated
from sqlalchemy import func, String, DateTime, Uuid
from sqlalchemy.orm import mapped_column

int_pk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
uuid_pk = Annotated[
    uuid.UUID, mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
]
created_at = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
updated_at = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
]
str_255 = Annotated[str, mapped_column(String(255))]
