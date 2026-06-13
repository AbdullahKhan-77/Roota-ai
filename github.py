import httpx
from rich.console import Console

console = Console()
def get_repo_file_tree(owner, repo, branch="main"):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

    response = httpx.get(url)

    if response.status_code == 200:
        data = response.json()
        paths = []
        for item in data["tree"]:
            paths.append(item["path"])
        return paths
    else:
        console.print(f"[bold red]Could not fetch repo tree (status {response.status_code})[/bold red]")
        return[]
def find_full_path(filename, all_paths):
    matches = [path for path in all_paths if path.endswith(filename)]

    if len(matches) == 0:
        return None

    if len(matches) == 1:
        return matches[0]

    # Multiple matches
    non_test_matches = [path for path in matches if 'test' not in path.lower()]

    if len(non_test_matches) == 1:
        return non_test_matches[0]

    console.print(f"[yellow]Warning: multiple files named '{filename}' found: {matches}. Using '{matches[0]}'[/yellow]")
    return matches[0]

def find_file_by_function(filename, function_name, all_paths, owner, repo_name,branch):
    candidates = [path for path in all_paths if path.endswith(filename)]

    if len(candidates) <= 1:
        return candidates[0] if candidates else None

    for path in candidates:
        content = fetch_file_from_github(owner, repo_name, path,branch)
        if content and f"def {function_name}" in content:
            return path

    console.print(f"[yellow]Warning: could not verify which '{filename}' contains '{function_name}'. Using '{candidates[0]}'[/yellow]")
    return candidates[0]


def fetch_file_from_github(owner, repo, filepath, branch="main"):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"

    response = httpx.get(url)

    if response.status_code == 200:
        return response.text
    else:
        console.print(f"[bold red]Could not fetch {filepath} (status {response.status_code})[/bold red]")
        return None
    
def get_default_branch(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"

    response = httpx.get(url)

    if response.status_code == 200:
        data = response.json()
        return data["default_branch"]
    else:
        console.print(f"[bold red]Could not fetch repo info (status {response.status_code})[/bold red]")
        return "main"

if __name__ == '__main__':
    branch = get_default_branch("AbdullahKhan-77", "demo-service")
    print(branch)