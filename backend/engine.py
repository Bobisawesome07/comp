import math
import secrets
import time
import uuid

from .mansion import generate_mansion, normalize_answer
from .math_service import SUBJECTS, InvalidAnswer, generate_questions, grade, public_question

class GameError(ValueError):
    pass

def now():
    return time.time()

def new_player(name):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 24:
        raise GameError("Choose a name between 1 and 24 characters.")
    return {"id": uuid.uuid4().hex, "name": name.strip(), "token": secrets.token_urlsafe(32),
            "online": False, "ready": False, "last_seen": now(), "offline_since": now()}

def new_room(code, name):
    player = new_player(name)
    return {"code": code, "host": player["id"], "players": [player], "status": "lobby",
            "config": {"game": "mansion", "pace": "timed", "subject": "algebra"},
            "puzzles": [], "questions": [], "index": 0, "mistakes": 0, "hints_used": 0,
            "points": 0, "bonus": 0, "elapsed": 0, "segment_started": None,
            "cooldown": 0, "chat": [], "requests": [], "updated": now(), "saved_at": now(),
            "reason": None}

def elapsed(room):
    return room["elapsed"] + (now() - room["segment_started"] if room["segment_started"] is not None else 0)

def limit(room):
    return {"relaxed": None, "timed": 1200, "pressure": 720}[room["config"]["pace"]]

def stop_clock(room):
    room["elapsed"] = elapsed(room)
    room["segment_started"] = None

def finish(room, won, reason):
    stop_clock(room)
    room["status"] = "won" if won else "lost"
    room["reason"] = reason
    room["bonus"] = max(0, math.floor((limit(room)-room["elapsed"])/10)) if won and limit(room) else 0

def tick(room):
    if room["status"] == "playing":
        online = [p for p in room["players"] if p["online"]]
        if not online and room["segment_started"] is not None:
            stop_clock(room)
        elif online and room["segment_started"] is None:
            room["segment_started"] = now()
        if limit(room) is not None and elapsed(room) >= limit(room):
            finish(room, False, "Time ran out")
    host = next(p for p in room["players"] if p["id"] == room["host"])
    if not host["online"] and now()-host["offline_since"] >= 30:
        candidates = [p for p in room["players"] if p["online"]]
        if candidates: room["host"] = candidates[0]["id"]

def connect(room, player):
    player.update(online=True, last_seen=now())
    tick(room)
    room["updated"] = now()

def disconnect(room, player):
    player.update(online=False, offline_since=now(), ready=False)
    tick(room)
    room["updated"] = now()

def restore(room):
    # A process restart resumes from the last persisted instant, not from stale connections.
    if room["segment_started"] is not None:
        room["elapsed"] += max(0, room["saved_at"]-room["segment_started"])
    room["segment_started"] = None
    for p in room["players"]:
        p.update(online=False, ready=False, offline_since=now())
    return room

def action(room, player, message):
    tick(room)
    kind = message.get("type")
    if kind == "ping":
        player["last_seen"] = now()
        return
    request_id = message.get("request_id")
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100:
        raise GameError("Missing action identifier.")
    request_key = player["id"]+":"+request_id
    if request_key in room["requests"]: return
    if kind == "chat":
        text = message.get("text", "")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 500:
            raise GameError("Messages must be between 1 and 500 characters.")
        previous = [m for m in room["chat"] if m["player_id"] == player["id"]]
        if previous and now()-previous[-1]["time"] < .5:
            raise GameError("Give your teammates a moment to read your message.")
        room["chat"].append({"id": uuid.uuid4().hex, "player_id": player["id"], "name": player["name"], "text": text.strip(), "time": now()})
        room["chat"] = room["chat"][-100:]
    elif kind in ("configure", "start", "replay"):
        if room["host"] != player["id"]: raise GameError("Only the host can do that.")
        if kind == "replay":
            if room["status"] not in ("won", "lost"): raise GameError("Finish this game first.")
            room.update(status="lobby", puzzles=[], questions=[], index=0, elapsed=0, segment_started=None,
                        points=0, bonus=0, mistakes=0, hints_used=0, reason=None, cooldown=0)
            for p in room["players"]: p["ready"] = False
        else:
            if room["status"] != "lobby": raise GameError("Settings are locked during a game.")
            if kind == "configure":
                config = message.get("config")
                if not isinstance(config, dict) or config.get("game") not in ("mansion", "math") or config.get("pace") not in ("relaxed", "timed", "pressure") or config.get("subject") not in SUBJECTS:
                    raise GameError("Choose valid game settings.")
                room["config"] = {k: config[k] for k in ("game", "pace", "subject")}
                for p in room["players"]: p["ready"] = False
            else:
                if len(room["players"]) < 2 or not all(p["online"] and p["ready"] for p in room["players"]):
                    raise GameError("At least two players must join, and everyone must be connected and ready.")
                if room["config"]["game"] == "math":
                    try: room["questions"] = generate_questions(room["config"]["subject"])
                    except ValueError as exc: raise GameError(str(exc))
                else:
                    room["puzzles"] = generate_mansion([p["id"] for p in room["players"]])
                room.update(status="playing", elapsed=0, segment_started=now())
    elif kind == "kick":
        if room["host"] != player["id"] or room["status"] != "lobby":
            raise GameError("Only the host can remove an absent player from the lobby.")
        target = next((p for p in room["players"] if p["id"] == message.get("player_id")),None)
        if not target or target["online"] or target["id"] == room["host"]:
            raise GameError("Only absent teammates can be removed.")
        room["players"].remove(target)
        for p in room["players"]: p["ready"] = False
    elif kind == "ready":
        if room["status"] != "lobby": raise GameError("The game has already started.")
        if type(message.get("ready")) is not bool: raise GameError("Invalid readiness value.")
        player["ready"] = message["ready"]
    elif kind in ("answer", "hint"):
        if room["status"] != "playing": raise GameError("There is no active game.")
        is_math = room["config"]["game"] == "math"
        current = (room["questions"] if is_math else room["puzzles"])[room["index"]]
        if message.get("puzzle_id") != current["id"]: raise GameError("That puzzle has already changed. Try the current one.")
        if kind == "hint":
            if is_math: raise GameError("Hints are available only in Mansion Escape.")
            if len(current["revealed"]) == 2: raise GameError("Both hints have been revealed.")
            if message.get("hint_index") != len(current["revealed"]):
                raise GameError("That hint has already been revealed. Review it before requesting another.")
            if player["id"] not in current["votes"]: current["votes"].append(player["id"])
            if len(current["votes"]) > len(room["players"])/2:
                current["revealed"].append(current["hints"][len(current["revealed"])])
                current["votes"] = []
                room["hints_used"] += 1
        else:
            if now() < room["cooldown"]: raise GameError("The team submission cooldown is still active.")
            raw = message.get("answer")
            if not isinstance(raw, str) or not raw.strip() or len(raw) > 160: raise GameError("Enter an answer of at most 160 characters.")
            try:
                correct = grade(current, raw) if is_math else normalize_answer(raw) == normalize_answer(current["answer"])
            except InvalidAnswer as exc:
                raise GameError(str(exc))
            # Grading can take time; enforce the deadline again before accepting it.
            tick(room)
            if room["status"] != "playing": raise GameError("Time ran out before the answer was accepted.")
            if correct:
                room["points"] += 100 if is_math or room["index"] < 6 else 400
                if not is_math: current["solved"] = True
                room["index"] += 1
                if room["index"] == (10 if is_math else 7): finish(room, True, "All questions solved" if is_math else "You escaped the mansion")
            else:
                room["mistakes"] += 1
                room["cooldown"] = now()+5
                if room["config"]["pace"] == "pressure" and room["mistakes"] >= 5:
                    finish(room, False, "Five incorrect answers")
    else:
        raise GameError("Unknown action.")
    room["requests"].append(request_key)
    room["requests"] = room["requests"][-2000:]
    room["updated"] = now()

def snapshot(room, pid):
    is_math = room["config"]["game"] == "math"
    result = {"code": room["code"], "host": room["host"], "you": pid, "status": room["status"],
              "config": room["config"], "players": [{k:p[k] for k in ("id", "name", "online", "ready")} for p in room["players"]],
              "index": room["index"], "total": 10 if is_math else 7,
              "score": max(0, room["points"] - 10*room["mistakes"] - 25*room["hints_used"] + room["bonus"]),
              "bonus": room["bonus"], "mistakes": room["mistakes"], "hints_used": room["hints_used"],
              "elapsed": math.floor(elapsed(room)), "remaining": max(0, math.ceil(limit(room)-elapsed(room))) if limit(room) else None,
              "paused": room["status"] == "playing" and room["segment_started"] is None,
              "cooldown": max(0, math.ceil(room["cooldown"]-now())), "chat": room["chat"], "reason": room["reason"],
              "keys": [{"number": i+1, "digit": p["key"]} for i,p in enumerate(room["puzzles"][:6]) if p["solved"]],
              "current": None, "results": []}
    if room["status"] == "playing":
        q = (room["questions"] if is_math else room["puzzles"])[room["index"]]
        result["current"] = public_question(q) if is_math else {k:q[k] for k in ("id", "room", "title", "story", "format", "revealed", "votes")}
        if not is_math: result["current"]["clues"] = q["clues"].get(pid, [])
    elif room["status"] in ("won", "lost"):
        result["results"] = [dict(public_question(q), answer=q["answer"], solved=i<room["index"]) for i,q in enumerate(room["questions"])] if is_math else [{"title":q["title"],"solved":q["solved"]} for q in room["puzzles"]]
    return result
