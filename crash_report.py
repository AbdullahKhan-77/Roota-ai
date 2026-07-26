import json
import glob
import os
import sys
from crashdump import report_crash

CONFIG_FILE = ".roota.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"[debugai-cpp] No {CONFIG_FILE} found. Create one with your api_key and repo.")
        sys.exit(1)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def find_latest_report(directory="cpp_integration"):
    pattern = os.path.join(directory, "crash_report_*.log")
    reports = glob.glob(pattern)
    if not reports:
        print(f"[debugai-cpp] No crash reports found in {directory}/")
        sys.exit(1)
    return max(reports, key=os.path.getmtime)


if __name__ == '__main__':
    config = load_config()
    report_path = find_latest_report()
    print(f"[debugai-cpp] Found report: {report_path}")
    report_crash(
        report_path,
        api_key=config["api_key"],
        repo=config.get("repo"),
        server=config.get("server", "https://tryroota.dev")
    )