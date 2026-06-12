import click
from parser import parse_log_file, display_results
from ai import analyze_logs
import os 
from rich.console import Console

console=Console()

@click.command()
@click.option('--log', required=True, help='Path to the log file to analyze')
def main(log):
    if os.path.exists(log):
        entries, errors, warnings = parse_log_file(log)
        display_results(entries, errors, warnings)
        analyze_logs(entries, errors, warnings)
    else:
        console.print(f"[bold red]File '{log}' doesnt exist[/bold red]")
        raise click.Abort()

if __name__ == '__main__':
    main()