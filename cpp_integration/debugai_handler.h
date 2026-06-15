#ifndef DEBUGAI_HANDLER_H
#define DEBUGAI_HANDLER_H

#include <iostream>
#include <csignal>
#include <cstdlib>
#include <fstream>
#include <string>
#include <unistd.h>
#include <ucontext.h>

namespace debugai {

inline void crash_handler(int signum, siginfo_t* info, void* context) {
    std::ofstream log("crash_report.log");

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

inline void install_crash_handler() {
    struct sigaction sa;
    sa.sa_sigaction = crash_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, nullptr);
}

}

#endif