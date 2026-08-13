import json
from datetime import datetime
from pathlib import Path

from config import Config
from store import atomic_write_text

# Chats live OUTSIDE memory/ on purpose: they are a UX archive (view / continue),
# NOT retrieval data. The engine never reads this folder for grounding.
CHATS_DIR = Config().chats_dir


def use_config(cfg):
    """Point the chat archive at a host app's workspace (see config.Config)."""
    global CHATS_DIR
    CHATS_DIR = cfg.chats_dir


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def new_session(seed_context=""):
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    return {
        "id": f"session-{stamp}",
        "title": "New chat",
        "created": _now(),
        "updated": _now(),
        "seed_context": seed_context,
        "messages": [],
        "status": "active",
    }


def save_session(session):
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
    session["updated"] = _now()
    path = CHATS_DIR / f"{session['id']}.json"
    atomic_write_text(path, json.dumps(session, ensure_ascii=False, indent=2))
    return path


def load_session(session_id):
    return json.loads((CHATS_DIR / f"{session_id}.json").read_text(encoding="utf-8"))


def list_sessions():
    if not CHATS_DIR.exists():
        return []
    out = []
    for p in CHATS_DIR.glob("session-*.json"):
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({
            "id": s["id"],
            "title": s.get("title", "chat"),
            "updated": s.get("updated", ""),
            "status": s.get("status", "active"),
            "count": len(s.get("messages", [])),
        })
    out.sort(key=lambda x: x["updated"], reverse=True)
    return out


def latest_session_id():
    sessions = list_sessions()
    return sessions[0]["id"] if sessions else None
