import sys
import traceback
import httpx
from datetime import datetime


DEBUGAI_SERVER = "http://127.0.0.1:8000"
_config = {
    "repo": None,
    "server": DEBUGAI_SERVER,
    "enabled": True,
    "api_key": None
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
            headers={"X-API-Key": _config["api_key"]},
            timeout=30
        )
        data = response.json()
        if data.get("status") == "success":
            print(f"[debugai] Incident #{data['incident_id']} captured.")
            if data.get("diagnosis"):
                print(f"\n{'='*60}")
                print("[debugai] DIAGNOSIS")
                print(f"{'='*60}")
                print(data["diagnosis"])
                print(f"{'='*60}\n")
            print(f"[debugai] View full incident at {_config['server']}/ui")
        else:
            print(f"[debugai] Capture failed: {data.get('message', 'unknown error')}")
    except Exception as e:
        print(f"[debugai] Could not send crash report: {e}")

    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
def install(repo=None, server=None, api_key=None):
    if not api_key:
        raise ValueError("[debugai] api_key is required. Get yours from your Roota dashboard and pass it to install(api_key=...)")

    if repo:
        _config["repo"] = repo
    if server:
        _config["server"] = server
    _config["api_key"] = api_key

    sys.excepthook = _exception_handler
    print(f"[debugai] Crash handler installed. Server: {_config['server']}")