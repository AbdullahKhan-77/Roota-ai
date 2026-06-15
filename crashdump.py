import subprocess
import re
BASE_MAP_PATTERN = re.compile(r'BASE_MAP:\s+([0-9a-f]+)-[0-9a-f]+.*\s{2,}(.+)$')
SIGNAL_PATTERN = re.compile(r'SIGNAL:\s+(\d+)')
CRASH_ADDRESS_PATTERN = re.compile(r'CRASH_ADDRESS:\s+(0x[0-9a-f]+)')

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
                result['crash_address']=int(crash_match.group(1),16)

    return result

def calculate_file_offset(crash_address, base_address):
    return crash_address - base_address


def resolve_address(binary_path, file_offset):
    hex_offset = hex(file_offset)

    result = subprocess.run(
        ["wsl", "addr2line", "-e", binary_path, hex_offset],
        capture_output=True,
        text=True
    )

    output = result.stdout.strip()
    return output


def diagnose_crash(binary_path, crash_address, base_address):
    file_offset = calculate_file_offset(crash_address, base_address)
    location = resolve_address(binary_path, file_offset)
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

    
if __name__ == '__main__':
    location = diagnose_from_report("cpp_integration/crash_report.log")
    filename, line_number = extract_file_and_line(location)
    print(filename, line_number)