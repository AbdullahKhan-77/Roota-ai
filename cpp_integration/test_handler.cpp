#include <iostream>
#include "debugai_handler.h"

int main() {
    debugai::install_crash_handler("crash_reports");

    int* ptr = nullptr;
    std::cout << "About to crash..." << std::endl;
    std::cout << *ptr << std::endl;
    return 0;
}