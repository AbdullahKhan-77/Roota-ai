#ifndef DEBUGAI_HANDLER_H
#define DEBUGAI_HANDLER_H

#ifdef _WIN32
#include <windows.h>
#include <dbghelp.h>
#include<ctime>

namespace debugai {

inline char g_output_dir_win[512] = ".";

inline void win_write_str(HANDLE h, const char* s) {
    DWORD written;
    DWORD len = 0;
    while (s[len]) len++;
    WriteFile(h, s, len, &written, nullptr);
}

inline void win_write_hex(HANDLE h, unsigned long long val) {
    char buf[20];
    int i = 18;
    buf[19] = '\0';
    if (val == 0) {
        buf[i--] = '0';
    }
    while (val > 0 && i >= 0) {
        int digit = val & 0xF;
        buf[i--] = (digit < 10) ? ('0' + digit) : ('a' + digit - 10);
        val >>= 4;
    }
    win_write_str(h, &buf[i + 1]);
}

inline void win_write_int(HANDLE h, long val) {
    char buf[24];
    int i = 22;
    buf[23] = '\0';
    if (val == 0) {
        buf[i--] = '0';
    }
    bool neg = val < 0;
    unsigned long uval = neg ? -val : val;
    while (uval > 0 && i >= 0) {
        buf[i--] = '0' + (uval % 10);
        uval /= 10;
    }
    if (neg) buf[i--] = '-';
    win_write_str(h, &buf[i + 1]);
}

inline LONG WINAPI crash_handler_win(EXCEPTION_POINTERS* pExceptionInfo) {
    time_t now = time(nullptr);

    char filename[600];
    int n = 0;
    const char* dir = g_output_dir_win;
    while (*dir && n < 500) filename[n++] = *dir++;

    const char* prefix = "\\crash_report_";
    const char* p = prefix;
    while (*p && n < 550) filename[n++] = *p++;

    {
        char numbuf[24];
        int ni = 22;
        numbuf[23] = '\0';
        unsigned long val = (unsigned long)now;
        if (val == 0) numbuf[ni--] = '0';
        while (val > 0 && ni >= 0) {
            numbuf[ni--] = '0' + (val % 10);
            val /= 10;
        }
        const char* numstart = &numbuf[ni + 1];
        while (*numstart && n < 590) filename[n++] = *numstart++;
    }

    const char* suffix = ".log";
    const char* s = suffix;
    while (*s && n < 599) filename[n++] = *s++;
    filename[n] = '\0';

    HANDLE hFile = CreateFileA(
        filename, GENERIC_WRITE, 0, nullptr,
        CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr
    );

    if (hFile == INVALID_HANDLE_VALUE) {
        return EXCEPTION_EXECUTE_HANDLER;
    }

    char exe_path[1024];
    DWORD len = GetModuleFileNameA(nullptr, exe_path, sizeof(exe_path));
    if (len == 0) {
        exe_path[0] = '\0';
    }

    HMODULE hModule = nullptr;
    GetModuleHandleExA(0, nullptr, &hModule);
    unsigned long long base_address = (unsigned long long)hModule;

    win_write_str(hFile, "BASE_MAP: ");
    win_write_hex(hFile, base_address);
    win_write_str(hFile, "  ");
    win_write_str(hFile, exe_path);
    win_write_str(hFile, "\n");

    DWORD exception_code = pExceptionInfo->ExceptionRecord->ExceptionCode;
    win_write_str(hFile, "SIGNAL: ");
    win_write_int(hFile, (long)exception_code);
    win_write_str(hFile, "\n");

#if defined(_M_X64) || defined(__x86_64__)
    unsigned long long rip = pExceptionInfo->ContextRecord->Rip;
#else
    unsigned long long rip = pExceptionInfo->ContextRecord->Eip;
#endif

    win_write_str(hFile, "CRASH_ADDRESS: 0x");
    win_write_hex(hFile, rip);
    win_write_str(hFile, "\n");

    win_write_str(hFile, "TIMESTAMP: ");
    win_write_int(hFile, (long)now);
    win_write_str(hFile, "\n");

    CloseHandle(hFile);

    return EXCEPTION_EXECUTE_HANDLER;
}

inline void install_crash_handler(const char* output_dir = ".") {
    size_t i = 0;
    while (output_dir[i] && i < sizeof(g_output_dir_win) - 1) {
        g_output_dir_win[i] = output_dir[i];
        i++;
    }
    g_output_dir_win[i] = '\0';

    SetUnhandledExceptionFilter(crash_handler_win);
}

}
#else
   
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fcntl.h>
#include <unistd.h>
#include <ucontext.h>

namespace debugai {

inline char g_output_dir[512] = ".";

inline void write_str(int fd, const char* s) {
    write(fd, s, strlen(s));
}

inline void write_hex(int fd, unsigned long long val) {
    char buf[20];
    int i = 18;
    buf[19] = '\0';
    if (val == 0) {
        buf[i--] = '0';
    }
    while (val > 0 && i >= 0) {
        int digit = val & 0xF;
        buf[i--] = (digit < 10) ? ('0' + digit) : ('a' + digit - 10);
        val >>= 4;
    }
    write_str(fd, &buf[i + 1]);
}

inline void write_int(int fd, long val) {
    char buf[24];
    int i = 22;
    buf[23] = '\0';
    if (val == 0) {
        buf[i--] = '0';
    }
    bool neg = val < 0;
    unsigned long uval = neg ? -val : val;
    while (uval > 0 && i >= 0) {
        buf[i--] = '0' + (uval % 10);
        uval /= 10;
    }
    if (neg) buf[i--] = '-';
    write_str(fd, &buf[i + 1]);
}

inline void crash_handler(int signum, siginfo_t* info, void* context) {
time_t now = time(nullptr);

    char filename[600];
    int n = 0;
    const char* dir = g_output_dir;
    while (*dir && n < 500) filename[n++] = *dir++;

    const char* prefix = "/crash_report_";
    const char* p = prefix;
    while (*p && n < 550) filename[n++] = *p++;

    // manually convert epoch seconds to digits, written directly into filename[]
    {
        char numbuf[24];
        int ni = 22;
        numbuf[23] = '\0';
        unsigned long val = (unsigned long)now;
        if (val == 0) numbuf[ni--] = '0';
        while (val > 0 && ni >= 0) {
            numbuf[ni--] = '0' + (val % 10);
            val /= 10;
        }
        const char* numstart = &numbuf[ni + 1];
        while (*numstart && n < 590) filename[n++] = *numstart++;
    }

    const char* suffix = ".log";
    const char* s = suffix;
    while (*s && n < 599) filename[n++] = *s++;
    filename[n] = '\0';

    int fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        std::_Exit(1);
    }

    char exe_path[1024];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
    } else {
        exe_path[0] = '\0';
    }

    ucontext_t* ctx = (ucontext_t*)context;
    unsigned long long rip = ctx->uc_mcontext.gregs[REG_RIP];

 int maps_fd = open("/proc/self/maps", O_RDONLY);
    if (maps_fd >= 0) {
        char buf[4096];
        char line[512];
        int line_len = 0;
        bool found = false;
        ssize_t r;
        while (!found && (r = read(maps_fd, buf, sizeof(buf))) > 0) {
            for (ssize_t i = 0; i < r && !found; i++) {
                if (buf[i] == '\n') {
                    line[line_len] = '\0';
                    bool match = false;
                    if (exe_path[0] != '\0') {
                        const char* p = line;
                        while (*p) {
                            const char* a = p;
                            const char* b = exe_path;
                            while (*a && *b && *a == *b) { a++; b++; }
                            if (*b == '\0') { match = true; break; }
                            p++;
                        }
                    }
                    if (match) {
                        write_str(fd, "BASE_MAP: ");
                        write(fd, line, line_len);
                        write_str(fd, "\n");
                        found = true;
                    }
                    line_len = 0;
                } else if (line_len < 511) {
                    line[line_len++] = buf[i];
                }
            }
        }
        close(maps_fd);
    }

    write_str(fd, "SIGNAL: ");
    write_int(fd, signum);
    write_str(fd, "\n");

    write_str(fd, "CRASH_ADDRESS: 0x");
    write_hex(fd, rip);
    write_str(fd, "\n");

    write_str(fd, "TIMESTAMP: ");
    write_int(fd, (long)now);
    write_str(fd, "\n");

    close(fd);
    std::_Exit(1);
}

inline void install_crash_handler(const char* output_dir = ".") {
    size_t i = 0;
    while (output_dir[i] && i < sizeof(g_output_dir) - 1) {
        g_output_dir[i] = output_dir[i];
        i++;
    }
    g_output_dir[i] = '\0';

    struct sigaction sa;
    sa.sa_sigaction = crash_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);

    sigaction(SIGSEGV, &sa, nullptr);
    sigaction(SIGABRT, &sa, nullptr);
    sigaction(SIGFPE, &sa, nullptr);
    sigaction(SIGILL, &sa, nullptr);
    sigaction(SIGBUS, &sa, nullptr);
}

}
#endif

#endif