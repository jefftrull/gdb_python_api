// testing procedure to find translation unit
namespace detail {
struct Foo {
    void member_fn() const {
        std::cout << "hello\n";
    };
    void member_fn2() const {
        std::cout << "hello\n";
    };
};

void do_something(Foo const& x) {
    x.member_fn();
}

}

