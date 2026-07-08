from sys import argv

from calc_core import evaluate

# Direct-chat (/message) evaluation. Namespace = the common pre-bound modules only.
evaluate(argv[1])
