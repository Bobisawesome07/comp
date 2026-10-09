"""Independent HTTP/WebSocket clients exercise the complete app boundary."""
import contextlib
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend import main

@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("PUBLIC_ORIGIN",raising=False)
    monkeypatch.delenv("APP_ENV",raising=False)
    main.rooms.clear();main.locks.clear();main.sockets.clear();main.limits.clear()
    from backend.store import Store
    monkeypatch.setattr(main,"store",Store())
    with TestClient(main.app) as client:
        yield client

def receive_state(ws,predicate=lambda s:True):
    for _ in range(150):
        packet=ws.receive_json()
        if packet["type"]=="error":raise AssertionError(packet["message"])
        if packet["type"]=="state" and predicate(packet["state"]):return packet["state"]
    raise AssertionError("Expected state was not received")

def send(ws,kind,**extra):
    ws.send_json({"type":kind,"request_id":uuid.uuid4().hex,**extra})

def build_team(client,stack,count):
    sessions=[client.post('/api/rooms',json={"name":"Host"}).json()]
    code=sessions[0]["code"]
    for i in range(1,count):
        response=client.post(f'/api/rooms/{code}/join',json={"name":f"Guest {i}"})
        assert response.status_code==200
        sessions.append(response.json())
    sockets=[]
    for session in sessions:
        ws=stack.enter_context(client.websocket_connect(f'/ws/{code}'))
        ws.send_json({"token":session["token"]})
        receive_state(ws,lambda s:s["you"]==session["player_id"])
        sockets.append(ws)
    return code,sessions,sockets

@pytest.mark.parametrize("count",[2,8])
@pytest.mark.parametrize("game",["mansion","math"])
def test_full_games_with_independent_clients(client,count,game):
    with contextlib.ExitStack() as stack:
        code,sessions,sockets=build_team(client,stack,count)
        config={"game":game,"pace":"relaxed","subject":"basic_math"}
        send(sockets[0],"configure",config=config)
        receive_state(sockets[0],lambda s:s["config"]==config)
        for i,ws in enumerate(sockets):
            send(ws,"ready",ready=True)
            receive_state(ws,lambda s:any(p["id"]==sessions[i]["player_id"] and p["ready"] for p in s["players"]))
        receive_state(sockets[0],lambda s:all(p["ready"] for p in s["players"]))
        send(sockets[0],"start")
        states=[receive_state(ws,lambda s:s["status"]=="playing") for ws in sockets]
        assert all("answer" not in s["current"] for s in states)
        assert all('"token"' not in json.dumps(s) for s in states)
        if game=="mansion":assert len({clue for s in states for clue in s["current"]["clues"]})==2
        send(sockets[-1],"chat",text="Let's solve this together.")
        receive_state(sockets[0],lambda s:any(m["text"]=="Let's solve this together." for m in s["chat"]))
        # Tests use server fixtures for canonical answers, never a public solution endpoint.
        questions=main.rooms[code]["questions" if game=="math" else "puzzles"]
        for i,q in enumerate(questions):
            ws=sockets[i%count]
            send(ws,"answer",puzzle_id=q["id"],answer=q["answer"])
            for player_ws in sockets:
                state=receive_state(player_ws,lambda s:s["index"]==i+1)
                assert state["score"]==((i+1)*100 if game=="math" or i<6 else 1000)
        assert state["status"]=="won" and state["score"]==1000
        assert len(state["results"])==len(questions)

def test_capacity_duplicates_and_authentication(client):
    with contextlib.ExitStack() as stack:
        code,sessions,sockets=build_team(client,stack,8)
        assert client.post(f'/api/rooms/{code}/join',json={"name":"Ninth"}).status_code==409
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f'/ws/{code}') as ws:
                ws.send_json({"token":"invalid"});ws.receive_json()
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws/AAAAAA') as ws:
                ws.send_json({"token":"invalid"});ws.receive_json()
    session=client.post('/api/rooms',json={"name":"Same"}).json()
    assert client.post(f'/api/rooms/{session["code"]}/join',json={"name":"same"}).status_code==409
    assert client.post('/api/rooms',json={"name":"   "}).status_code==400

def test_reconnect_retains_identity_and_private_clues(client):
    with contextlib.ExitStack() as stack:
        code,sessions,sockets=build_team(client,stack,2)
        for ws in sockets:send(ws,"ready",ready=True)
        receive_state(sockets[0],lambda s:all(p["ready"] for p in s["players"]))
        send(sockets[0],"start")
        before=receive_state(sockets[0],lambda s:s["status"]=="playing")
        # A second connection for the same token replaces the first securely.
        ws=stack.enter_context(client.websocket_connect(f'/ws/{code}'))
        ws.send_json({"token":sessions[0]["token"]})
        after=receive_state(ws,lambda s:s["status"]=="playing")
        assert after["you"]==before["you"] and after["current"]["clues"]==before["current"]["clues"]
        assert len(after["players"])==2
        with pytest.raises(WebSocketDisconnect):
            while True:sockets[0].receive_json()

def test_unready_and_nonhost_actions_return_errors(client):
    with contextlib.ExitStack() as stack:
        code,sessions,sockets=build_team(client,stack,2)
        send(sockets[1],"start")
        while True:
            data=sockets[1].receive_json()
            if data["type"]=="error":break
        assert "host" in data["message"]
        assert main.rooms[code]["status"]=="lobby"

def test_invalid_math_returns_feedback_without_penalty(client):
    with contextlib.ExitStack() as stack:
        code,sessions,sockets=build_team(client,stack,2)
        config={"game":"math","pace":"timed","subject":"algebra"}
        send(sockets[0],"configure",config=config);receive_state(sockets[0],lambda s:s["config"]==config)
        for ws in sockets:send(ws,"ready",ready=True)
        receive_state(sockets[0],lambda s:all(p["ready"] for p in s["players"]))
        send(sockets[0],"start");state=receive_state(sockets[0],lambda s:s["status"]=="playing")
        send(sockets[0],"answer",puzzle_id=state["current"]["id"],answer="x.__class__")
        while True:
            packet=sockets[0].receive_json()
            if packet["type"]=="error":break
        state=receive_state(sockets[0])
        assert state["mistakes"]==0 and state["cooldown"]==0 and state["index"]==0

def test_origin_check_blocks_unexpected_site(client,monkeypatch):
    monkeypatch.setenv("PUBLIC_ORIGIN","https://game.example")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws/ABC234',headers={"origin":"https://other.example"}):pass
