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
    int value() { return v_; }

private:
    int v_;
};

bool operator<(int_wrapper_t a, int_wrapper_t b)
{
    return a.value() < b.value();
}

std::ostream& operator<<(std::ostream& os, int_wrapper_t i)
{
    os << i.value();
    return os;
}

void swap(int_wrapper_t & a, int_wrapper_t & b)
{
    // we will hook this function to find out what's going on
    std::swap(a, b);
}

int main()
{
    int const N = 20;
    std::vector<int_wrapper_t> A(N);
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
