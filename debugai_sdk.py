import sys
import traceback
import httpx
from datetime import datetime


DEBUGAI_SERVER = "http://127.0.0.1:8000"
_config = {
    "repo": None,
    "server": DEBUGAI_SERVER,
    "enabled": True
}


def _format_traceback(exc_type, exc_value, exc_traceback):
    lines = []
    lines.append(f"2{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ERROR [AutoCapture] Unhandled exception: {exc_type.__name__}: {exc_value}")

    frames = traceback.extract_tb(exc_traceback)
    for frame in frames:
        lines.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ERROR [AutoCapture] Traceback: {frame.filename.split('/')[-1].split(chr(92))[-1]} line {frame.lineno}, in {frame.name}")
        if frame.line:
            lines.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ERROR [AutoCapture] Code: {frame.line.strip()}")

    return "\n".join(lines)


def _exception_handler(exc_type, exc_value, exc_traceback):
    if not _config["enabled"]:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    log_text = _format_traceback(exc_type, exc_value, exc_traceback)

    print(f"\n[debugai] Capturing crash and sending for analysis...")

    try:
        response = httpx.post(
            f"{_config['server']}/ingest",
            json={
                "log_text": log_text,
                "repo": _config["repo"],
                "source": "python_sdk"
            },
            timeout=30
        )
        data = response.json()
        if data.get("status") == "success":
            print(f"[debugai] Incident #{data['incident_id']} captured. View at {_config['server']}/ui")
        else:
            print(f"[debugai] Capture failed: {data.get('message', 'unknown error')}")
    except Exception as e:
        print(f"[debugai] Could not send crash report: {e}")

    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def install(repo=None, server=None):
    if repo:
        _config["repo"] = repo
    if server:
        _config["server"] = server

    sys.excepthook = _exception_handler
    print(f"[debugai] Crash handler installed. Server: {_config['server']}")