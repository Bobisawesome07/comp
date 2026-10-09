import asyncio
import contextlib
import logging
import os
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import engine
from .math_service import SUBJECTS
from .store import Store

log = logging.getLogger("lastkey")
rooms, locks, sockets = {}, defaultdict(asyncio.Lock), defaultdict(dict)
limits = defaultdict(deque)
store = Store()

def rate_limit(ip):
    q = limits[ip]
    while q and q[0] < time.time()-60: q.popleft()
    if len(q) >= 30: raise HTTPException(429, "Too many requests. Try again in a minute.")
    q.append(time.time())

async def get_room(code):
    code = code.upper()
    if not re.fullmatch(r"[A-Z2-9]{6}", code): raise HTTPException(404, "Room not found. Check your six-character code.")
    if code not in rooms:
        saved = await store.load(code)
        if not saved: raise HTTPException(404, "Room not found or expired.")
        rooms[code] = engine.restore(saved)
    return rooms[code]

async def broadcast(room):
    pairs = list(sockets[room["code"]].items())
    async def send(pid, ws):
        try: await asyncio.wait_for(ws.send_json({"type":"state", "state":engine.snapshot(room,pid)}), 2)
        except (RuntimeError, WebSocketDisconnect, TimeoutError): pass
    await asyncio.gather(*(send(pid,ws) for pid,ws in pairs))

async def maintenance():
    while True:
        await asyncio.sleep(1)
        for code in list(rooms):
            try:
                async with locks[code]:
                    room = rooms.get(code)
                    if not room: continue
                    for p in room["players"]:
                        if p["online"] and engine.now()-p["last_seen"] > 45:
                            ws = sockets[code].pop(p["id"], None)
                            if ws:
                                with contextlib.suppress(Exception): await ws.close(code=1001)
                            engine.disconnect(room,p)
                    engine.tick(room)
                    if not any(p["online"] for p in room["players"]) and engine.now()-room["updated"] > 86400:
                        await store.delete(code)
                        rooms.pop(code,None); sockets.pop(code,None)
                        continue
                    if any(p["online"] for p in room["players"]):
                        await store.save(room)
                    await broadcast(room)
            except Exception:
                log.exception("Room maintenance failed")
        for ip in list(limits):
            if not limits[ip] or limits[ip][-1] < time.time()-60: limits.pop(ip,None)

@asynccontextmanager
async def lifespan(app):
    await store.health()
    task = asyncio.create_task(maintenance())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError): await task
    for room in rooms.values():
        engine.stop_clock(room)
        for p in room["players"]: p["online"] = False
        await store.save(room)
    await store.close()

app = FastAPI(title="The Last Key", lifespan=lifespan)

class Join(BaseModel):
    name: str = Field(min_length=1,max_length=24)

@app.get("/api/health")
async def health():
    try: await store.health()
    except Exception: raise HTTPException(503,"Room storage unavailable")
    return {"status":"ok", "storage":"redis" if store.redis else "memory (development)"}

@app.get("/api/subjects")
async def subjects():
    return [{"id":key,"label":value} for key,value in SUBJECTS.items()]

@app.post("/api/rooms")
async def create(body:Join, request:Request):
    rate_limit(request.client.host)
    async with locks["__create__"]:
        for _ in range(20):
            code = ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
            if code not in rooms and not await store.load(code): break
        else: raise HTTPException(503,"Please try creating a room again.")
        try: room = engine.new_room(code,body.name)
        except engine.GameError as exc: raise HTTPException(400,str(exc))
        await store.save(room)
        rooms[code] = room
        p = room["players"][0]
        return {"code":code,"player_id":p["id"],"token":p["token"]}

@app.post("/api/rooms/{code}/join")
async def join(code:str, body:Join, request:Request):
    rate_limit(request.client.host)
    code = code.upper()
    async with locks[code]:
        room = await get_room(code)
        if room["status"] != "lobby": raise HTTPException(409,"This game has started. Rejoin from your original device.")
        if len(room["players"]) >= 8: raise HTTPException(409,"This room is full (8 players).")
        try: p = engine.new_player(body.name)
        except engine.GameError as exc: raise HTTPException(400,str(exc))
        if any(existing["name"].casefold() == p["name"].casefold() for existing in room["players"]):
            raise HTTPException(409,"That name is already in use. Choose another.")
        room["players"].append(p)
        for existing in room["players"]: existing["ready"] = False
        room["updated"] = engine.now()
        await store.save(room)
        await broadcast(room)
        return {"code":code,"player_id":p["id"],"token":p["token"]}

@app.websocket("/ws/{code}")
async def websocket(ws:WebSocket, code:str):
    code = code.upper()
    try:
        rate_limit(ws.client.host)
    except HTTPException:
        await ws.close(code=1008)
        return
    origin = ws.headers.get("origin")
    allowed = os.getenv("PUBLIC_ORIGIN")
    expected_origin = f"https://{ws.headers.get('host')}" if os.getenv("APP_ENV") == "production" else None
    if origin and (allowed or expected_origin) and origin != (allowed or expected_origin):
        await ws.close(code=1008); return
    await ws.accept()
    player, room = None, None
    try:
        hello = await asyncio.wait_for(ws.receive_json(),10)
        if not isinstance(hello,dict): await ws.close(code=1008); return
        async with locks[code]:
            room = await get_room(code)
            token = hello.get("token","")
            if not isinstance(token,str): await ws.close(code=1008); return
            player = next((p for p in room["players"] if secrets.compare_digest(p["token"],token)),None)
            if not player: await ws.close(code=1008); return
            old = sockets[code].get(player["id"])
            if old:
                with contextlib.suppress(Exception): await old.close(code=4001,reason="Connected from another tab")
            sockets[code][player["id"]] = ws
            engine.connect(room,player)
            await store.save(room)
            await broadcast(room)
        recent = deque()
        while True:
            raw = await ws.receive_text()
            if len(raw) > 4096: await ws.close(code=1009); return
            import json
            try: message = json.loads(raw)
            except ValueError:
                await ws.send_json({"type":"error","message":"Invalid message."}); continue
            if not isinstance(message,dict): continue
            while recent and recent[0] < time.time()-10: recent.popleft()
            if len(recent) >= 40:
                await ws.send_json({"type":"error","message":"Too many actions. Slow down."}); continue
            recent.append(time.time())
            async with locks[code]:
                if sockets[code].get(player["id"]) is not ws: return
                player["last_seen"] = engine.now()
                try:
                    await asyncio.to_thread(engine.action,room,player,message)
                except engine.GameError as exc:
                    await ws.send_json({"type":"error","message":str(exc),"request_id":message.get("request_id")})
                else:
                    if message.get("type") != "ping":
                        await store.save(room)
                        await ws.send_json({"type":"ack","request_id":message.get("request_id")})
                await broadcast(room)
    except (TimeoutError, HTTPException, ValueError):
        with contextlib.suppress(Exception): await ws.close(code=1008)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket failure")
        with contextlib.suppress(Exception): await ws.close(code=1011)
    finally:
        if player and room:
            async with locks[code]:
                if sockets[code].get(player["id"]) is ws:
                    sockets[code].pop(player["id"],None)
                    engine.disconnect(room,player)
                    await store.save(room)
                    await broadcast(room)

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets",StaticFiles(directory=DIST/"assets"),name="assets")
    @app.get("/{path:path}")
    async def index(path:str):
        if path.startswith(("api/","ws/")): raise HTTPException(404)
        return FileResponse(DIST/"index.html")
