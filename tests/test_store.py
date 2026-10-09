import asyncio
import copy

from backend import engine
from backend.store import Store

def test_redis_snapshot_and_ttl(monkeypatch):
    import fakeredis.aioredis
    monkeypatch.delenv("REDIS_URL",raising=False)
    store=Store();store.redis=fakeredis.aioredis.FakeRedis(decode_responses=True)
    async def run():
        room=engine.new_room("ABC234","Host")
        await store.save(room)
        saved=await store.load("ABC234")
        assert saved==room
        assert 86390 <= await store.redis.ttl("lastkey:room:ABC234") <= 86400
        saved["players"][0]["name"]="Changed"
        assert (await store.load("ABC234"))["players"][0]["name"]=="Host"
        await store.health();await store.delete("ABC234")
        assert await store.load("ABC234") is None
        await store.close()
    asyncio.run(run())

def test_production_requires_redis(monkeypatch):
    import pytest
    monkeypatch.setenv("APP_ENV","production");monkeypatch.delenv("REDIS_URL",raising=False)
    with pytest.raises(RuntimeError,match="REDIS_URL"):Store()
