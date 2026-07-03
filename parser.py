import re
from rich.console import Console
from rich.table import Table
from google import genai
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


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
    warnings = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            parsed = parse_log_line(line)
            if parsed:
                entries.append(parsed)
                if parsed['level'] == 'ERROR':
                    errors.append(parsed)
                elif parsed['level'] == 'WARNING':
                    warnings.append(parsed)

    if len(entries) < 2:
        console.print("[dim]Regex parser found few matches — trying AI-powered format detection...[/dim]")
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        return ai_parse_log(raw_text)

    return entries, errors, warnings

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
        
def ai_parse_log(raw_text):
    prompt = f"""You are a log parsing expert. Extract all log entries from the following log text.
The log may be in ANY format - structured, JSON, plain text, Python tracebacks, Node.js errors, etc.

For each log entry you find, extract:
- timestamp (best guess if not explicit, use empty string if none)
- level (ERROR, WARNING, INFO, or DEBUG - infer from context if not explicit)
- service (service/component name if present, use 'Unknown' if not)
- message (the actual error/warning message)

Return ONLY a JSON array with no markdown, no explanation, no backticks. Example:
[
  {{"timestamp": "2024-03-10 14:22:01", "level": "ERROR", "service": "UserService", "message": "KeyError: 9981"}},
  {{"timestamp": "", "level": "WARNING", "service": "Unknown", "message": "Memory usage high"}}
]

LOG TEXT:
{raw_text}"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    raw = response.text.strip()
    raw = raw.replace('```json', '').replace('```', '').strip()

    parsed = json.loads(raw)

    entries = []
    errors = []
    warnings = []

    for item in parsed:
        entry = {
            'timestamp': item.get('timestamp', ''),
            'level': item.get('level', 'INFO').upper(),
            'service': item.get('service', 'Unknown'),
            'message': item.get('message', '')
        }
        entries.append(entry)
        if entry['level'] == 'ERROR':
            errors.append(entry)
        elif entry['level'] == 'WARNING':
            warnings.append(entry)

    return entries, errors, warnings
