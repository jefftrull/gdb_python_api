// new idea for leakage example
#include <functional>
#include <vector>
#include <memory>
#include <iostream>


using namespace std;

struct TaskList
{
    template<typename F>
    void add(F f) {
        tasks_.push_back(move(f));
    }

    void doOne() {
        if (!tasks_.empty()) {
            auto f = tasks_.back();
            tasks_.pop_back();
            f();
        }
    }

private:
    vector<function<void()>> tasks_;

};

int main() {
    auto tasks = make_shared<TaskList>();

    tasks->add([tasks]() {
            cout << "task 1\n";
            // queue another one
            tasks->add([]() {
                    cout << "task 2\n";
                });
        });

}

