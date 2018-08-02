// Some example code with lots of local variables going in and out of scope
// so we can see stack movements

#include <string>
#include <vector>
#include <tuple>

std::tuple<int, int, int> outside;

void noargs() {
    // no args - frame print starts with return address
    // just one local:
    std::vector<std::string> baz{"foo", "bar", "baz"};
    baz.push_back("");
}

void work(int j, std::string const& s) {
    // two args (one in a register), no locals

    noargs();  // new frame

    // one arg and one local on the frame
    std::vector<std::string> bar{"foo", "bar", "baz"};

    {
        // one arg, two locals
        std::string foo("foo");
    }

    // one arg, one local
    bar.push_back(s);

    // suppress unused warning
    (void)j;

}

int main(int argc, char **argv) {
    work(1, "quux");

    (void)argc;
    (void)argv;
}
