// test_crash_win.cpp
#include "debugai_handler.h"

int main() {
    debugai::install_crash_handler(".");

    int* p = nullptr;
    *p = 42;  // deliberate null pointer dereference

    return 0;
}