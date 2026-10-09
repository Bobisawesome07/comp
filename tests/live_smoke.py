"""End-to-end smoke test against a running local or deployed game.

Run: .venv/bin/python tests/live_smoke.py https://your-game.onrender.com
Creates disposable rooms and solves from public questions/private player clues.
"""
import asyncio
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from contextlib import AsyncExitStack
from pathlib import Path

import httpx
import websockets

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.math_service import parse_expression

async def state(ws,predicate=lambda s:True):
    for _ in range(200):
        packet=json.loads(await asyncio.wait_for(ws.recv(),30))
        if packet["type"]=="error":raise AssertionError(packet["message"])
        if packet["type"]=="state" and predicate(packet["state"]):return packet["state"]
    raise AssertionError("No matching state")

async def send(ws,kind,**extra):
    await ws.send(json.dumps({"type":kind,"request_id":uuid.uuid4().hex,**extra}))

def mansion_answer(states):
    q=states[0]["current"]
    clues=' '.join(clue for s in states for clue in s["current"]["clues"])
    if q["title"]=="The brass crest":
        order=re.search(r"left to right: (.+?)\.",clues)[1].split(' → ')
        mapping=dict(re.findall(r"(moon|owl|rose|star) = (\d)",clues))
        return ''.join(mapping[v] for v in order)
    if q["title"]=="The silent clock":
        hour=int(re.search(r"hour hand rested on (\d+)",clues)[1])
        minute=int(re.search(r"(\d+) marks clockwise",clues)[1])*5
        return f"{hour:02}:{minute:02}"
    if q["title"]=="The indexed shelf":
        words=re.search(r"page reads: '([^']+)'",clues)[1].split()
        return words[int(re.search(r"Take word (\d)",clues)[1])-1]
    if q["title"]=="The sealed letter":
        word=re.search(r"password: ([A-Z]+)",clues)[1].lower()
        shift=int(re.search(r"FORWARD (\d)",clues)[1])
        return ''.join(chr((ord(c)-97-shift)%26+97) for c in word)
    if q["title"]=="The three dials":
        order=re.search(r"order: (.+?)\.",clues)[1].split(' → ')
        mapping=dict(re.findall(r"(amber|jade|ivory) = (\d)",clues))
        return ''.join(mapping[v] for v in order)
    if q["title"]=="The copper circuit":
        order=re.search(r"flow: (.+?)\.",clues)[1].split(' → ')
        mapping=dict(re.findall(r"([ABCD]) = (\d)",clues))
        return ''.join(mapping[v] for v in order)
    if q["title"]=="The last key":
        order=[]
        for half in ('First','Second'):
            order.extend(map(int,re.search(half+r" half of the blueprint: key teeth (.+?)\.",clues)[1].split(', ')))
        keys={k["number"]:k["digit"] for k in states[0]["keys"]}
        return ''.join(keys[n] for n in order)
    raise AssertionError("Unknown mansion puzzle")

def read_mathml(node):
    tag=node.tag.split('}')[-1]
    children=[read_mathml(c) for c in node]
    if tag=='msqrt':return 'sqrt('+''.join(children)+')'
    if tag=='msup':return '('+children[0]+')^('+children[1]+')'
    if tag=='mfrac':return '('+children[0]+')/('+children[1]+')'
    if children:return ''.join(children)
    return (node.text or '').replace('×','*').replace('·','*').replace('−','-').replace('=','')

async def play(base,count,game):
    async with httpx.AsyncClient(base_url=base,timeout=60) as http:
        first=await http.post('/api/rooms',json={"name":"Smoke host"});first.raise_for_status()
        sessions=[first.json()];code=sessions[0]["code"]
        for i in range(1,count):
            response=await http.post(f'/api/rooms/{code}/join',json={"name":f"Smoke player {i}"})
            response.raise_for_status();sessions.append(response.json())
        async with AsyncExitStack() as stack:
            sockets=[]
            for session in sessions:
                ws=await stack.enter_async_context(websockets.connect(base.replace('https://','wss://').replace('http://','ws://')+f'/ws/{code}',origin=base))
                await ws.send(json.dumps({"token":session["token"]}));await state(ws)
                sockets.append(ws)
            config={"game":game,"pace":"relaxed","subject":"basic_math"}
            await send(sockets[0],"configure",config=config);await state(sockets[0],lambda s:s["config"]==config)
            for i,ws in enumerate(sockets):
                await send(ws,"ready",ready=True)
                await state(ws,lambda s:any(p["id"]==sessions[i]["player_id"] and p["ready"] for p in s["players"]))
            await state(sockets[0],lambda s:all(p["ready"] for p in s["players"]))
            await send(sockets[0],"start")
            states=[await state(ws,lambda s:s["status"]=="playing") for ws in sockets]
            await send(sockets[-1],"chat",text="Live smoke check: ready to solve.")
            for ws in sockets:await state(ws,lambda s:bool(s["chat"]))
            for i in range(states[0]["total"]):
                q=states[0]["current"]
                if game=='mansion':answer=mansion_answer(states)
                else:
                    expression=''.join(read_mathml(ET.fromstring(p["mathml"])) for p in q["parts"] if 'mathml' in p)
                    answer=str(parse_expression(expression))
                await send(sockets[i%count],"answer",puzzle_id=q["id"],answer=answer)
                states=[await state(ws,lambda s:s["index"]==i+1) for ws in sockets]
                assert len({s["score"] for s in states})==1
            assert states[0]["status"]=='won' and states[0]["score"]==1000
            print(f"PASS {count} players / {game}: complete game, shared chat and progress, 1000 points")

async def main():
    base=(sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8000').rstrip('/')
    async with httpx.AsyncClient(timeout=60) as client:
        health=await client.get(base+'/api/health');health.raise_for_status()
        print('Health:',health.json())
    await play(base,2,'mansion')
    await play(base,8,'mansion')
    await play(base,2,'math')

if __name__=='__main__':asyncio.run(main())
