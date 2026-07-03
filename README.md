# debugai

> AI-powered production log analyzer that connects crash logs to your actual source code and delivers exact root causes, timelines, and fixes — automatically.

---

## The Problem

When a production system crashes, engineers spend hours hunting through logs, grepping stack traces, and manually cross-referencing source code. Existing tools tell you **what** broke. They never tell you **why** or **how to fix it**.

debugai closes that gap.

---

## What It Does

Given a log file and a GitHub repository, debugai:

1. Parses and structures all errors and warnings from your log
2. Extracts which source files are mentioned in the crash
3. Fetches the actual source code from your GitHub repo (any branch, any folder structure)
4. Sends logs + real source code to an AI for grounded analysis
5. Returns an exact diagnosis: root cause, timeline, cascading effects, and a specific code fix with exact line numbers and variable names

For C++ applications, debugai also resolves raw memory addresses to exact source lines using a lightweight drop-in crash handler — no debugger required.

---

## Installation

```bash
git clone https://github.com/AbdullahKhan-77/debugai.git
cd debugai
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install click httpx rich python-dotenv google-genai
```

Create a `.env` file in the project root:

GEMINI_API_KEY=your_key_here
---

## Usage

### Basic log analysis

```bash
python debugai.py --log crash.log
```

### With GitHub source code (recommended)

```bash
python debugai.py --log crash.log --repo owner/repo-name
```

When `--repo` is provided, debugai automatically:
- Fetches the full file tree of the repository
- Identifies which files are involved in the crash
- Disambiguates between files with the same name using function-name verification
- Detects the correct default branch automatically (main, master, develop, etc.)

### C++ crash report analysis

```bash
python debugai.py --log crash.log --repo owner/repo-name --crash-report path/to/crash_report.log
```

---

## Example Output
``` bash
debugai v0.1.0 — AI-powered production debugger
Errors Detected
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Time                ┃ Service     ┃ Message                                           ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 2024-03-10 14:22:01 │ UserService │ KeyError: 9981                                    │
│ 2024-03-10 14:22:01 │ UserService │ Traceback: user_session.py line 6, in get_session │
│ 2024-03-10 14:22:01 │ UserService │ Unhandled exception, request failed with 500      │
└─────────────────────┴─────────────┴───────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analyzing with AI...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT SUMMARY:
The UserService crashed when accessing a non-existent session key for user 9981.
TIMELINE:

[14:22:01] UserService receives request for user_id 9981
[14:22:01] get_session() called — key missing from active_sessions dict
[14:22:01] Unhandled KeyError — returns 500 to client

ROOT CAUSE:
get_session() in user_session.py performs a direct dictionary lookup without
validating key existence, crashing when a session has expired or never existed.
FIX:
File: user_session.py, Line 6
Before: return self.active_sessions[user_id]
After:  return self.active_sessions.get(user_id)
CONFIDENCE: 10/10
```

## C++ Crash Handler

For C++ applications, debugai includes a header-only crash handler that automatically captures crash addresses, memory maps, and signal information — with no debugger required.

### Setup (one time)

Copy `cpp_integration/debugai_handler.h` into your C++ project. Then add two lines:

```cpp
#include "debugai_handler.h"

int main() {
    debugai::install_crash_handler("logs/");  // output directory (optional, defaults to ".")
    // ... rest of your code
}
```

### What happens when your app crashes

A timestamped crash report is written automatically:
logs/crash_report_20260615_143022.log

Containing:
```bash
BASE_MAP: 60b82188b000-60b82188d000 r--p ... /path/to/your/binary
SIGNAL: 11
CRASH_ADDRESS: 0x60b82188d451
```
### Analyzing the crash

```bash
python debugai.py --log service.log --repo owner/repo --crash-report logs/crash_report_20260615_143022.log
```

debugai resolves the memory address to an exact source line using `addr2line` (requires WSL on Windows or Linux), fetches the source file from GitHub, and produces a grounded diagnosis with **CONFIDENCE: 10/10** — because the crash location is mathematically verified, not guessed.

---

## How File Disambiguation Works

Real codebases have files with the same name in different folders (e.g., `src/services/user_session.py` and `tests/user_session.py`). debugai uses a three-stage disambiguation pipeline:

1. **Filename match** — find all files matching the name from the log
2. **Test file filter** — prefer non-test paths for production crash analysis  
3. **Function verification** — fetch candidate files and check which one actually contains the function named in the traceback

This guarantees the AI analyzes the **correct** file, not a coincidental name match.

---

## Supported Log Formats

- Structured plain text logs: `TIMESTAMP LEVEL [SERVICE] MESSAGE`
- Python tracebacks with file and function references
- C++ crash reports generated by `debugai_handler.h`

---

## Project Structure
```bash
debugai/
├── debugai.py            # CLI entry point (click-based)
├── parser.py             # Log parsing, error/warning extraction, filename/function detection
├── ai.py                 # AI analysis via Gemini API with structured prompt engineering
├── github.py             # GitHub source fetching, file tree navigation, disambiguation
├── crashdump.py          # C++ crash address resolution via WSL addr2line
├── cpp_integration/
│   ├── debugai_handler.h # Drop-in C++ crash handler (header-only, binary-agnostic)
│   └── crash_reports/    # Example crash report output
├── .env                  # API keys (never committed)
└── .gitignore
```

## Requirements

- Python 3.11+
- WSL (Windows Subsystem for Linux) — required for C++ crash address resolution on Windows
- A Gemini API key (free tier available at aistudio.google.com)
- g++ with debug symbols (`-g` flag) for C++ crash analysis

---

## Roadmap

- [ ] Web UI — paste logs in browser, get diagnosis without CLI
- [ ] Sentry integration — auto-analyze errors as they fire
- [ ] Support for private GitHub repos (token-based auth)
- [ ] FastAPI backend for team/shared usage
- [ ] Fine-tuning on accumulated incident data

---

## Built by

Abdullah Khan — Lahore, Pakistan  
Building the AI-native production debugger for C++ and distributed systems.
