import resource
import sys
import math
import pandas
import numpy
import random

def nf(value,format_line='{:,}'):
    return format_line.format(value)

try:
	res_limits = resource.getrusage(resource.RUSAGE_SELF)
	resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
	request = sys.argv[1]
	print( eval(request) )
except Exception as e:
	print(e)
