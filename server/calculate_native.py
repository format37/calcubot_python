import resource
from sys import argv
from user_defined import *
import pandas as pd
import numpy as np
import scipy
from scipy import stats
import random
import datetime as dt
import statistics
import ast
import math
import sympy
import json
import re
import signal

# Add the signal handling function to catch SIGXCPU
def signal_handler(signum, frame):
    print('Timeout exceeds')

"""try:
	res_limits = resource.getrusage(resource.RUSAGE_SELF)
	resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
	request = argv[1]
	print( eval(request) )
except Exception as e:
	print(e)
"""

try:
    res_limits = resource.getrusage(resource.RUSAGE_SELF)
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    
    # Register the signal handler
    signal.signal(signal.SIGXCPU, signal_handler)

    request = argv[1]
    
    # Perform the evaluation safely
    print(eval(request))
    
except Exception as e:
    print(e)
