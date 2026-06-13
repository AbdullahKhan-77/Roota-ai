import click
from parser import parse_log_file, display_results, extract_filenames, extract_file_function_map
from github import fetch_file_from_github, get_repo_file_tree, find_full_path, find_file_by_function
from ai import analyze_logs
import os 
from rich.console import Console

console=Console()

@click.command()
@click.option('--log', required=True, help='Path to the log file to analyze')
@click.option('--repo', required=False, help='GitHub repo in format owner/repo, e.g. AbdullahKhan-77/demo-service')
def main(log,repo):
    if os.path.exists(log):
        entries, errors, warnings = parse_log_file(log)
        display_results(entries, errors, warnings)
        code_context = None

        if repo:
            filenames = extract_filenames(errors)
            owner, repo_name = repo.split('/')
            code_context = {}
            
            file_tree=get_repo_file_tree(owner,repo_name)
            file_function_map = extract_file_function_map(errors)

            for filename in filenames:
                if filename in file_function_map:
                    function_name=file_function_map[filename]
                    full_path=find_file_by_function(filename,function_name,file_tree,owner,repo_name)
                else:
                    full_path=find_full_path(filename,file_tree)
                if full_path:
                    content = fetch_file_from_github(owner, repo_name, full_path)
                    if content:
                        code_context[filename]=content

        analyze_logs(entries, errors, warnings, code_context)
        
    else:
        console.print(f"[bold red]File '{log}' doesnt exist[/bold red]")
        raise click.Abort()

if __name__ == '__main__':
    main()
    