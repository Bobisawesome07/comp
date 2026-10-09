import json
import os

from redis.asyncio import Redis

class Store:
    def __init__(self):
        url = os.getenv("REDIS_URL")
        if os.getenv("APP_ENV") == "production" and not url:
            raise RuntimeError("Production requires REDIS_URL for room recovery.")
        self.redis = Redis.from_url(url, decode_responses=True) if url else None
        self.memory = {}

    async def load(self, code):
        raw = await self.redis.get("lastkey:room:"+code) if self.redis else self.memory.get(code)
        return json.loads(raw) if raw else None

    async def save(self, room):
        from .engine import now
        room["saved_at"] = now()
        raw = json.dumps(room)
        if self.redis: await self.redis.set("lastkey:room:"+room["code"], raw, ex=86400)
        else: self.memory[room["code"]] = raw

    async def delete(self, code):
        if self.redis: await self.redis.delete("lastkey:room:"+code)
        else: self.memory.pop(code, None)

    async def health(self):
        if self.redis: await self.redis.ping()

    async def close(self):
        if self.redis: await self.redis.aclose()
