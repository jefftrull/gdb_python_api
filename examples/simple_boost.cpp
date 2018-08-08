// simple Boost usage example for gdb

#include <iostream>
#include <boost/math/common_factor_rt.hpp>

int main()
{
    using namespace boost::math;
    int result = gcd_evaluator<int>()(50, 125);
    std::cout << "GCD of 50 and 125 is " << result << "\n";
}
