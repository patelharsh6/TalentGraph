"""ID and hashing helpers."""

import hashlib
from uuid import UUID, uuid4


def new_id() -> UUID:
    return uuid4()


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
