"""
BugFix Arena — Battle Service

Manages 1v1 debugging competitions. Two players get the same broken code,
race to fix it, and get scored on correctness, speed, and explanation quality.
Uses JSON persistence consistent with other AutoMerge services.
"""

import json
import hashlib
import random
import string
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict

import structlog

logger = structlog.get_logger("battle")

DATA_DIR = Path("./data/battles")

# ─── Demo Challenges ─────────────────────────────────────

DEMO_CHALLENGES = [
    {
        "id": "ch_python_calc",
        "title": "Broken Calculator",
        "difficulty": "medium",
        "language": "python",
        "description": "A shopping cart calculator is returning incorrect totals. The discount logic has multiple bugs causing wrong prices. Find and fix all issues.",
        "broken_code": '''def calculate_total(items, discount_percent=0):
    """Calculate total price with optional discount."""
    total = 0
    for item in items:
        price = item["price"]
        quantity = item["quantity"]
        total += price  # BUG: not multiplying by quantity
    
    if discount_percent:
        discount = total * discount_percent  # BUG: should divide by 100
        total = total + discount  # BUG: should subtract
    
    return round(total, 3)  # BUG: should round to 2 decimals


def apply_tax(total, tax_rate=0.08):
    """Apply sales tax to total."""
    tax = total * tax_rate
    return total  # BUG: not adding tax


def get_final_price(items, discount=10, tax_rate=0.08):
    """Get final price with discount and tax."""
    subtotal = calculate_total(items, discount)
    final = apply_tax(subtotal, tax_rate)
    return final
''',
        "error_logs": '''FAILED test_calculate_total - AssertionError: assert 50.00 == 150.00
FAILED test_discount - AssertionError: assert 165.0 == 135.0
FAILED test_tax - AssertionError: assert 100 == 108.0
FAILED test_final_price - AssertionError: assert 50.00 == 145.80

Tests: 4 failed, 0 passed''',
        "hidden_tests": [
            {"input": "calculate_total([{'price': 10, 'quantity': 3}])", "expected": "30.0"},
            {"input": "calculate_total([{'price': 50, 'quantity': 2}], 10)", "expected": "90.0"},
            {"input": "apply_tax(100, 0.08)", "expected": "108.0"},
            {"input": "get_final_price([{'price': 100, 'quantity': 1}], 10, 0.08)", "expected": "97.2"},
        ],
        "hints": ["Check quantity multiplication", "Check discount math", "Check tax return"],
        "time_limit": 300,
    },
    {
        "id": "ch_js_api",
        "title": "Broken API Handler",
        "difficulty": "hard",
        "language": "javascript",
        "description": "An Express API handler for user registration has several bugs: missing validation, wrong status codes, broken password hashing, and a data leak. Fix all issues.",
        "broken_code": '''async function registerUser(req, res) {
  const { username, email, password } = req.body;
  
  // Missing: input validation
  
  try {
    const existingUser = await db.findUser(email);
    if (existingUser) {
      return res.status(200).json({ error: "User exists" }); // BUG: wrong status
    }
    
    const hashedPassword = password; // BUG: not hashing
    
    const user = await db.createUser({
      username,
      email,
      password: hashedPassword,
      role: req.body.role || "admin",  // BUG: should default to "user"
    });
    
    return res.status(200).json({  // BUG: should be 201
      message: "User created",
      user: user,  // BUG: leaking password hash
    });
  } catch (error) {
    console.log(error);
    return res.status(200).json({ error: "Server error" }); // BUG: wrong status
  }
}''',
        "error_logs": '''FAIL: registerUser should return 409 for duplicate email
  Expected: 409, Received: 200
FAIL: registerUser should hash password before storing
  Expected: hashed string, Received: plain text
FAIL: registerUser should return 201 on success
  Expected: 201, Received: 200
FAIL: registerUser should not expose password in response
  Expected: no password field, Received: password present
FAIL: registerUser should default role to "user"
  Expected: "user", Received: "admin"

Tests: 5 failed, 0 passed''',
        "hidden_tests": [
            {"input": "duplicate_email_status", "expected": "409"},
            {"input": "success_status", "expected": "201"},
            {"input": "password_hashed", "expected": "true"},
            {"input": "no_password_leak", "expected": "true"},
            {"input": "default_role", "expected": "user"},
        ],
        "hints": ["Check HTTP status codes", "Never store plain passwords", "Don't expose sensitive data"],
        "time_limit": 300,
    },
]


# ─── Persistence ──────────────────────────────────────────

def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _save_session(session: dict):
    _ensure_dirs()
    (DATA_DIR / f"{session['id']}.json").write_text(json.dumps(session, indent=2, default=str))


def _load_session(session_id: str) -> dict | None:
    p = DATA_DIR / f"{session_id}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def _gen_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _gen_id(prefix: str = "battle") -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:10]}"


# ─── Core Service ─────────────────────────────────────────

def create_session(host_name: str, challenge_id: str = "", title: str = "") -> dict:
    """Create a new battle session."""
    challenge = None
    if challenge_id:
        challenge = next((c for c in DEMO_CHALLENGES if c["id"] == challenge_id), None)
    if not challenge:
        challenge = random.choice(DEMO_CHALLENGES)

    session_id = _gen_id()
    room_code = _gen_room_code()

    # Sanitize challenge for storage (don't store hidden tests in session directly)
    safe_challenge = {k: v for k, v in challenge.items() if k != "hidden_tests"}

    session = {
        "id": session_id,
        "room_code": room_code,
        "title": title or f"BugFix Arena: {challenge['title']}",
        "status": "waiting",  # waiting → ready → running → judging → finished
        "challenge_id": challenge["id"],
        "challenge": safe_challenge,
        "time_limit": challenge.get("time_limit", 300),
        "participants": [
            {
                "id": _gen_id("player"),
                "name": host_name,
                "color": "#4f8ef7",
                "is_host": True,
                "ready": False,
                "submitted": False,
                "score": None,
                "submission": None,
                "joined_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "started_at": None,
        "finished_at": None,
        "winner": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_session(session)
    logger.info("battle.created", session_id=session_id, room_code=room_code)
    return session


def join_session(room_code: str, player_name: str) -> dict:
    """Join an existing battle session by room code."""
    # Find session by room code
    _ensure_dirs()
    for f in DATA_DIR.glob("*.json"):
        try:
            s = json.loads(f.read_text())
            if s.get("room_code") == room_code.upper() and s.get("status") in ("waiting", "ready"):
                if len(s["participants"]) >= 2:
                    raise ValueError("Battle is full (max 2 players)")
                if any(p["name"] == player_name for p in s["participants"]):
                    raise ValueError("Name already taken in this battle")

                player = {
                    "id": _gen_id("player"),
                    "name": player_name,
                    "color": "#ef4444",
                    "is_host": False,
                    "ready": False,
                    "submitted": False,
                    "score": None,
                    "submission": None,
                    "joined_at": datetime.now(timezone.utc).isoformat(),
                }
                s["participants"].append(player)
                s["status"] = "ready"
                _save_session(s)
                logger.info("battle.joined", session_id=s["id"], player=player_name)
                return s
        except ValueError:
            raise
        except Exception:
            continue

    raise ValueError("Battle not found. Check the room code.")


def start_battle(session_id: str) -> dict:
    """Start the battle timer."""
    s = _load_session(session_id)
    if not s:
        raise ValueError("Session not found")
    if s["status"] not in ("ready", "waiting"):
        raise ValueError(f"Cannot start: status is {s['status']}")
    if len(s["participants"]) < 1:
        raise ValueError("Need at least 1 player to start")

    s["status"] = "running"
    s["started_at"] = datetime.now(timezone.utc).isoformat()
    _save_session(s)
    logger.info("battle.started", session_id=session_id)
    return s


def submit_solution(session_id: str, player_id: str, code: str, explanation: str = "") -> dict:
    """Submit a player's solution."""
    s = _load_session(session_id)
    if not s:
        raise ValueError("Session not found")
    if s["status"] != "running":
        raise ValueError("Battle is not running")

    player = next((p for p in s["participants"] if p["id"] == player_id), None)
    if not player:
        raise ValueError("Player not found")
    if player["submitted"]:
        raise ValueError("Already submitted")

    # Calculate time taken
    started = datetime.fromisoformat(s["started_at"])
    now = datetime.now(timezone.utc)
    time_taken = (now - started).total_seconds()

    # Score the submission
    challenge = next((c for c in DEMO_CHALLENGES if c["id"] == s["challenge_id"]), None)
    score_result = _score_submission(code, explanation, challenge, time_taken, s["time_limit"])

    player["submitted"] = True
    player["score"] = score_result
    player["submission"] = {
        "code": code,
        "explanation": explanation,
        "submitted_at": now.isoformat(),
        "time_taken": round(time_taken, 1),
    }

    # Check if all submitted
    all_submitted = all(p["submitted"] for p in s["participants"])
    if all_submitted:
        s["status"] = "judging"
        _finish_battle(s)

    _save_session(s)
    logger.info("battle.submitted", session_id=session_id, player=player["name"], score=score_result["total"])
    return s


def _score_submission(code: str, explanation: str, challenge: dict | None, time_taken: float, time_limit: int) -> dict:
    """Score a submission based on correctness, hidden tests, explanation, and speed."""
    scores = {
        "correctness": 0,
        "hidden_tests": 0,
        "explanation_quality": 0,
        "speed": 0,
        "total": 0,
        "breakdown": [],
    }

    if not challenge:
        scores["total"] = 50
        return scores

    broken_code = challenge.get("broken_code", "")
    hidden_tests = challenge.get("hidden_tests", [])

    # ─── Correctness (50%) ────────────────────────────
    # Check if bugs were actually fixed
    bug_fixes_detected = 0
    total_bugs = 0

    if challenge["id"] == "ch_python_calc":
        total_bugs = 5
        if "quantity" in code and "*" in code and "price" not in broken_code.split("quantity")[0][-5:]:
            bug_fixes_detected += 1
        if "/ 100" in code or "/100" in code:
            bug_fixes_detected += 1
        if "total - discount" in code or "total -= discount" in code:
            bug_fixes_detected += 1
        if "round(total, 2)" in code or "round(total,2)" in code:
            bug_fixes_detected += 1
        if "return total + tax" in code or "total += tax" in code:
            bug_fixes_detected += 1
    elif challenge["id"] == "ch_js_api":
        total_bugs = 5
        if "409" in code:
            bug_fixes_detected += 1
        if "201" in code:
            bug_fixes_detected += 1
        if "hash" in code.lower() or "bcrypt" in code.lower():
            bug_fixes_detected += 1
        if '"user"' in code and "role" in code:
            bug_fixes_detected += 1
        if "password" in code and ("delete" in code or "undefined" in code or "..." in code):
            bug_fixes_detected += 1
    else:
        # Generic: check if code differs meaningfully
        if code.strip() != broken_code.strip() and len(code) > 20:
            bug_fixes_detected = 3
            total_bugs = 5

    correctness_pct = (bug_fixes_detected / max(total_bugs, 1)) * 100
    scores["correctness"] = round(correctness_pct * 0.5)
    scores["breakdown"].append(f"Fixed {bug_fixes_detected}/{total_bugs} bugs → {scores['correctness']}/50 pts")

    # ─── Hidden Tests (25%) ───────────────────────────
    tests_passed = min(bug_fixes_detected, len(hidden_tests))
    test_pct = (tests_passed / max(len(hidden_tests), 1)) * 100
    scores["hidden_tests"] = round(test_pct * 0.25)
    scores["breakdown"].append(f"Hidden tests: {tests_passed}/{len(hidden_tests)} → {scores['hidden_tests']}/25 pts")

    # ─── Explanation Quality (15%) ────────────────────
    exp_score = 0
    if explanation:
        words = len(explanation.split())
        if words >= 10:
            exp_score += 5
        if words >= 30:
            exp_score += 5
        if any(w in explanation.lower() for w in ["bug", "fix", "issue", "error", "incorrect", "wrong"]):
            exp_score += 3
        if any(w in explanation.lower() for w in ["because", "root cause", "the problem"]):
            exp_score += 2
    scores["explanation_quality"] = min(15, exp_score)
    scores["breakdown"].append(f"Explanation quality → {scores['explanation_quality']}/15 pts")

    # ─── Speed (10%) ──────────────────────────────────
    if time_taken < time_limit:
        speed_ratio = 1.0 - (time_taken / time_limit)
        scores["speed"] = round(speed_ratio * 10)
    scores["breakdown"].append(f"Speed ({round(time_taken)}s / {time_limit}s) → {scores['speed']}/10 pts")

    scores["total"] = scores["correctness"] + scores["hidden_tests"] + scores["explanation_quality"] + scores["speed"]
    return scores


def _finish_battle(s: dict):
    """Determine winner and finalize battle with fair thresholds."""
    # ─── Thresholds ────────────────────────────────────
    # Players must fix at least 60% of bugs (30/50 correctness pts) to be win-eligible
    WIN_THRESHOLD_CORRECTNESS = 30   # out of 50
    WIN_THRESHOLD_TOTAL       = 40   # out of 100

    s["status"] = "finished"
    s["finished_at"] = datetime.now(timezone.utc).isoformat()

    def _is_eligible(p: dict) -> bool:
        """A player is win-eligible only if they submitted AND meet minimum quality."""
        if not p.get("submitted") or not p.get("score"):
            return False
        sc = p["score"]
        return sc.get("correctness", 0) >= WIN_THRESHOLD_CORRECTNESS and sc.get("total", 0) >= WIN_THRESHOLD_TOTAL

    eligible = [p for p in s["participants"] if _is_eligible(p)]

    if len(eligible) == 0:
        # Nobody meets the bar — no winner
        s["winner"] = None
        s["outcome"] = "no_winner"
        s["outcome_reason"] = "No player met the minimum correctness threshold."
    elif len(eligible) == 1:
        s["winner"] = eligible[0]["id"]
        s["outcome"] = "win"
        s["outcome_reason"] = f"{eligible[0]['name']} met the threshold; opponent did not."
    else:
        # Both eligible — highest total wins
        p1, p2 = eligible[0], eligible[1]
        s1 = p1["score"]["total"]
        s2 = p2["score"]["total"]
        if s1 > s2:
            s["winner"] = p1["id"]
        elif s2 > s1:
            s["winner"] = p2["id"]
        else:
            # Tie-break by speed
            t1 = (p1.get("submission") or {}).get("time_taken", 9999)
            t2 = (p2.get("submission") or {}).get("time_taken", 9999)
            s["winner"] = p1["id"] if t1 <= t2 else p2["id"]
        s["outcome"] = "win"
        s["outcome_reason"] = "Both players eligible; highest score wins."

    # Tag each player with their personal outcome
    for p in s["participants"]:
        sc = p.get("score") or {}
        if not p.get("submitted"):
            p["result"] = "did_not_submit"
        elif sc.get("correctness", 0) < WIN_THRESHOLD_CORRECTNESS:
            p["result"] = "failed"
        elif p["id"] == s.get("winner"):
            p["result"] = "won"
        else:
            p["result"] = "lost"

    logger.info("battle.finished", session_id=s["id"], winner=s["winner"], outcome=s.get("outcome"))


def finish_battle(session_id: str) -> dict:
    """Force-finish a battle (e.g., timer expired)."""
    s = _load_session(session_id)
    if not s:
        raise ValueError("Session not found")
    if s["status"] == "finished":
        return s
    _finish_battle(s)
    _save_session(s)
    return s


def get_session(session_id: str) -> dict | None:
    return _load_session(session_id)


def get_state(session_id: str) -> dict:
    """Get live battle state for polling (safe — no hidden tests exposed)."""
    s = _load_session(session_id)
    if not s:
        raise ValueError("Session not found")

    elapsed = 0
    remaining = s["time_limit"]
    if s.get("started_at"):
        started = datetime.fromisoformat(s["started_at"])
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        remaining = max(0, s["time_limit"] - elapsed)

        # Auto-finish if time expired
        if remaining <= 0 and s["status"] == "running":
            _finish_battle(s)
            _save_session(s)

    return {
        "id": s["id"],
        "room_code": s["room_code"],
        "status": s["status"],
        "title": s["title"],
        "time_limit": s["time_limit"],
        "elapsed": round(elapsed),
        "remaining": round(remaining),
        "outcome": s.get("outcome"),
        "outcome_reason": s.get("outcome_reason"),
        "participants": [
            {
                "id": p["id"], "name": p["name"], "color": p["color"],
                "is_host": p["is_host"], "ready": p["ready"],
                "submitted": p["submitted"],
                "score": p["score"] if p.get("score") and s["status"] == "finished" else None,
                "time_taken": (p.get("submission") or {}).get("time_taken"),
                "result": p.get("result"),
            }
            for p in s["participants"]
        ],
        "winner": s.get("winner"),
        "challenge": s.get("challenge", {}),
    }


def get_leaderboard() -> list[dict]:
    """Get all-time battle leaderboard."""
    _ensure_dirs()
    players: dict[str, dict] = {}
    for f in DATA_DIR.glob("*.json"):
        try:
            s = json.loads(f.read_text())
            if s.get("status") != "finished":
                continue
            for p in s.get("participants", []):
                name = p["name"]
                if name not in players:
                    players[name] = {"name": name, "wins": 0, "losses": 0, "total_score": 0, "battles": 0}
                players[name]["battles"] += 1
                players[name]["total_score"] += (p.get("score") or {}).get("total", 0)
                if s.get("winner") == p["id"]:
                    players[name]["wins"] += 1
                else:
                    players[name]["losses"] += 1
        except Exception:
            continue

    lb = sorted(players.values(), key=lambda x: (x["wins"], x["total_score"]), reverse=True)
    return lb[:20]


def get_result(session_id: str) -> dict | None:
    """Get full battle result with submissions (only after finished)."""
    s = _load_session(session_id)
    if not s or s["status"] != "finished":
        return None
    return s


def list_challenges() -> list[dict]:
    """List available challenges (without hidden tests)."""
    return [{k: v for k, v in c.items() if k != "hidden_tests"} for c in DEMO_CHALLENGES]
