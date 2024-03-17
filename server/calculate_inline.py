import resource
from sys import argv
from user_defined import *
import random
import datetime as dt
import math
import json
import re
import ast

try:
    res_limits = resource.getrusage(resource.RUSAGE_SELF)
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    request = argv[1]
    print(ast.literal_eval(request))
except (ValueError, SyntaxError) as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(e)