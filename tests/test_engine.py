import copy
import json
import uuid

import pytest

from backend import engine as e

@pytest.fixture
def clock(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(e,"now",lambda:clock[0])
    return clock

def setup_room(count=2, game="mansion", pace="relaxed", subject="algebra"):
    room = e.new_room("ABC234","Player 1")
    room["players"] += [e.new_player(f"Player {i+1}") for i in range(1,count)]
    for p in room["players"]: e.connect(room,p)
    room["config"] = {"game":game,"pace":pace,"subject":subject}
    for p in room["players"]: p["ready"] = True
    act(room,"start")
    return room

def act(room, kind, player=0, **extra):
    message = {"type":kind,"request_id":uuid.uuid4().hex,**extra}
    e.action(room,room["players"][player],message)
    return message

def current(room):
    return (room["questions"] if room["config"]["game"]=="math" else room["puzzles"])[room["index"]]

@pytest.mark.parametrize("count",[2,8])
def test_complete_mansion_private_clues_and_score(count,clock):
    room=setup_room(count)
    for puzzle in room["puzzles"]:
        snapshots=[e.snapshot(room,p["id"]) for p in room["players"]]
        assert all("answer" not in s["current"] for s in snapshots)
        assert all("token" not in json.dumps(s) for s in snapshots)
        clues=[clue for s in snapshots for clue in s["current"]["clues"]]
        assert len(clues)==2 and len(set(clues))==2
        assert sum(bool(s["current"]["clues"]) for s in snapshots)==2
        act(room,"answer",puzzle_id=puzzle["id"],answer=puzzle["answer"])
    assert room["status"]=="won"
    assert e.snapshot(room,room["host"])["score"]==1000
    assert len(e.snapshot(room,room["host"])["keys"])==6

@pytest.mark.parametrize("subject",["basic_math","algebra","geometry","calculus","statistics","computer_science"])
def test_complete_math(subject,clock):
    room=setup_room(game="math",subject=subject)
    assert len(room["questions"])==10
    assert not e.snapshot(room,room["host"])["results"]
    for q in room["questions"]:
        assert "answer" not in e.snapshot(room,room["host"])["current"]
        act(room,"answer",puzzle_id=q["id"],answer=q["answer"])
    assert room["status"]=="won"
    assert e.snapshot(room,room["host"])["score"]==1000
    assert len(e.snapshot(room,room["host"])["results"])==10

def test_idempotency_stale_answers_and_cooldown(clock):
    room=setup_room();q=current(room)
    msg=act(room,"answer",puzzle_id=q["id"],answer="wrong")
    assert room["mistakes"]==1
    e.action(room,room["players"][0],msg)
    assert room["mistakes"]==1
    with pytest.raises(e.GameError,match="cooldown"):act(room,"answer",player=1,puzzle_id=q["id"],answer=q["answer"])
    clock[0]+=5
    msg=act(room,"answer",puzzle_id=q["id"],answer=q["answer"])
    e.action(room,room["players"][0],msg)
    assert room["index"]==1
    with pytest.raises(e.GameError,match="changed"):act(room,"answer",player=1,puzzle_id=q["id"],answer=q["answer"])
    assert room["index"]==1 and room["mistakes"]==1

@pytest.mark.parametrize("count",[2,8])
def test_hint_majority_and_stale_votes(count,clock):
    room=setup_room(count);q=current(room)
    threshold=count//2+1
    for i in range(threshold-1):act(room,"hint",player=i,puzzle_id=q["id"],hint_index=0)
    assert not q["revealed"]
    act(room,"hint",player=threshold-1,puzzle_id=q["id"],hint_index=0)
    assert len(q["revealed"])==1 and room["hints_used"]==1
    with pytest.raises(e.GameError,match="already been revealed"):act(room,"hint",puzzle_id=q["id"],hint_index=0)
    assert not q["votes"]

def test_pause_reconnect_host_transfer_and_deadline(clock):
    room=setup_room(pace="timed")
    clock[0]+=10
    e.disconnect(room,room["players"][0])
    assert room["segment_started"] is not None
    clock[0]+=30;e.tick(room)
    assert room["host"]==room["players"][1]["id"]
    e.disconnect(room,room["players"][1])
    assert e.elapsed(room)==40 and e.snapshot(room,room["host"])["paused"]
    clock[0]+=100
    assert e.elapsed(room)==40
    e.connect(room,room["players"][0])
    assert e.elapsed(room)==40
    clock[0]+=1160
    q=current(room)
    with pytest.raises(e.GameError,match="no active"):act(room,"answer",puzzle_id=q["id"],answer=q["answer"])
    assert room["status"]=="lost" and room["index"]==0

def test_pressure_fifth_mistake_and_score_floor(clock):
    room=setup_room(pace="pressure");q=current(room)
    for i in range(5):
        act(room,"answer",puzzle_id=q["id"],answer="incorrect")
        clock[0]+=5
    assert room["status"]=="lost" and room["mistakes"]==5
    assert e.snapshot(room,room["host"])["score"]==0

def test_timed_bonus_and_replay(clock):
    room=setup_room(pace="timed");clock[0]+=101
    for q in room["puzzles"]:act(room,"answer",puzzle_id=q["id"],answer=q["answer"])
    assert e.snapshot(room,room["host"])["score"]==1109
    act(room,"replay")
    assert room["status"]=="lobby" and room["points"]==0 and not any(p["ready"] for p in room["players"])

def test_invalid_math_no_penalty_and_no_hints(clock):
    room=setup_room(game="math");q=current(room)
    with pytest.raises(e.GameError):act(room,"answer",puzzle_id=q["id"],answer="__import__('os')")
    assert room["mistakes"]==0 and room["cooldown"]==0
    with pytest.raises(e.GameError,match="only in Mansion"):act(room,"hint",puzzle_id=q["id"],hint_index=0)

def test_restoration_pauses_at_saved_instant(clock):
    room=setup_room(pace="timed");clock[0]+=50
    room["saved_at"]=clock[0]
    saved=copy.deepcopy(room);clock[0]+=100
    restored=e.restore(saved)
    assert e.elapsed(restored)==50 and not any(p["online"] for p in restored["players"])
    e.connect(restored,restored["players"][0]);assert e.elapsed(restored)==50

def test_permissions_and_readiness(clock):
    room=e.new_room("ABC234","Host");room["players"].append(e.new_player("Guest"))
    for p in room["players"]:e.connect(room,p)
    with pytest.raises(e.GameError,match="host"):act(room,"configure",player=1,config=room["config"])
    with pytest.raises(e.GameError,match="ready"):act(room,"start")
    for p in room["players"]:p["ready"]=True
    act(room,"configure",config={"game":"math","pace":"relaxed","subject":"geometry"})
    assert not any(p["ready"] for p in room["players"])

def test_generation_failure_stays_in_lobby(monkeypatch,clock):
    room=e.new_room("ABC234","Host");room["players"].append(e.new_player("Guest"))
    for p in room["players"]:e.connect(room,p);p["ready"]=True
    room["config"]["game"]="math"
    def fail(_):raise ValueError("Generation failed")
    monkeypatch.setattr(e,"generate_questions",fail)
    with pytest.raises(e.GameError,match="Generation failed"):act(room,"start")
    assert room["status"]=="lobby" and room["segment_started"] is None
