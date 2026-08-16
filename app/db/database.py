from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr
from app.settings import settings

engine = create_async_engine(
    settings.DATABASE.async_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

session_local = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @classmethod
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


async def get_db():
    async with session_local() as session:
        yield session


async def get_db_write():
    async with session_local.begin() as session:
        yield session


def get_session_maker() -> async_sessionmaker:
    return session_local
