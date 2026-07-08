# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

[@calcubot](t.me/calcubot) — a Telegram bot that acts as a Python console calculator. It accepts arbitrary Python **programs** (multi-line, with imports from a curated allowlist) and runs them via `exec()` in a sandboxed, privilege-dropped subprocess, echoing the final expression's value REPL-style. Served via FastAPI, deployed via Docker Compose, connected to a local Telegram server.

## Running / Deploying

```bash
# Build and (re)start the container
bash compose.sh        # runs: sudo docker compose down calcubot -v && docker compose up --build --force-recreate -d

# Follow logs
bash logs.sh
```

The container maps port `8704 → 8000`. `config.json` (with the bot `TOKEN`) is bind-mounted at runtime into the **root-only `/secrets/` directory** (`./config.json:/secrets/config.json:ro`) and is **not baked into the image**. The uid-5000 evaluation subprocess cannot traverse `/secrets/`, so it can never read the token; only the root parent process reads it at startup.

For the test bot, use `config_test.json` as the source for `config.json`.

## Dependencies

`server/requirements.in` is the **hand-edited** list of direct (top-level)
dependencies. `server/requirements.txt` is a **generated, fully-pinned lock**
(every transitive dependency pinned) — it is what the Docker image installs and
what GitHub Dependabot scans, so transitive deps (e.g. `starlette` under
FastAPI) are watched for vulnerabilities too.

Never hand-edit `requirements.txt`. To change a dependency: edit
`requirements.in`, then regenerate the lock from the `server/` directory in the
same Python the image uses:

```bash
docker run --rm -v "$PWD:/w" -w /w python:3.14-slim-trixie \
  sh -c "pip install -q pip-tools && pip-compile --strip-extras requirements.in"
```

Commit both files. A bare `requirements.txt` (direct deps only, no lock) leaves
transitive vulnerabilities invisible to Dependabot — verify coverage with an OSV
scan of the running container's `pip freeze` if in doubt.

## Architecture

```
FastAPI server (server/server.py)
  POST /message   — direct chat messages
  POST /inline    — Telegram inline query handler
  GET  /test      — health check
```

Evaluation pipeline (in `secure_eval`):
1. **AST analysis** (`is_dangerous_ast`) — parses in `exec` mode and rejects, before anything runs: imports outside `ALLOWED_IMPORTS`; any reference to a `DANGEROUS_NAMES` builtin (in *any* position, so aliasing like `o = open` is caught); any `__dunder__` identifier (name/attr/arg/func/class); and string literals containing `__` (the `str.format`/`%` → `__globals__` gadget).
2. **Unicode decode + regex blocklist** (`calcubot_security`) — normalises `\uXXXX` escapes then checks against `server/unsecure_words.txt` (secondary tripwire).
3. **Privilege-dropped, seccomp-filtered sandbox subprocess** — `python3 calculate_native.py <src>` (or `calculate_inline.py`) is spawned with `cwd='sandbox/'`, a clean env (`PATH`, `PYTHONBREAKPOINT=0`, `HOME=/tmp`), and — when the server runs as root — `user=5000, group=5000` so it cannot read `/secrets/config.json`. A wall-clock `communicate(timeout=8)` kills hung runs.
4. **Output filter** (`filter_sensitive_output`) — redacts any Telegram bot token pattern from the response.

The sandbox scripts are thin wrappers over `sandbox/calc_core.py`, which (a) sets `RLIMIT_CPU` (2 s — busy loops / heavy-int) **and** `RLIMIT_AS` (512 MiB — memory bombs like `999999**99999999`); (b) installs a **seccomp-BPF syscall filter** (`sandbox/seccomp_filter.py`, stdlib ctypes, no deps) that denies `socket`/`connect`/`execve`/`fork`/`clone` so a language-level escape can reach neither the network nor a shell; then (c) `exec()`s the program and echoes the final expression REPL-style. `calculate_inline.py` additionally injects `nf`, `fact` from `user_defined.py`.

## Security model

Defense-in-depth is intentional — `prompt.md` documents the original design philosophy (full Python accepted knowingly) and the December 2025 vulnerability report that led to layered security. A July 2026 red-team proved that string/AST filtering **cannot** contain `exec()` + Python introspection: runtime-built strings (`'_'*2+'glob'+'als'`) fed to a string→attribute primitive (`operator.attrgetter`, `str.format`, or a generator's `gi_frame.f_builtins`) reconstruct `__globals__`/`__builtins__` no static check can see. (The same generator-frame gadget was a live RCE on the pre-migration single-expression bot.) So **the security boundary is the OS layer**: the token is unreadable to the sandbox uid, and the seccomp filter makes arbitrary code harmless (no network, no process spawn) — reduced to pure computation over world-readable, non-secret files. The import allowlist + AST + regex filters are defense-in-depth that block the *known* gadgets before seccomp is needed. `vulnerability-test.md` is the canonical test suite — run through its checklist when changing security logic.

Key invariants to maintain:
- The token file must stay behind the root-only `/secrets/` dir, mounted read-only; the sandbox subprocess must keep dropping to an unprivileged uid.
- `calc_core.py` must install the seccomp filter **before** running user code; the filter must keep denying network + exec/fork syscalls. This is the load-bearing containment — do not weaken it on the assumption the string filters will catch everything (they cannot).
- `ALLOWED_IMPORTS` must contain **only** pure-computation modules — never anything that touches the filesystem, network, process, or reflection (`os`, `sys`, `io`, `subprocess`, `importlib`, `ctypes`, `socket`, `pickle`, `inspect`, …).
- The AST check runs **before** the subprocess and must keep blocking: dangerous-name references anywhere (incl. `operator.attrgetter`/`itemgetter`/`methodcaller`), all `__dunder__` identifiers, the frame/generator introspection attrs in `DANGEROUS_ATTRS`, and `__`/introspection-bearing string literals.
- CPU **and** memory rlimits must stay set — the bot is expected to survive inefficient input (e.g. `999999**99999999`) without freezing.
