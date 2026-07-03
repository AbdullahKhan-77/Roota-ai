from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import tempfile
import os

from parser import parse_log_file, display_results, extract_filenames, extract_file_function_map
from ai import analyze_logs
from github import fetch_file_from_github, get_repo_file_tree, find_full_path, find_file_by_function, get_default_branch

app = FastAPI(title="debugai API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

        return {
            "status": "success",
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