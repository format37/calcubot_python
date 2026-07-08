from sys import argv

from calc_core import evaluate
from user_defined import nf, fact

# Inline (/inline) evaluation. Same as native plus the user_defined helpers.
evaluate(argv[1], {'nf': nf, 'fact': fact})
