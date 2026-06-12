import httpx
from rich.console import Console

console = Console()


def fetch_file_from_github(owner, repo, filepath, branch="main"):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"

    response = httpx.get(url)

    if response.status_code == 200:
        return response.text
    else:
        console.print(f"[bold red]Could not fetch {filepath} (status {response.status_code})[/bold red]")
        return None
    
if __name__ == '__main__':
    content = fetch_file_from_github("AbdullahKhan-77", "demo-service", "user_session.py")
    if content:
        print(content)
        