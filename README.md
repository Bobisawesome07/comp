# The Last Key

A real-time cooperative browser game for 2–8 people, with room-code invitations, private mansion clues, shared math questions, text chat, and anonymous reconnection. The frontend uses React, TypeScript, Vite, and **Bun**. The server uses Python, FastAPI, WebSockets, and Redis.

## Run locally

Requirements: Bun 1.4.2 or later and Python 3.11. Install [Bun](https://bun.com/docs/installation) if needed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cd frontend
bun install --frozen-lockfile
bun run build
cd ..
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Open http://localhost:8000. Create a room, then join from another browser tab or device using the invitation code. On the same Wi-Fi, other devices need the computer's LAN address, for example `http://192.168.1.10:8000`; `localhost` on a phone refers to the phone. Allow the server through the computer's firewall if prompted.

Local development works without Redis, using memory storage. In this mode rooms disappear when the server stops. Set `REDIS_URL` before starting to enable persisted room recovery. In production, the server refuses to start without Redis.

For frontend development, run `bun run dev` inside `frontend/` while the Python server runs on port 8000. Vite proxies `/api` and `/ws` to that server.

### Docker and Redis

```sh
docker compose up --build
```

This starts the game on port 8000 and Redis with an append-only persistent volume. `compose.yaml` sets `PUBLIC_ORIGIN=http://localhost:8000`. For LAN testing with Docker, change it to the exact URL players will use, or remove that override and use HTTPS for production.

## Deploy on Render

The repository includes `render.yaml`, defining a **Free Docker web service** and **Free Key Value service**, with the private Redis connection wired automatically.

1. Push this source to a GitHub repository and allow Render to access that repository.
2. In Render, choose **New → Blueprint**, select the repository and `main`, and use `render.yaml`.
3. Confirm that both instances are **Free** before deploying. The Docker build uses Bun for the frontend and installs the Python dependencies.
4. Open the resulting HTTPS URL. `/api/health` should report `status: ok` and `storage: redis`.
5. Create a room and join from another device on another network. Verify chat and a shared answer before distributing the URL.

Free services have cold starts. Free Key Value does not persist data through a Redis service restart, although it preserves room snapshots through game-server restarts while Redis remains running. Persistent Redis infrastructure or a paid Key Value plan is needed to survive Redis restarts; do not upgrade without choosing that cost explicitly. See [Render's free-service limits](https://render.com/docs/free).

Use **one instance and one Uvicorn worker**. Redis stores snapshots; connected sockets and per-room action locks live in the application process. Horizontal scaling requires a shared event bus and distributed room ownership, which this version does not implement. Keep `APP_ENV=production` and serve through HTTPS. `PUBLIC_ORIGIN` can restrict WebSocket connections to an exact custom domain; otherwise the request's HTTPS host is used.

## Rules

- A host creates a six-character room code. Join with a display name; no accounts are required. The host selects the mode and pace. Changing settings or joining resets readiness. Everyone must be connected and ready before starting.
- **Mansion Escape:** The Foyer, Library, and Secret Study each contain two puzzles. Solve all six to unlock a seventh final-door puzzle. Clues are dealt across players so two people can solve every puzzle and larger teams share clue duty. Six recovered key teeth are used at the final door. Codes and clue assignments change between runs.
- **Math:** Select basic math, algebra, geometry, calculus, statistics, or computer science. Solve ten verified, randomly generated questions, one at a time, as a team. Each device has its own answer draft. Questions and typed-answer previews use MathML.
- **Pace:** Relaxed has no deadline; Timed lasts 20 minutes; High Pressure lasts 12 minutes and ends on the fifth incorrect submission.
- **Scoring:** Each room puzzle or math question gives 100 points; the mansion's final escape gives 400. Each incorrect answer costs 10 points and starts a five-second team cooldown. Successful timed runs add one point for every full ten seconds remaining. Scores never go below zero.
- **Hints:** Mansion puzzles each have two progressive hints, including the final door. A majority must vote for a hint, with both players required in two-player games. Each revealed hint costs 25 points. Math has no hints.
- **Ending:** Complete every puzzle/question to win. A deadline or mistake limit ends the run. Results reveal score, elapsed time, mistakes, and hints. Math results reveal all ten questions and answers.
- **Recovery:** Refresh or reconnect from the original tab. The home screen also offers reconnection to the latest room used on that device. If everyone disconnects, the clock pauses. An absent host's controls transfer after 30 seconds. Abandoned rooms expire after 24 hours; connected rooms refresh their storage TTL.
- Hosts can remove absent players in the lobby so abandoned seats do not block readiness. Players cannot join a game already in progress except by reconnecting with their existing token.

## Math adapters

The server runs the actual [`mathgenerator` Python library](https://lukew3.github.io/mathgenerator/mathgenerator.html), version 1.5.0. The linked page is library documentation, not a hosted HTTP question service.

Vetted generators:

| Subject | Included generators |
| --- | --- |
| Basic math | Addition, subtraction, multiplication, square root |
| Algebra | Basic algebra, combine like terms, factoring |
| Geometry | Third triangle angle, triangle area |
| Calculus | Power-rule differentiation, definite integrals |
| Statistics | Combinations, dice-sum probability |
| Computer science | Binary to decimal, modulo, one's complement |

Each adapter computes its own expected solution and compares it to the generator's result before admitting the question. Undefined modulo questions, faulty generated answers, and duplicate questions are discarded. The known faulty power-rule integration generator is excluded. Ten questions are prepared before the clock starts; generation failure leaves the team in the lobby.

Supported typed notation includes `1/2`, `2x^2`, `(x+1)(x-1)`, `sqrt(9)`, `sin(x)`, `cos(x)`, `tan(x)`, `abs(x)`, `log(x)`, `exp(x)`, `pi`, and `e`. A restricted AST parser constructs bounded mathematical expressions without evaluating player code. Equivalent fractions and expressions are accepted. Rounded questions specify their precision and accept values within half a last decimal place of the expected result. One's-complement questions require the full bit string, preserving leading zeros. Invalid syntax does not count as a wrong answer.

## Verification

```sh
.venv/bin/python -m pytest -q
cd frontend
bun run test
bun run build
```

The backend tests cover complete two- and eight-client games through independent HTTP/WebSocket clients, private clue isolation, shared chat/progress, canonical math grading, input restrictions, hint voting, scoring, duplicate submissions, cooldowns, deadlines, host transfer, pausing, reconnect replacement, authentication, and Redis snapshots/TTL. Frontend tests verify MathML previews and rejection of unsupported notation. Redis persistence tests use `fakeredis`; deployment smoke checks use the real deployed Redis service.

## Server interfaces

- `GET /api/health`: readiness and storage status.
- `GET /api/subjects`: enabled subject IDs and labels.
- `POST /api/rooms` with `{ "name": "Morgan" }`: create a room and return its code, player ID, and reconnect token.
- `POST /api/rooms/{code}/join` with the same body: join a lobby, up to eight players.
- `WS /ws/{code}`: authenticate with `{ "token": "..." }` as the first message. Tokens never go in URL parameters.

Subsequent actions carry `type` and a unique `request_id`: `configure`, `ready`, `start`, `chat`, `answer`, `hint`, `kick`, or `replay`. Answers name `puzzle_id`; hints additionally name `hint_index`. Heartbeats use `type: ping`. The server sends `state`, `ack`, or `error` packets. Each state includes only that recipient's private clues and never includes active question solutions or another player's token.

Room changes are serialized, acknowledged, and persisted. Browsers reconnect with exponential backoff. A replaced tab stops reconnecting to avoid competing sessions. Display names, room capacity, input lengths, chat rate, action rate, and connection origins are checked on the server.
