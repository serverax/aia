"""Async Redis Streams helpers.

Agents communicate via Redis Streams using consumer groups so messages are
delivered at-least-once and pods can be horizontally scaled. This module
hides the consumer-group bookkeeping (create-if-missing, XACK on success)
and exposes a simple `consume()` async iterator.
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass

import redis.asyncio as aioredis
from redis.exceptions import ResponseError

logger = logging.getLogger(__name__)


@dataclass
class StreamMessage:
    """A single message read from a stream."""

    stream: str
    message_id: str
    fields: dict[str, str]


def build_client(
    host: str | None = None,
    port: int | None = None,
    password: str | None = None,
) -> aioredis.Redis:
    """Build an async Redis client from explicit args or env vars."""
    return aioredis.Redis(
        host=host or os.environ.get("REDIS_HOST", "localhost"),
        port=port or int(os.environ.get("REDIS_PORT", "6379")),
        password=password or os.environ.get("REDIS_PASSWORD") or None,
        decode_responses=True,
    )


async def ensure_group(
    client: aioredis.Redis,
    stream: str,
    group: str,
    start_id: str = "0",
) -> None:
    """Create the consumer group if it doesn't exist. No-op otherwise.

    `start_id="0"` reads from the beginning of the stream, `"$"` reads only
    new messages. Use `"$"` in production to avoid replaying history.
    """
    try:
        await client.xgroup_create(stream, group, id=start_id, mkstream=True)
        logger.info("Created consumer group %s on stream %s", group, stream)
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            return  # Group already exists - fine
        raise


async def consume(
    client: aioredis.Redis,
    stream: str,
    group: str,
    consumer: str,
    block_ms: int = 5000,
    count: int = 10,
) -> AsyncIterator[StreamMessage]:
    """Yield messages from a stream until cancelled.

    The caller is responsible for `ack(client, stream, group, msg_id)` after
    successful processing. Unacked messages remain in the Pending Entries
    List and will be re-delivered to another consumer after a claim.
    """
    await ensure_group(client, stream, group)

    while True:
        response = await client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )
        if not response:
            continue

        for stream_name, entries in response:
            for message_id, fields in entries:
                yield StreamMessage(stream=stream_name, message_id=message_id, fields=fields)


async def ack(
    client: aioredis.Redis,
    stream: str,
    group: str,
    message_id: str,
) -> None:
    """Acknowledge successful processing of a message."""
    await client.xack(stream, group, message_id)


async def publish(
    client: aioredis.Redis,
    stream: str,
    fields: dict[str, str],
    maxlen: int | None = 10000,
) -> str:
    """Append a message to a stream. Returns the assigned message ID.

    `maxlen` caps stream size (approximate) so unconsumed streams can't grow
    unbounded. Set to None to disable trimming.
    """
    return await client.xadd(stream, fields, maxlen=maxlen, approximate=True)
