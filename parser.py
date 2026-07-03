import re
from rich.console import Console
from rich.table import Table

console = Console()

LOG_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(ERROR|WARNING|INFO|DEBUG)\s+\[(\w+)\]\s+(.*)'
)
FILE_PATTERN = re.compile(r'([\w\-/]+\.(?:py|cpp|c|h|hpp|js|ts|java|go|rb))')
FILE_FUNCTION_PATTERN = re.compile(
    r'([\w\-/]+\.(?:py|cpp|c|h|hpp|js|ts|java|go|rb)) line \d+, in (\w+)'
)
def extract_filenames(errors):
    filenames = set()

    for error in errors:
        matches = FILE_PATTERN.findall(error['message'])
        for match in matches:
            filenames.add(match)

    return list(filenames)     

def extract_file_function_map(errors):
    file_function_map = {}

    for error in errors:
        match = FILE_FUNCTION_PATTERN.search(error['message'])
        if match:
            filename = match.group(1)
            function_name = match.group(2)
            file_function_map[filename]=function_name

    return file_function_map
def parse_log_line(line):
    match = LOG_PATTERN.match(line.strip())
    if match:
        return {
            'timestamp': match.group(1),
            'level': match.group(2),
            'service': match.group(3),
            'message': match.group(4)
        }
    return None

def parse_log_file(filepath):
    entries = []
    errors = []
    warnings=[]

    with open(filepath, 'r', encoding ='utf-8') as f:
        for line in f:
            parsed = parse_log_line(line)
            if parsed:
                entries.append(parsed)
                if parsed['level'] == 'ERROR':
                    errors.append(parsed)
                elif parsed['level']=='WARNING':
                    warnings.append(parsed)
                    

    return entries, errors,warnings

def display_results(entries, errors,warnings):
    console.print(f"\n[bold]Total log lines parsed:[/bold] {len(entries)}")
    console.print(f"[bold red]Errors found:[/bold red] {len(errors)}\n")
    console.print(f"[bold red]Warnings found:[/bold red] {len(warnings)}\n")

    if errors:
        table = Table(title="Errors Detected")
        table.add_column("Time", style="cyan")
        table.add_column("Service", style="magenta")
        table.add_column("Message", style="red")

        for error in errors:
            table.add_row(error['timestamp'], error['service'], error['message'])

        console.print(table)
    if warnings:
        table = Table(title="Warnings Detected")
        table.add_column("Time", style="cyan")
        table.add_column("Service", style="magenta")
        table.add_column("Message", style="yellow")

        for warning in warnings:
            table.add_row(warning['timestamp'], warning['service'], warning['message'])

        console.print(table)
