from google import genai
import os
from dotenv import load_dotenv
from rich.console import Console
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
console = Console()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_logs(entries, errors, warnings, code_context=None):
    if not errors and not warnings:
        console.print("[green]No errors or warnings found. System looks healthy.[/green]")
        return

    error_text = ""
    for e in errors:
        error_text += f"[{e['timestamp']}] {e['service']}: {e['message']}\n"

    warning_text = ""
    for w in warnings:
        warning_text += f"[{w['timestamp']}] {w['service']}: {w['message']}\n"
        
    code_text = ""
    if code_context:
        for filename, content in code_context.items():
            code_text += f"\n=== {filename} ===\n{content}\n"

    prompt =f"""You are an expert production debugger with 15 years of experience in distributed systems.

Analyze these production logs carefully. Multiple services may be involved.

ERRORS:
{error_text}

WARNINGS:
{warning_text}

RELEVANT SOURCE CODE:
{code_text}

Provide your analysis in exactly this structure:

INCIDENT SUMMARY:
One sentence describing what happened overall.

TIMELINE:
Reconstruct the sequence of events in chronological order based on timestamps.

ROOT CAUSE:
The single most likely root cause. Be specific. Name the service, the type of failure, and why it happened.

CASCADING EFFECTS:
Which other services were affected as a result and how.

FIX:
The single most important thing to fix first. If source code was provided above,
reference the EXACT variable names, function names, and line numbers from that code. 
Show the exact line that causes the problem and the exact corrected line.

CONFIDENCE: X/10
How confident you are in this diagnosis and why."""

    console.print("\n[bold yellow]Sending logs to AI for analysis...[/bold yellow]\n")

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    console.print("[bold green]AI Diagnosis:[/bold green]\n")
    print(response.text)