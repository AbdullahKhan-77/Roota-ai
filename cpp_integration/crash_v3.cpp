#include <iostream>
#include <csignal>
#include <cstdlib>
#include <fstream>
#include <ucontext.h>

void crash_handler(int signum, siginfo_t* info, void* context) {
    std::ofstream log("crash_report.log");

    ucontext_t* ctx = (ucontext_t*)context;
    unsigned long long rip = ctx->uc_mcontext.gregs[REG_RIP];

    std::ifstream maps("/proc/self/maps");
    std::string line;
    while (std::getline(maps, line)) {
        if (line.find("crash_pie_v3") != std::string::npos) {
            log << "BASE_MAP: " << line << std::endl;
            break;
        }
    }

    log << "SIGNAL: " << signum << std::endl;
    log << "CRASH_ADDRESS: 0x" << std::hex << rip << std::endl;
    log.close();

    std::_Exit(1);
}

int main() {
    struct sigaction sa;
    sa.sa_sigaction = crash_handler;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, nullptr);

    int* ptr = nullptr;
    std::cout << "About to crash..." << std::endl;
    std::cout << *ptr << std::endl;
    return 0;
}