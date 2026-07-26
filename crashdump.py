import subprocess
import re
import httpx
import time

BASE_MAP_PATTERN = re.compile(r'BASE_MAP:\s+([0-9a-f]+)(?:-[0-9a-f]+.*?)?\s{2,}(.+)$')
SIGNAL_PATTERN = re.compile(r'SIGNAL:\s+(-?\d+)')
CRASH_ADDRESS_PATTERN = re.compile(r'CRASH_ADDRESS:\s+(0x[0-9a-f]+)')
TIMESTAMP_PATTERN = re.compile(r'TIMESTAMP:\s+(\d+)')

SIGNAL_NAMES = {
    11: "SIGSEGV",
    6: "SIGABRT",
    8: "SIGFPE",
    4: "SIGILL",
    7: "SIGBUS",
    -1073741819: "EXCEPTION_ACCESS_VIOLATION",
    -1073741676: "EXCEPTION_INT_DIVIDE_BY_ZERO",
    -1073741795: "EXCEPTION_ILLEGAL_INSTRUCTION",
    -1073741571: "EXCEPTION_STACK_OVERFLOW",
    -2147483645: "EXCEPTION_BREAKPOINT"
}

def parse_crash_report(filepath):
    result = {}

    with open(filepath, 'r') as f:
        for line in f:
            base_match = BASE_MAP_PATTERN.search(line)
            if base_match:
                result['base_address'] = int(base_match.group(1), 16)
                result['binary_path'] = base_match.group(2)

            signal_match = SIGNAL_PATTERN.search(line)
            if signal_match:
                result['signal'] = int(signal_match.group(1))

            crash_match = CRASH_ADDRESS_PATTERN.search(line)
            if crash_match:
                result['crash_address'] = int(crash_match.group(1), 16)

            timestamp_match = TIMESTAMP_PATTERN.search(line)
            if timestamp_match:
                result['timestamp'] = int(timestamp_match.group(1))

    return result


def calculate_file_offset(crash_address, base_address):
    return crash_address - base_address

def resolve_address(binary_path, address_or_offset, is_windows=False):
    if is_windows:
        result = subprocess.run(
            ["addr2line", "-e", binary_path, hex(address_or_offset)],
            capture_output=True,
            text=True
        )
    else:
        result = subprocess.run(
            ["wsl", "addr2line", "-e", binary_path, hex(address_or_offset)],
            capture_output=True,
            text=True
        )
    return result.stdout.strip()

def diagnose_crash(binary_path, crash_address, base_address):
    is_windows = binary_path.lower().endswith('.exe')

    if is_windows:
        location = resolve_address(binary_path, crash_address, is_windows=True)
    else:
        file_offset = calculate_file_offset(crash_address, base_address)
        location = resolve_address(binary_path, file_offset, is_windows=False)

    if location.startswith("??"):
        if is_windows:
            raise RuntimeError(
                f"Could not resolve crash location for '{binary_path}'. This usually means one of two things: "
                f"(1) the binary was compiled without debug symbols — recompile with -g, or "
                f"(2) ASLR randomized the load address — recompile with the linker flag "
                f"-Wl,--disable-dynamicbase so addresses stay predictable. "
                f"See the Windows setup guide in the README for details."
            )
        else:
            raise RuntimeError(
                f"Could not resolve crash location — '{binary_path}' appears to be missing debug symbols. "
                f"Recompile with the -g flag (e.g. g++ -g -o your_app your_app.cpp) and try again."
            )

    return location

def diagnose_from_report(report_path):
    report = parse_crash_report(report_path)

    location = diagnose_crash(
        binary_path=report['binary_path'],
        crash_address=report['crash_address'],
        base_address=report['base_address']
    )

    return location


def extract_file_and_line(location_string):
    path_part, line_part = location_string.rsplit(':', 1)
    line_number = int(line_part)

    filename = path_part.split('/')[-1]

    return filename, line_number


def format_crash_as_log(report, filename, line_number):
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['timestamp']))
    sig_name = SIGNAL_NAMES.get(report['signal'], f"SIGNAL_{report['signal']}")

    lines = []
    lines.append(f"{ts} ERROR [CppAutoCapture] Unhandled signal: {sig_name}")
    lines.append(f"{ts} ERROR [CppAutoCapture] Traceback: {filename} line {line_number}, in <unknown>")
    lines.append(f"{ts} ERROR [CppAutoCapture] Crash address: {hex(report['crash_address'])}")

    return "\n".join(lines)


def send_to_ingest(log_text, api_key, repo=None, server="https://tryroota.dev"):
    response = httpx.post(
        f"{server}/ingest",
        json={
            "log_text": log_text,
            "repo": repo,
            "source": "cpp_sdk"
        },
        headers={"X-API-Key": api_key},
        timeout=30
    )
    return response.json()

def report_crash(report_path, api_key, repo=None, server="https://tryroota.dev"):
    report = parse_crash_report(report_path)

    try:
        location = diagnose_crash(
            binary_path=report['binary_path'],
            crash_address=report['crash_address'],
            base_address=report['base_address']
        )
    except RuntimeError as e:
        print(f"[debugai-cpp] {e}")
        return

    filename, line_number = extract_file_and_line(location)
    log_text = format_crash_as_log(report, filename, line_number)

    print(f"[debugai-cpp] Capturing crash and sending for analysis...")
    try:
        data = send_to_ingest(log_text, api_key, repo, server)
        if data.get("status") == "success":
            print(f"[debugai-cpp] Incident #{data['incident_id']} captured.")
            if data.get("diagnosis"):
                print(f"\n{'='*60}")
                print("[debugai-cpp] DIAGNOSIS")
                print(f"{'='*60}")
                print(data["diagnosis"])
                print(f"{'='*60}\n")
            print(f"[debugai-cpp] View full incident at {server}/ui")
        else:
            print(f"[debugai-cpp] Capture failed: {data.get('message', 'unknown error')}")
    except Exception as e:
        print(f"[debugai-cpp] Could not send crash report: {e}")
        
if __name__ == '__main__':
    location = diagnose_from_report("cpp_integration/crash_report.log")
    filename, line_number = extract_file_and_line(location)
    print(filename, line_number)