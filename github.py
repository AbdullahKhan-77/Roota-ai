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
        