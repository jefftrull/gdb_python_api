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

using Strings = std::vector<std::string>;

int main() {
    // (broken) attempt at lexicographic sort

    std::vector<Strings> data{
        {{"Foo", "Bar", "Baz"}},
        {{"Frodo", "Sam", "Smeagol"}},
        {{"Monoid", "Endofunctor", "Monad"}}};

    // sample code targets the beginning of this call:
    std::sort(data.begin(), data.end(),
              [](Strings const & a, Strings const & b) {
                  if (a[0] < b[0]) {
                      return true;
                  } else {
                      return a[1] < b[1];
                  }
              });

    for(auto const & v : data) {
        std::copy(v.begin(), v.end(),
                  std::ostream_iterator<std::string>(std::cout, ", "));
        std::cout << "\n";
    }

}
