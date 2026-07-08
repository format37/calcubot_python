"""Shared sandbox execution core.

Runs a (possibly multi-line) user program under hard resource limits and prints
its result. Security vetting (AST allowlist / denylist, regex blocklist) is done
by the parent process (server.py) BEFORE this script is ever spawned; this module
only provides the last two layers of defense:

  * OS resource caps  - RLIMIT_CPU (busy-loop / heavy-int freeze) and RLIMIT_AS
                        (memory bomb, e.g. ``999999**99999999``).
  * REPL-style output - execute every statement; if the final statement is a bare
                        expression, echo its value (like a Python shell), so both
                        ``2+2`` and ``from math import comb\\nprint(comb(5,2))`` work.

The process is additionally expected to run as an unprivileged uid with no read
access to config.json (dropped by the parent via Popen(user=...)), so even a full
filter bypass cannot reach the bot token.
"""
import ast
import resource
import datetime as dt
import json
import math
import random
import re

import seccomp_filter

# Wall-clock is bounded by the parent (Popen communicate timeout); here we bound
# CPU time and address space so a single evaluation cannot exhaust the host.
CPU_SECONDS = 2
MEM_BYTES = 512 * 1024 * 1024  # 512 MiB


def _apply_limits():
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    except (ValueError, OSError):
        pass


def _base_globals(extra):
    # Modules pre-bound for convenience / backward compatibility (users have always
    # been able to write ``math.sqrt(2)`` without importing). Additional modules can
    # be pulled in with an explicit import, gated by server.py's allowlist.
    g = {'math': math, 'random': random, 'dt': dt, 'json': json, 're': re}
    if extra:
        g.update(extra)
    return g


def evaluate(source, extra_globals=None):
    """Execute ``source`` and print its result (REPL semantics)."""
    _apply_limits()
    # Last line of defense: even if user code reaches os/socket/subprocess through
    # some language-level bypass, the kernel refuses network and process-spawn
    # syscalls. Best-effort — the token is already protected by the uid drop and
    # root-only /secrets, so a failed install degrades gracefully.
    seccomp_filter.install()
    g = _base_globals(extra_globals)
    try:
        tree = ast.parse(source, mode='exec')
        body = tree.body
        if body and isinstance(body[-1], ast.Expr):
            # Run all leading statements, then evaluate + echo the trailing expression.
            head = ast.Module(body=body[:-1], type_ignores=[])
            tail = ast.Expression(body[-1].value)
            exec(compile(head, '<calc>', 'exec'), g)
            value = eval(compile(tail, '<calc>', 'eval'), g)
            if value is not None:
                print(value)
        else:
            exec(compile(tree, '<calc>', 'exec'), g)
    except Exception as ex:
        print(f'{type(ex).__name__}: {ex}')
