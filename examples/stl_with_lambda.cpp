// Sample code for analyzing with libClang

// Release mode turns this off
#ifdef SUPPRESS_INLINE
#define INLINECTL __attribute__((noinline,optimize("-O0")))
#else
#define INLINECTL
#endif

#include <vector>
#include <algorithm>
#include <iostream>
#include <iterator>
#include <string>

#include "detail.h"

using namespace detail;

int main() {
    // (broken) attempt at lexicographic sort

    using Strings = std::vector<std::string>;

    std::vector<Strings> data{
        {"Frodo", "Sam", "Smeagol"},
        {"Foo", "Bar", "Baz"},
        {"Monoid", "Endofunctor", "Monad"}};

    // sample code targets the beginning of this call:
    std::sort(data.begin(), data.end(),
              [](Strings const & a, Strings const & b) {
                  if (a[0] < b[0]) {
                      return true;
                  } else {
                      return a[1] < b[1];
                  }
              });

    Foo f;
    do_something(f);

    for(auto const & v : data) {
        std::copy(v.begin(), v.end(),
                  std::ostream_iterator<std::string>(std::cout, ", "));
        std::cout << "\n";
    }

}
