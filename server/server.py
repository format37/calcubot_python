from fastapi import FastAPI, Request, Header, Response
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from asyncio.subprocess import PIPE, STDOUT
import ast
import hmac
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.formatting import escape_markdown
import json
from re import search, escape
import sqlite3
import asyncio
import os

DB_PATH = '/server/data/calcubot.db'
compact_users: set = set()

# Unprivileged identity the evaluation subprocess is dropped to (created in the
# Dockerfile). The token lives in the root-only /secrets dir, so this user cannot
# traverse to it and cannot read the bot token even if a filter is bypassed.
SANDBOX_UID = int(os.environ.get('SANDBOX_UID', '5000'))
SANDBOX_GID = int(os.environ.get('SANDBOX_GID', '5000'))
# Wall-clock ceiling for a single evaluation (CPU/memory are capped in-process).
SANDBOX_WALL_TIMEOUT = 8

# User-facing replies for the two empty-output cases. Never return '' — Telegram
# rejects empty messages, so in compact mode an empty result arrives as nothing.
TIMEOUT_MESSAGE = 'Timed out: the computation was too heavy (2-second limit)'
NO_OUTPUT_MESSAGE = 'No output (the program did not produce a value)'

def _fmt(segments, md):
    """Render (kind, text) segments to MarkdownV2 (md=True) or plain (md=False).
    Prose is escaped with telebot's escape_markdown; 'code' goes in a fenced block
    (monospace, only backslash/backtick escaped) so examples need no hand-escaping."""
    out = []
    for kind, text in segments:
        if kind == 'code':
            if md:
                out.append('```\n' + text.replace('\\', '\\\\').replace('`', '\\`') + '\n```')
            else:
                out.append(text)
        elif kind == 'bold':
            out.append('*' + escape_markdown(text) + '*' if md else text)
        else:
            out.append(escape_markdown(text) if md else text)
    return '\n'.join(out)


_START_SEGMENTS = [
    ('text', "Hi! I'm a Python console calculator. Send me any expression and I'll return the value of the final line."),
    ('text', 'Try:'),
    ('code', '2 + 2\nmath.sqrt(144)\nsum(x**2 for x in range(10))'),
    ('text', 'Send /help for imports and multi-line programs.'),
]

_HELP_SEGMENTS = [
    ('bold', 'CalcuBot - a Python console calculator'),
    ('text', 'Send an expression; the value of the final line comes back, REPL-style.'),
    ('code', '2 + 2\n(3.14 * 100) / 2\n17 % 5'),
    ('bold', 'Ready to use (no import needed)'),
    ('text', 'math, random, dt (datetime), json, re'),
    ('code', 'math.factorial(10)\nrandom.randint(1, 100)'),
    ('bold', 'Multi-line programs & imports'),
    ('text', 'Full programs work. Import from a math/data allowlist: math, cmath, statistics, fractions, decimal, random, datetime, itertools, functools, operator, collections, re, json, string, bisect, heapq, numbers, array.'),
    ('code', 'from fractions import Fraction\nFraction(1, 3) + Fraction(1, 6)'),
    ('code', 'total = 0\nfor i in range(1, 6):\n    total += i ** 2\ntotal'),
    ('bold', 'Inline (any chat)'),
    ('text', 'Type  @calcubot 2**64  in any message box and pick a result.'),
    ('bold', 'Commands'),
    ('text', '/mode - toggle compact output in private chat (result only)\n/cl - in groups, prefix your expression so I reply to your message'),
]

START_MESSAGE_MD = _fmt(_START_SEGMENTS, md=True)
START_MESSAGE_PLAIN = _fmt(_START_SEGMENTS, md=False)
HELP_MESSAGE_MD = _fmt(_HELP_SEGMENTS, md=True)
HELP_MESSAGE_PLAIN = _fmt(_HELP_SEGMENTS, md=False)

def _init_db() -> set:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS compact_users (user_id TEXT PRIMARY KEY)')
    conn.commit()
    rows = conn.execute('SELECT user_id FROM compact_users').fetchall()
    conn.close()
    return {row[0] for row in rows}

def _db_add_user(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT OR REPLACE INTO compact_users VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def _db_remove_user(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM compact_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Read unsecure words from file
with open('unsecure_words.txt') as f:
    calcubot_unsecure_words = f.readlines()
calcubot_unsecure_words = [x.strip() for x in calcubot_unsecure_words]

# Read blocked users from file
with open('blocked_users.txt') as f:
    blocked_users = f.readlines()
blocked_users = [x.strip() for x in blocked_users]

# Initialize FastAPI with a lifespan handler (modern Starlette; replaces on_event).
@asynccontextmanager
async def lifespan(app):
    global compact_users
    loop = asyncio.get_running_loop()
    compact_users = await loop.run_in_executor(None, _init_db)
    logger.info(f'Loaded {len(compact_users)} compact-mode users from DB')
    yield

app = FastAPI(lifespan=lifespan)

# Initialize logging
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.info('Logging started')

# The token lives behind a root-only directory (see Dockerfile / compose) so the
# dropped-privilege evaluation subprocess cannot reach it. Only this parent
# process (root) reads it, at startup, into memory.
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/secrets/config.json')
with open(CONFIG_PATH) as config_file:
    _config = json.load(config_file)
bot = telebot.TeleBot(_config['TOKEN'])
# Optional shared secret authenticating inbound update POSTs. Unset by default, so
# the existing gateway keeps working unchanged; when set (env wins over config.json)
# a matching Authorization header is required on /message and /inline.
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET') or _config.get('WEBHOOK_SECRET') or ''
del _config
# logger.info(f'Bot initialized: {bot}')


def safe_send_message(chat_id, text, **kwargs):
    """Send a Telegram message, swallowing expected delivery errors.

    The common case is 403 'bot was blocked by the user' — e.g. a delayed or
    retried update for someone who has since blocked the bot. Such errors must
    not crash the request handler: otherwise FastAPI returns 500 and the update
    gets re-delivered, re-processing the same expression in a loop.
    """
    try:
        bot.send_message(chat_id, text, **kwargs)
    except ApiTelegramException as e:
        logger.info(f'send_message skipped for chat {chat_id}: {e.description}')


def safe_send_markdown(chat_id, md_text, plain_text, **kwargs):
    """Send MarkdownV2; on a parse/delivery error fall back to plain text so a
    formatting slip can never blank the message."""
    try:
        bot.send_message(chat_id, md_text, parse_mode='MarkdownV2', **kwargs)
    except ApiTelegramException as e:
        logger.info(f'MarkdownV2 send failed for chat {chat_id}: {e.description}; plain fallback')
        safe_send_message(chat_id, plain_text, **kwargs)


async def is_complete_expression(expression):
    try:
        # If empty string then return False
        if expression.strip() == '':
            return False
        ast.parse(expression)
        return True
    except SyntaxError:
        return False

# Modules a user program is allowed to import. Pure-computation stdlib only:
# nothing that touches the filesystem, network, process, or reflection machinery.
ALLOWED_IMPORTS = {
    'math', 'cmath', 'statistics', 'fractions', 'decimal', 'random', 'datetime',
    'itertools', 'functools', 'operator', 'collections', 're', 'json', 'string',
    'bisect', 'heapq', 'numbers', 'array',
}

# Builtins that must never be *referenced* (in any position — not just called),
# so that aliasing them past the filter under exec (e.g. ``o = open``) is blocked.
# Includes operator's getattr/getitem/method primitives, which are string->attr
# equivalents that would otherwise reconstruct __globals__/__builtins__ at runtime.
DANGEROUS_NAMES = {
    '__import__', 'exec', 'eval', 'compile', 'open', 'input',
    'getattr', 'setattr', 'delattr', 'vars', 'dir', 'globals', 'locals',
    'builtins', 'breakpoint', 'exit', 'quit', 'help', 'memoryview',
    'attrgetter', 'methodcaller', 'itemgetter',
}

# Non-dunder introspection attributes that reach frames/globals/builtins (the
# generator/coroutine frame gadget: ``(x for x in[1]).gi_frame.f_builtins``).
# Blocked both as attribute access and inside string literals (str.format path).
DANGEROUS_ATTRS = {
    'gi_frame', 'gi_code', 'gi_yieldfrom', 'cr_frame', 'cr_code', 'cr_await',
    'ag_frame', 'ag_code', 'ag_await', 'f_globals', 'f_builtins', 'f_locals',
    'f_back', 'f_code', 'f_trace', 'tb_frame', 'tb_next', 'tb_lasti',
    'func_globals', 'func_code',
}


def is_dangerous_ast(expression):
    """AST-based security check - detects dangerous patterns at syntax level.

    Parses in ``exec`` mode so multi-statement programs (loops, assignments,
    imports) are supported, and rejects, before anything runs:
      * imports of modules outside ``ALLOWED_IMPORTS``;
      * any reference to a dangerous builtin (blocks alias tricks like ``o=open``);
      * any dunder identifier (name, attribute, argument, function/class name);
      * string literals carrying ``__`` (blocks the ``str.format``/``%`` gadget
        that reaches ``__globals__``/``__builtins__`` from inside a literal).
    """
    try:
        tree = ast.parse(expression, mode='exec')
    except SyntaxError:
        return True  # Block invalid syntax

    for node in ast.walk(tree):
        # Import allowlist (import X / from X import ...)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] not in ALLOWED_IMPORTS:
                    return True
        elif isinstance(node, ast.ImportFrom):
            if (node.module or '').split('.')[0] not in ALLOWED_IMPORTS:
                return True
        # Dangerous builtin referenced anywhere (call target, alias, argument, ...)
        if isinstance(node, ast.Name) and node.id in DANGEROUS_NAMES:
            return True
        # Dangerous method call by attribute (e.g. x.getattr(...))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in DANGEROUS_NAMES:
            return True
        # Block introspection attributes that reach frames/globals/builtins
        if isinstance(node, ast.Attribute) and node.attr in DANGEROUS_ATTRS:
            return True
        # Block every dunder identifier, whatever the node kind
        for field in ('id', 'attr', 'arg', 'name'):
            ident = getattr(node, field, None)
            if isinstance(ident, str) and ident.startswith('__'):
                return True
        # Block dunders / introspection names hidden inside a string literal
        # (the str.format / % gadget: "{0.gi_frame.f_builtins}".format(gen))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and ('__' in node.value
                     or any(a in node.value for a in DANGEROUS_ATTRS)):
            return True
    return False

def filter_sensitive_output(response):
    """Filter potential token leaks from output"""
    # Telegram bot token pattern: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    if search(r'\d{6,}:[A-Za-z0-9_-]{32,}', response):
        return '[FILTERED]'
    return response

async def calcubot_security(request):
    # 1. AST-based check (catches construction bypasses like string concat, f-strings, byte decoding)
    if is_dangerous_ast(request):
        return False

    # 2. Regex blocklist (catches string patterns)
    try:
        decoded = request.encode('utf-8').decode('unicode_escape')
    except:
        decoded = request  # fallback if decode fails

    for word in calcubot_unsecure_words:
        # Use word boundary matching to avoid false positives
        # e.g., "os" should block "os.system" but not "gosuslugi"
        if search(r'\b' + escape(word) + r'\b', decoded):
            return False
    return True

async def is_blocked_user(user_id):
    return user_id in blocked_users

@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})

async def secure_eval(expression, mode):
    logger.info(f'expression to evaluate: {expression!r}')
    if not await calcubot_security(expression):
        return 'Request is not supported'
    subprocess_kwargs = dict(
        stdout=PIPE,
        stderr=STDOUT,
        cwd='sandbox',                                     # no config.json here
        env={'PATH': '/usr/local/bin:/usr/bin',
             'PYTHONBREAKPOINT': '0',                      # never drop into pdb
             'HOME': '/tmp'},                              # dropped user has no home
    )
    # Drop privileges so the evaluation cannot read config.json (the bot token)
    # even if every string filter is bypassed. Only possible when the server runs
    # as root (i.e. inside the container); a no-op in local dev.
    if hasattr(os, 'getuid') and os.getuid() == 0:
        subprocess_kwargs['user'] = SANDBOX_UID
        subprocess_kwargs['group'] = SANDBOX_GID
        subprocess_kwargs['extra_groups'] = []
    # Async subprocess + await: a heavy or hung evaluation must not block the event
    # loop (and thus every other user). Wall-clock is bounded here; CPU and memory
    # are bounded in-process by the sandbox rlimits.
    proc = await asyncio.create_subprocess_exec(
        'python3', 'calculate_' + mode + '.py', expression, **subprocess_kwargs)
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(),
                                           timeout=SANDBOX_WALL_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return TIMEOUT_MESSAGE
    result = stdout.decode('utf-8').replace('\n', ' ').strip()
    # A negative return code means the sandbox was killed by a signal - almost
    # always the CPU/memory limit on a heavy computation, which leaves no output.
    if proc.returncode is not None and proc.returncode < 0:
        return TIMEOUT_MESSAGE
    # Clean exit but nothing printed: the program produced no value.
    if result == '':
        return NO_OUTPUT_MESSAGE
    # Last line of defense against token leaks.
    return filter_sensitive_output(result)

@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    if WEBHOOK_SECRET and not hmac.compare_digest(authorization or '', WEBHOOK_SECRET):
        return Response(content='unauthorized', status_code=401)
    message = await request.json()
#     response = """Hello,

# This bot is currently undergoing maintenance related to migration to another server and refactoring. Please wait until June 3, 2023, for the bot to resume its normal functionality.
# I appreciate that you are using this bot and thank you for your patience and understanding during this maintenance period.

# Warm regards,
# Alex"""
#     safe_send_message(message['chat']['id'], response)
#     return Response(content='ok', status_code=200)

    # Empty message
    if 'text' not in message:
        return Response(content='ok', status_code=200)
    expression = message['text']
    # Start or help
    if expression.startswith('/start'):
        safe_send_markdown(message['chat']['id'], START_MESSAGE_MD, START_MESSAGE_PLAIN)
        return Response(content='ok', status_code=200)
    if expression.startswith('/help'):
        safe_send_markdown(message['chat']['id'], HELP_MESSAGE_MD, HELP_MESSAGE_PLAIN)
        return Response(content='ok', status_code=200)
    # Mode toggle (private chat only)
    if expression.startswith('/mode'):
        if message['chat']['type'] == 'private':
            user_id = str(message['from']['id'])
            loop = asyncio.get_running_loop()
            if user_id in compact_users:
                compact_users.discard(user_id)
                await loop.run_in_executor(None, _db_remove_user, user_id)
                safe_send_message(message['chat']['id'], 'Mode: full')
            else:
                compact_users.add(user_id)
                await loop.run_in_executor(None, _db_add_user, user_id)
                safe_send_message(message['chat']['id'], 'Mode: compact')
        return Response(content='ok', status_code=200)
    # Not private chat
    if not message['chat']['type'] == 'private':
        # logger.info(f"message: {message}")
        # if via_bot is in message, return
        if 'via_bot' in message or 'reply_to_message' in message:
            # logger.info(f"answer canceled due to via_bot or reply_to_message in message")
            return Response(content='ok', status_code=200)
    #     # Exit from group
    #     logger.info(f"### ### ### Leaving group: {message['chat']['id']}: {bot.leave_chat(message['chat']['id'])}")
    #     return Response(content='ok', status_code=200)
    # Some updates (anonymous admins, channel-as-sender, auto-forwards) carry no
    # 'from'. Drop them instead of raising KeyError -> 500 -> gateway retry loop.
    from_user = message.get('from')
    if from_user is None:
        return Response(content='ok', status_code=200)
    user_id = str(from_user['id'])
    # Blocked user
    if await is_blocked_user(user_id):
        return Response(content='ok', status_code=200)
    
    need_to_reply = False
    # /cl (optionally /cl@botname): reply directly to the user's message. Prefix
    # match, not substring, so an expression that merely contains '/cl' stays intact.
    if expression.startswith('/cl'):
        rest = expression[3:]
        if rest[:1] == '@':                # '/cl@botname ...'
            parts = rest.split(None, 1)
            rest = parts[1] if len(parts) > 1 else ''
        expression = rest.strip()
        need_to_reply = True
   
    answer_max_length = 4095
    res = str(await secure_eval(expression, 'native'))[:answer_max_length]
    if message['chat']['type'] == 'private' and user_id in compact_users:
        response = res
    else:
        response = f'{res} = {expression}'
    logger.info(f'Sending message to chat {message["chat"]["id"]}: {response!r}')
    if need_to_reply:
        safe_send_message(message['chat']['id'], response, reply_to_message_id=message['message_id'])
    else:
        safe_send_message(message['chat']['id'], response)
    
    return Response(content='ok', status_code=200)


# Post inline query
@app.post("/inline")
async def call_inline(request: Request, authorization: str = Header(None)):
    if WEBHOOK_SECRET and not hmac.compare_digest(authorization or '', WEBHOOK_SECRET):
        return JSONResponse(content={"status": "unauthorized"}, status_code=401)
    message = await request.json()
    from_user_id = message['from_user_id']
    inline_query_id = message['inline_query_id']
    expression = message['query']
    # Blocked user
    if await is_blocked_user(from_user_id):
        return JSONResponse(content={"status": "ok"})
    if not await is_complete_expression(expression):
        res = f'Incomplete expression: {expression}'
        answer = [res]
    else:
        answer_max_lenght       = 4095
        res = str(await secure_eval(expression, 'inline'))[:answer_max_lenght]
        answer  = [
                    res + ' = ' + expression,
                    expression + ' = ' + res,
                    res
                ]
    logger.info(f'User: {from_user_id} Inline request: {expression} Response: {res}')

    try:
        inline_elements = []
        for i in range(len(answer)):
            element = telebot.types.InlineQueryResultArticle(
                str(i),
                answer[i],
                telebot.types.InputTextMessageContent(answer[i]),
            )
            inline_elements.append(element)
        
        # logger.info(f'[answer_inline_query] inline_query_id: {inline_query_id} inline_elements: {inline_elements}')
        bot.answer_inline_query(
            inline_query_id,
            inline_elements,
            cache_time=0,
            is_personal=True
        )
    except Exception as e:
        logger.error(f'User: {from_user_id} Inline request: {expression}  Error processing inline query: {str(e)}')

    return JSONResponse(content={"status": "ok"})

