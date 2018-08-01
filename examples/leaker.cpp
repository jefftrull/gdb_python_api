// example code with leaks related to shared_ptr reference loops
#include <memory>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <iterator>

struct Person : std::enable_shared_from_this<Person> {
    Person(std::string name) : name_(std::move(name)) {}
    std::shared_ptr<Person> parent() { return parent_; }

    std::shared_ptr<Person> create_child(std::string name) {
        // can't use make_shared because it cannot access the private ctor :(
        auto child = std::shared_ptr<Person>(new Person(std::move(name), shared_from_this()));
        children_.push_back(child);
        return child;
    }
    std::string name() const { return name_; }

private:
    Person(std::string name, std::shared_ptr<Person> parent)
        : name_(std::move(name)), parent_(std::move(parent)) {}

    std::shared_ptr<Person>              parent_;
    std::vector<std::shared_ptr<Person>> children_;
    std::string                          name_;
};

int main() {
    {
        auto alice = std::make_shared<Person>("Alice");
        auto bob   = alice->create_child("Bob");
        auto carol = alice->create_child("Carol");

    }
    auto david = std::make_shared<Person>("David");
}

