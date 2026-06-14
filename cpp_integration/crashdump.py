import subprocess


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
if __name__ == '__main__':
    result = diagnose_crash(
        binary_path="/mnt/c/Users/ABDULLAH KHAN/Desktop/cpp-crash-demo/crash_pie",
        crash_address=0x00005555555551cc,
        base_address=0x0000555555554000
    )
    print(result)