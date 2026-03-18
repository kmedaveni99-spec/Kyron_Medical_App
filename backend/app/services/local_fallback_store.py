"""Local fallback event persistence for third-party API outages."""
import datetime
import json
from pathlib import Path

FALLBACK_DIR = Path(__file__).parent.parent.parent / "notifications"


def save_fallback_event(event_type: str, payload: dict) -> str | None:
    """Persist a fallback event to local storage and return the file path."""
    try:
        FALLBACK_DIR.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = FALLBACK_DIR / f"fallback_{event_type}_{ts}.json"
        record = {
            "type": "fallback",
            "event_type": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "payload": payload,
        }
        with open(filename, "w") as f:
            json.dump(record, f, indent=2, default=str)
        return str(filename)
    except Exception as e:
        print(f"Failed to persist fallback event {event_type}: {e}")
        return None

