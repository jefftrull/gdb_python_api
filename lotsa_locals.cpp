// Some example code with lots of local variables going in and out of scope
// so we can see stack movements

#include <iostream>
#include <string>
#include <vector>

int main() {
    std::cout << "begin\n";
    {
        std::string foo("foo");
        std::cout << "phase 1\n";
    }
    std::vector<std::string> bar{"foo", "bar", "baz"};
    for (auto s : bar) {
        std::cout << "phase 2\n";
    }
    std::cout << "phase 3\n";
}
