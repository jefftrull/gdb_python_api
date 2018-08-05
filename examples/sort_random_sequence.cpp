// simple use of std algorithm to drive animation

#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <iterator>
#include <random>

struct int_wrapper_t
{
    int_wrapper_t() : v_(0) {}
    int_wrapper_t(int v) : v_(v) {}

    // std::sort uses swap, move, and move assignment
    // our custom swap is below
    int_wrapper_t(int_wrapper_t && other);
    int_wrapper_t& operator=(int_wrapper_t && other);

    // so I don't have to write operator< or operator<<
    operator int() const { return v_; }

private:
    int v_;
};

std::vector<int_wrapper_t> * vec = nullptr;

// instrumentable functions
int_wrapper_t::int_wrapper_t(int_wrapper_t && other)
{
    v_ = other.v_;
}

int_wrapper_t& int_wrapper_t::operator=(int_wrapper_t && other)
{
    v_ = other.v_;
    return *this;
}

void swap(int_wrapper_t & a, int_wrapper_t & b)
{
    // we will hook this function to find out what's going on
    // BOZO but std::swap will call other stuff we are observing... oops
    std::swap(a, b);

}

int main()
{
    int const N = 20;
    std::vector<int_wrapper_t> A(N);
    vec = &A;
    // randomly shuffle the sequence 1 to N
    std::iota(A.begin(), A.end(), 1);
    std::shuffle(A.begin(), A.end(),
                 std::mt19937{std::random_device{}()});

    // then sort it
    std::sort(A.begin(), A.end());

    std::cout << "A=[ ";
    std::copy(A.begin(), A.end(),
              std::ostream_iterator<int_wrapper_t>(std::cout, " "));
    std::cout << "]\n";

}
