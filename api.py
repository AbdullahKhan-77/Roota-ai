from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import tempfile
import os
import json
from database import save_incident, get_all_incidents, get_incident, init_db, save_feedback

from parser import parse_log_file, display_results, extract_filenames, extract_file_function_map
from ai import analyze_logs
from github import fetch_file_from_github, get_repo_file_tree, find_full_path, find_file_by_function, get_default_branch
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI(title="debugai API", version="0.1.0")

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"message": "debugai API is running", "version": "0.1.0"}

@app.post("/analyze")
async def analyze(
    log_file: UploadFile = File(...),
    repo: Optional[str] = Form(None)
):
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
            total_lines=len(entries)
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
def list_incidents():
    incidents = get_all_incidents()
    return {"incidents": incidents}


@app.get("/incidents/{incident_id}")
def get_incident_by_id(incident_id: int):
    incident = get_incident(incident_id)
    if not incident:
        return {"error": "Incident not found"}
    incident['errors'] = json.loads(incident['errors'])
    incident['warnings'] = json.loads(incident['warnings'])
    return incident

@app.post("/incidents/{incident_id}/feedback")
def submit_feedback(incident_id: int, rating: str = Query(...)):
    save_feedback(incident_id, rating)
    return {"status": "feedback saved", "incident_id": incident_id, "rating": rating}

@app.get("/ui")
def serve_ui():
    return FileResponse("index.html")

@app.post("/ingest")
async def ingest(data: dict):
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
            owner, repo_name = repo.split('/')
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
            total_lines=len(entries)
        )

        os.unlink(tmp_path)

        return {
            "status": "success",
            "incident_id": incident_id,
            "source": source,
            "errors_found": len(errors)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}