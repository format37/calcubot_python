from fastapi import FastAPI, Request, Header, Response
# , HTTPException
# from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import logging
from subprocess import Popen, PIPE, STDOUT
import ast
import telebot
import json
from re import findall, search, escape

# Read unsecure words from file
with open('unsecure_words.txt') as f:
    calcubot_unsecure_words = f.readlines()
calcubot_unsecure_words = [x.strip() for x in calcubot_unsecure_words]

# Read blocked users from file
with open('blocked_users.txt') as f:
    blocked_users = f.readlines()
blocked_users = [x.strip() for x in blocked_users]

# Initialize FastAPI
app = FastAPI()

# Initialize logging
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.info('Logging started')

with open('config.json') as config_file:
    bot = telebot.TeleBot(json.load(config_file)['TOKEN'])
# drop config_file
config_file.close()
# logger.info(f'Bot initialized: {bot}')


async def is_complete_expression(expression):
    try:
        # If empty string then return False
        if expression.strip() == '':
            return False
        ast.parse(expression)
        return True
    except SyntaxError:
        return False

async def calcubot_security(request):
    # Decode unicode escapes before checking to prevent bypass via \uXXXX sequences
    try:
        decoded = request.encode('utf-8').decode('unicode_escape')
    except:
        decoded = request  # fallback if decode fails

    # Check is request secure:
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
    logger.info(f'expression original: {expression}')
    logger.info(f'expression to evaluate: {expression}')
    if await calcubot_security(expression):
        ExpressionOut = Popen(
            ['python3', 'calculate_'+mode+'.py', expression],
            stdout=PIPE,
            stderr=STDOUT,
            cwd='sandbox',                              # Run in sandbox directory (no config.json there)
            env={'PATH': '/usr/local/bin:/usr/bin'}  # Clean environment, no secrets inherited
        )
        stdout, stderr = ExpressionOut.communicate()
        return stdout.decode("utf-8").replace('\n','')
    else:
        return 'Request is not supported'

def sequrity(user_input):
    # functions = ["random"]

    # Sequre symbols
    s_s = "-+*/()"
    # Sequre symbols regex
    s_s_r = "[" + "".join(["\\" + s for s in s_s]) + "]"
    # Sequre number regex
    s_n_r = r"\d+.?\d*"

    twisted_number_regex = rf"[{s_n_r}{s_s_r}?]?"
    print(twisted_number_regex)

    # user_input = "4 * 6"
    user_secure_input = "".join(
        findall(
            twisted_number_regex,
            user_input.replace(" ", ""),
        )
    )
    return user_secure_input
    # try:
    #     bot_output = eval(user_secure_input)
    # except Exception as e:
    #     # log(e)
    #     bot_output = "Irrational input!"

    # print(bot_output, "=", user_input)

    
@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    message = await request.json()
#     response = """Hello,

# This bot is currently undergoing maintenance related to migration to another server and refactoring. Please wait until June 3, 2023, for the bot to resume its normal functionality.
# I appreciate that you are using this bot and thank you for your patience and understanding during this maintenance period.

# Warm regards,
# Alex"""
#     bot.send_message(message['chat']['id'], response)
#     return Response(content='ok', status_code=200)

    # Empty message
    if 'text' not in message:
        return Response(content='ok', status_code=200)
    expression = message['text']
    # Start or help
    if expression.startswith('/start') or expression.startswith('/help'):
        """link = 'https://rtlm.info/help.mp4'
        bot.send_video(message.chat.id, link,
                            reply_to_message_id=str(message))"""
        # Send help message
        response = "This is a console calculator using Python syntax. Just type your expression and get the result. For example: 2+2"
        bot.send_message(message['chat']['id'], response)
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
    # Blocked user
    if await is_blocked_user(str(message['from']['id'])):
        return Response(content='ok', status_code=200)
    
    need_to_reply = False
    # if /cl is in expression, replace /cl with ''
    if '/cl' in expression:
        expression = expression.replace('/cl', '')
        need_to_reply = True
   
    answer_max_lenght = 4095
    res = str(await secure_eval(expression, 'native'))[:answer_max_lenght]    
    response = f'{res} = {expression}'
    logging.info(f'Sending message to chat id: {message["chat"]["id"]}, response: {response}')
    if need_to_reply:
        bot.send_message(message['chat']['id'], response, reply_to_message_id=message['message_id'])
    else:
        bot.send_message(message['chat']['id'], response)
    
    return Response(content='ok', status_code=200)


# Post inline query
@app.post("/inline")
async def call_inline(request: Request, authorization: str = Header(None)):
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

