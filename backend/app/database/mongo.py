"""MongoDB client + index management.

Indexes (created once at startup):
- prediction_id (unique): point lookups of a single prediction record.
- created_at (descending): time-range listing of recent predictions for the
  history endpoint and future dashboard queries.
- risk_level: filtering predictions by LOW/MEDIUM/HIGH for operational review.
"""
from __future__ import annotations

import logging

log = logging.getLogger("fraud_api")


async def get_collection(mongo_uri: str, db_name: str, collection_name: str):
    """Return (collection, status). Never raises: on failure returns (None, reason)."""
    if not mongo_uri:
        return None, "disabled"
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        coll = client[db_name][collection_name]
        await coll.create_index("prediction_id", unique=True)
        await coll.create_index([("created_at", -1)])
        await coll.create_index("risk_level")
        return coll, "connected"
    except Exception as e:
        log.warning("mongodb unavailable, persistence degraded: %s", type(e).__name__)
        return None, "degraded"
