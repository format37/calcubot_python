import resource
import sys
import math
import pandas
import pandas as pd
import numpy
import numpy as np
import scipy
from scipy import stats
import random
import datetime
import statistics

def nf(value,format_line='{:,}'):
    return format_line.format(value)

def fact(n):

    factors = []

    def get_factor(n):
        x_fixed = 2
        cycle_size = 2
        x = 2
        factor = 1

        while factor == 1:
            for count in range(cycle_size):
                if factor > 1: break
                x = (x * x + 1) % n
                factor = math.gcd(x - x_fixed, n)

            cycle_size *= 2
            x_fixed = x

        return factor

    while n > 1:
        next = get_factor(n)
        factors.append(next)
        n //= next

    return factors

try:
        res_limits = resource.getrusage(resource.RUSAGE_SELF)
        resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
        request = sys.argv[1]
        print( eval(request) )
except Exception as e:
        print(e)
