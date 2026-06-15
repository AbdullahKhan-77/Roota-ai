#ifndef DEBUGAI_HANDLER_H
#define DEBUGAI_HANDLER_H

#include <iostream>
#include <csignal>
#include <cstdlib>
#include <fstream>
#include <string>
#include <ctime>
#include <unistd.h>
#include <ucontext.h>

namespace debugai {

inline std::string g_output_dir = ".";

inline std::string get_timestamp() {
    std::time_t now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", std::localtime(&now));
    return std::string(buf);
}

inline void crash_handler(int signum, siginfo_t* info, void* context) {
    std::string filename = g_output_dir + "/crash_report_" + get_timestamp() + ".log";
    std::ofstream log(filename);

    char exe_path[1024];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
    } else {
        exe_path[0] = '\0';
    }

    ucontext_t* ctx = (ucontext_t*)context;
    unsigned long long rip = ctx->uc_mcontext.gregs[REG_RIP];

    std::ifstream maps("/proc/self/maps");
    std::string line;
    while (std::getline(maps, line)) {
        if (line.find(exe_path) != std::string::npos) {
            log << "BASE_MAP: " << line << std::endl;
            break;
        }
    }

    log << "SIGNAL: " << signum << std::endl;
    log << "CRASH_ADDRESS: 0x" << std::hex << rip << std::endl;
    log.close();

    std::_Exit(1);
}

inline void install_crash_handler(const std::string& output_dir = ".") {
    g_output_dir = output_dir;

    struct sigaction sa;
    sa.sa_sigaction = crash_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, nullptr);
}

}

#endif