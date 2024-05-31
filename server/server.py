from fastapi import FastAPI, Request, Header, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import logging
import subprocess
import ast
import telebot
import json

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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info('Logging started')

with open('config.json') as config_file:
    bot = telebot.TeleBot(json.load(config_file)['TOKEN'])
# drop config_file
config_file.close()
logger.info(f'Bot initialized: {bot}')


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
    # Check is request sequre:
    for word in calcubot_unsecure_words:
        if word in request:
            return False
    return True

async def is_blocked_user(user_id):
    return user_id in blocked_users

@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})

async def secure_eval(expression, mode):
    if await calcubot_security(expression):
        ExpressionOut = subprocess.Popen(
        ['python3', 'calculate_'+mode+'.py',expression],
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT)
        stdout,stderr = ExpressionOut.communicate()
        return( stdout.decode("utf-8").replace('\n','') )
    else:
        return 'Request is not supported'
    
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

