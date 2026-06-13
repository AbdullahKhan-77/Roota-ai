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
    for path in all_paths:
        if path.endswith(filename):
            return path
    return None

def fetch_file_from_github(owner, repo, filepath, branch="main"):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"

    response = httpx.get(url)

    if response.status_code == 200:
        return response.text
    else:
        console.print(f"[bold red]Could not fetch {filepath} (status {response.status_code})[/bold red]")
        return None
    
if __name__ == '__main__':
    paths = get_repo_file_tree("AbdullahKhan-77", "demo-service")
    full_path = find_full_path("user_session.py", paths)
    print(full_path)
        