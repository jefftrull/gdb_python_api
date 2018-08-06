// example code with leaks related to shared_ptr reference loops
#include <memory>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <iterator>

struct Person : std::enable_shared_from_this<Person> {
    Person(std::string name) : name_(std::move(name)) {}
    std::shared_ptr<Person> manager() { return manager_; }

    std::shared_ptr<Person> create_employee(std::string name) {
        // can't use make_shared because it cannot access the private ctor :(
        auto employee = std::shared_ptr<Person>(new Person(std::move(name), shared_from_this()));
        employees_.push_back(employee);
        return employee;
    }
    std::string name() const { return name_; }

private:
    Person(std::string name, std::shared_ptr<Person> manager)
        : manager_(std::move(manager)), name_(std::move(name)) {}

    std::shared_ptr<Person>              manager_;
    std::vector<std::shared_ptr<Person>> employees_;
    std::string                          name_;
};

void foo() {
  auto alice = std::make_shared<Person>("Alice");
  auto bob = alice->create_employee("Bob");
  auto carol = alice->create_employee("Carol");

  std::cout << "three colleagues: " << alice->name() << ", " << bob->name() << ", and " << carol->name() << "\n";
}   // alice and either one of her employees form a reference loop, so this leaks here

int main() {
    foo();
    std::cout << "done with foo\n";
    auto david = std::make_shared<Person>("David");  // valgrind recognizes leak in here
    std::cout << "david's name is " << david->name() << "\n";
}

