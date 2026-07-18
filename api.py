from fastapi import FastAPI, UploadFile, File, Form, Query,Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import tempfile
import os
import json
from database import save_incident, get_all_incidents, get_incident, init_db, save_feedback,create_user, get_user_by_api_key, get_user_incidents
from database import create_user, get_user_by_api_key, get_user_incidents, verify_user
from parser import parse_log_file, display_results, extract_filenames, extract_file_function_map
from ai import analyze_logs
from github import fetch_file_from_github, get_repo_file_tree, find_full_path, find_file_by_function, get_default_branch
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import sqlite3
import bcrypt
from database import DB_PATH
from database import set_reset_token, get_user_by_reset_token, clear_reset_token
from email_utils import send_reset_email

app = FastAPI(title="Roota API", version="0.1.0")

if os.path.isdir("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

init_db()
def get_current_user(x_api_key: str = Header(None)):
    if not x_api_key:
        return None
    return get_user_by_api_key(x_api_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return RedirectResponse(url="/home")

@app.get("/login")
def serve_login():
    return FileResponse("login.html")

@app.get("/home")
def serve_home():
    return FileResponse("landing.html")

@app.post("/analyze")
async def analyze(
    log_file: UploadFile = File(...),
    repo: Optional[str] = Form(None),
    x_api_key: str = Header(None) 
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user_id = user['id']
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.log', delete=False) as tmp:
        content = await log_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        entries, errors, warnings = parse_log_file(tmp_path)

        code_context = None

        if repo:
            filenames = extract_filenames(errors)
            repo = repo.strip().strip('/')
            parts = repo.split('/')
            if len(parts) != 2:
                raise HTTPException(status_code=400, detail="repo must be in 'owner/repo_name' format ")
            owner, repo_name = parts[0], parts[1]
            branch = get_default_branch(owner, repo_name)
            code_context = {}

            file_tree = get_repo_file_tree(owner, repo_name, branch)
            file_function_map = extract_file_function_map(errors)

            for filename in filenames:
                if filename in file_function_map:
                    function_name = file_function_map[filename]
                    full_path = find_file_by_function(filename, function_name, file_tree, owner, repo_name, branch)
                else:
                    full_path = find_full_path(filename, file_tree)
                if full_path:
                    file_content = fetch_file_from_github(owner, repo_name, full_path, branch)
                    if file_content:
                        code_context[filename] = file_content

        diagnosis = analyze_logs(entries, errors, warnings, code_context)

        with open(tmp_path, 'r', encoding='utf-8') as f:
            log_text = f.read()

        incident_id = save_incident(
            log_text=log_text,
            repo=repo,
            errors=errors,
            warnings=warnings,
            diagnosis=diagnosis,
            total_lines=len(entries),
            user_id=user_id
        )

        return {
            "status": "success",
            "incident_id": incident_id,
            "stats": {
                "total_lines": len(entries),
                "errors": len(errors),
                "warnings": len(warnings)
            },
            "errors": errors,
            "warnings": warnings,
            "diagnosis": diagnosis
        }
    finally:
        os.unlink(tmp_path)
        
@app.get("/incidents")
def list_incidents(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    incidents = get_user_incidents(user['id'])
    return {"incidents": incidents}

@app.get("/incidents/{incident_id}")
def get_incident_by_id(incident_id: int, x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident['user_id'] != user['id']:
        raise HTTPException(status_code=404, detail="Not found")
    incident['errors'] = json.loads(incident['errors'])
    incident['warnings'] = json.loads(incident['warnings'])
    return incident

@app.post("/incidents/{incident_id}/feedback")
def submit_feedback(incident_id: int, rating: str = Query(...), x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident['user_id'] != user['id']:
        raise HTTPException(status_code=404, detail="Not found")
    save_feedback(incident_id, rating)
    return {"status": "feedback saved", "incident_id": incident_id, "rating": rating}

@app.get("/ui")
def serve_ui():
    return FileResponse("index.html")

@app.post("/ingest")
async def ingest(data: dict, x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        log_text = data.get('log_text', '')
        repo = data.get('repo', None)
        source = data.get('source', 'sdk')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', 
                                         delete=False, encoding='utf-8') as tmp:
            tmp.write(log_text)
            tmp_path = tmp.name

        entries, errors, warnings = parse_log_file(tmp_path)

        code_context = None
        if repo and errors:
            filenames = extract_filenames(errors)
            repo = repo.strip().strip('/')
            parts = repo.split('/')
            if len(parts) != 2:
                raise HTTPException(status_code=400, detail="repo must be in 'owner/repo_name' format")
            owner, repo_name = parts[0], parts[1]
            branch = get_default_branch(owner, repo_name)
            code_context = {}
            file_tree = get_repo_file_tree(owner, repo_name, branch)
            file_function_map = extract_file_function_map(errors)

            for filename in filenames:
                if filename in file_function_map:
                    function_name = file_function_map[filename]
                    full_path = find_file_by_function(filename, function_name, file_tree, owner, repo_name, branch)
                else:
                    full_path = find_full_path(filename, file_tree)
                if full_path:
                    file_content = fetch_file_from_github(owner, repo_name, full_path, branch)
                    if file_content:
                        code_context[filename] = file_content

        diagnosis = analyze_logs(entries, errors, warnings, code_context)

        incident_id = save_incident(
            log_text=log_text,
            repo=repo,
            errors=errors,
            warnings=warnings,
            diagnosis=diagnosis,
            total_lines=len(entries),
            user_id=user['id']
        )

        os.unlink(tmp_path)

        return {
            "status": "success",
            "incident_id": incident_id,
            "source": source,
            "errors_found": len(errors),
            "diagnosis": diagnosis
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": f"server-side analysis failed: {e}"}
    
@app.post("/register")
def register(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    result = create_user(name, username, email, password)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "status": "success",
        "email": result["email"],
        "username": result["username"],
        "api_key": result["api_key"]
    }

@app.post("/login")
def login(login: str = Form(...), password: str = Form(...)):
    user = verify_user(login, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    return {
        "status": "success",
        "email": user["email"],
        "username": user["username"],
        "api_key": user["api_key"]
    }
    
@app.get("/docs-page")
def serve_docs():
    return FileResponse("docs.html")

@app.get("/pricing")
def serve_pricing():
    return FileResponse("pricing.html")

@app.get("/changelog")
def serve_changelog():
    return FileResponse("changelog.html")

@app.get("/privacy")
def serve_privacy():
    return FileResponse("privacy.html")

@app.get("/terms")
def serve_terms():
    return FileResponse("terms.html")

@app.get("/reset-password")
def serve_reset_password():
    return FileResponse("reset_password.html")

@app.post("/change-password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    x_api_key: Optional[str] = Header(None)
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/waitlist")
def join_waitlist(email: str = Form(...)):
    email = email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1] or len(email) > 254:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('INSERT OR IGNORE INTO waitlist (email) VALUES (?)', (email,))
        conn.commit()
    finally:
        conn.close()
    return {"status": "success"}


@app.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    token = set_reset_token(email)
    if token:
        try:
            send_reset_email(email, token)
        except Exception as e:
            print(f"Failed to send reset email: {e}")
    return {"status": "success", "message": "If that email is registered, a reset link has been sent."}


@app.post("/reset-password")
def reset_password(token: str = Form(...), new_password: str = Form(...)):
    user = get_user_by_reset_token(token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Please request a new one.")

    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
    conn.commit()
    conn.close()

    clear_reset_token(user['id'])
    return {"status": "success"}