# Roota

**AI-powered production debugger.** Feed it a log file (and optionally a GitHub repo), and it finds the root cause, explains the failure chain, and tells you the exact line to fix — powered by Gemini.

Works with plain logs, Python crashes, and C++ crashes (Linux and Windows), locally or synced to a dashboard.

```
$ debugai --log server.log --repo myorg/myrepo

ROOT CAUSE:
UserService.SessionManager.get_session doesn't check for key existence
before dictionary access, causing a KeyError when a session expires
under memory pressure. This crash prevents the DB connection from
being released, leading to pool exhaustion.

FIX:
- return self.active_sessions[user_id]
+ return self.active_sessions.get(user_id)
```

---

## Why Roota

Most log tools show you *what* happened. Roota tells you *why*, and shows you the fix — with the actual source code from your repo, not just a stack trace.

- **Local-first CLI** — no signup, no account, just point it at a log file
- **Cross-platform crash capture** — Python and C++ (Linux + Windows) auto-capture unhandled crashes
- **GitHub-aware** — fetches the relevant source file automatically so the AI diagnosis references your real code, real variable names, real line numbers
- **Optional dashboard** — sync incidents to a web dashboard for team visibility and history, only if you want it

---

## Quick start (CLI, zero setup)

```bash
pip install -r requirements.txt
python debugai.py --log demo.log --repo owner/repo
```

That's it — no account, no API key, fully local. Add `--sync --api-key YOUR_KEY` if you want the result saved to your Roota dashboard too.

---

## Components

| Component | What it does |
|---|---|
| `debugai.py` | CLI — analyze any log file locally, optional GitHub context, optional dashboard sync |
| `debugai_sdk.py` | Python SDK — auto-captures unhandled exceptions in your running app |
| `cpp_integration/debugai_handler.h` | C++ crash handler — auto-captures segfaults/crashes on Linux and Windows |
| `api.py` | FastAPI backend — powers the dashboard, incident storage, and diagnosis engine |
| `index.html` / `login.html` | Web dashboard — incident history, team accounts, analysis UI |

---

## Setting up the Python SDK

```python
import debugai_sdk

debugai_sdk.install(
    api_key="your_roota_api_key",   # required — get one by registering on the dashboard
    repo="your-org/your-repo"       # optional — enables source-aware diagnosis
)

# Your app code — any unhandled exception is now automatically captured,
# diagnosed, and (if configured) synced to your dashboard.
```

---

## Setting up the C++ crash handler

### Linux

```bash
g++ -g -o your_app your_app.cpp
```

Include the header and install the handler at startup:

```cpp
#include "debugai_handler.h"

int main() {
    debugai::install_crash_handler(".");  // output directory for crash reports
    // ... your app
}
```

**Requires `-g`** (debug symbols) for crash resolution to work. Without it, Roota can detect *that* a crash happened but can't tell you *where* in your source.

### Windows (MinGW-w64 only — MSVC not currently supported)

```bash
g++ -g -o your_app.exe your_app.cpp -Wl,--disable-dynamicbase
```

Same header, same `install_crash_handler()` call. Two flags are **required** on Windows:
- `-g` — debug symbols (same as Linux)
- `-Wl,--disable-dynamicbase` — disables ASLR. Without this, Windows randomizes your binary's load address on every run, and crash addresses won't resolve back to a source line.

### Resolving a captured crash

```bash
python crash_report.py
```

Auto-finds the newest crash report in the current directory, reads your `.roota.json` config, resolves the crash to an exact file/line, and prints the AI diagnosis.

**One-time config** — create `.roota.json` in your project:
```json
{
    "api_key": "your_roota_api_key",
    "repo": "your-org/your-repo",
    "server": "http://127.0.0.1:8000"
}
```

---

## Running the dashboard locally

```bash
pip install -r requirements.txt
python -m uvicorn api:app --reload
```

Visit `http://127.0.0.1:8000` to register an account and use the web dashboard.

**Environment setup** — create a `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key
SMTP_EMAIL=your_smtp_sender_email       # only needed for password reset
SMTP_APP_PASSWORD=your_gmail_app_password
```

---

## Project status

Roota is under active development. Currently working:
- CLI log analysis (local + synced)
- Python SDK auto-capture
- C++ crash handler (Linux + Windows)
- Web dashboard with auth, incident history, feedback
- Password reset via email

Planned:
- Google OAuth sign-in
- Deployment guide for production hosting
- PostgreSQL migration path (currently SQLite for MVP)

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

*(Add contribution guidelines once you're ready to accept PRs.)*