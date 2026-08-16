"""
CLI для управления API-ключами (хранятся в PostgreSQL как SHA-256 хэш).

Использование:
    python -m scripts.manage_keys create --name "client-a" [--rate-limit 5]
    python -m scripts.manage_keys list
    python -m scripts.manage_keys revoke <key_id>
"""

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import session_local  # noqa: E402
from app.db.repositories import ApiKeyRepository  # noqa: E402
from app.security import hash_key  # noqa: E402


async def create_key(name: str, rate_limit: int | None):
    raw_key = secrets.token_urlsafe(32)
    async with session_local.begin() as session:
        api_key = await ApiKeyRepository.create(
            session,
            key_hash=hash_key(raw_key),
            key_prefix=raw_key[:8],
            name=name,
            rate_limit_per_minute=rate_limit,
        )
        print(f"Created key id={api_key.id} name={api_key.name}")
        print(f"API key (shown once, store it securely): {raw_key}")


async def list_keys():
    async with session_local() as session:
        keys = await ApiKeyRepository.get_all(session)
        for k in keys:
            status = "active" if k.is_active else "revoked"
            limit = k.rate_limit_per_minute or "default"
            print(f"{k.id}  {k.key_prefix}...  {k.name}  [{status}]  limit={limit}/min")


async def revoke_key(key_id: str):
    import uuid

    async with session_local.begin() as session:
        api_key = await ApiKeyRepository.set_active(session, uuid.UUID(key_id), False)
        if api_key:
            print(f"Revoked key {api_key.id}")
        else:
            print("Key not found")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create")
    create_p.add_argument("--name", required=True)
    create_p.add_argument("--rate-limit", type=int, default=None)

    sub.add_parser("list")

    revoke_p = sub.add_parser("revoke")
    revoke_p.add_argument("key_id")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(create_key(args.name, args.rate_limit))
    elif args.command == "list":
        asyncio.run(list_keys())
    elif args.command == "revoke":
        asyncio.run(revoke_key(args.key_id))


if __name__ == "__main__":
    main()
