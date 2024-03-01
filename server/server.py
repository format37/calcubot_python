from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import logging
import subprocess
import telebot
import os

calcubot_unsecure_words = [
        'exec',
        'import',
        'sys',
        'subprocess',
        'eval',
        'open',
        'file',
        'write',
        'read',
        'print',
        'compile'
        'globals',
        'locals',
        'builtins',
        'getattr'
    ]

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def calcubot_sequrity(request):
    # Check is request sequre:
    for word in calcubot_unsecure_words:
        if word in request:
            # add_to_blocked_csv(user_id)
            return False
    return True

@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})

async def secure_eval(expression, mode):
    if await calcubot_sequrity(expression):
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
    # logger.info('call_message')
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if token:
        pass
    else:
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })"""
        return JSONResponse(content={
            "type": "empty",
            "body": ''
            })
    message = await request.json()
    # bot = telebot.TeleBot(token)
    if 'text' not in message:
        return JSONResponse(content={
            "type": "empty",
            "body": ''
            })
    if not message['chat']['type'] == 'private':
        return JSONResponse(content={
            "type": "empty",
            "body": ''
            })
    expression = message['text']
    if expression.startswith('/start') or expression.startswith('/help'):
        """link = 'https://rtlm.info/help.mp4'
        bot.send_video(message.chat.id, link,
                            reply_to_message_id=str(message))"""
        return JSONResponse(content={
            "type": "text",
            "body": 'This is a Python interpreter. Just type your expression and get the result. For example: 2+2'
        })
    start_from_cl = expression.startswith('/cl ')
    if not start_from_cl and not message['chat']['type'] == 'private':
        return JSONResponse(content={
            "type": "text",
            "body": ''
        })

    if start_from_cl:
        expression = expression[4:]
    answer_max_lenght = 4095
    user_id = str(message['from']['id'])
    # logging.info(f'User: {user_id} Request: {expression}')
    res = str(await secure_eval(expression, 'native'))[:answer_max_lenght]    
    response = f'{res} = {expression}'
    prefix = 'cl ' if start_from_cl else ''
    logging.info(f'{prefix}User: {user_id} Request: {expression} Response: {response}')
    return JSONResponse(content={
        "type": "text",
        "body": response
    })
    
# Post inline query
@app.post("/inline")
async def call_inline(request: Request, authorization: str = Header(None)):
    # logger.info('call_inline')
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    if token:
        pass
    else:
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })"""
        return JSONResponse(content={
            "type": "empty",
            "body": ''
            })
    message = await request.json()
    bot = telebot.TeleBot(token)
    from_user_id = message['from_user_id']
    inline_query_id = message['inline_query_id']
    expression = message['query']

    answer_max_lenght       = 4095
    res = str(await secure_eval(expression, 'inline'))[:answer_max_lenght]
    answer  = [
                res + ' = ' + expression,
                expression + ' = ' + res,
                res
            ]
    logger.info(f'User: {from_user_id} Inline request: {expression} Response: {res}')
    inline_elements = []
    for i in range(len(answer)):    
        element = telebot.types.InlineQueryResultArticle(
            str(i),
            answer[i],
            telebot.types.InputTextMessageContent(answer[i]),
        )
        inline_elements.append(element)
    try:
        bot.answer_inline_query(
            inline_query_id,
            inline_elements,
            cache_time=0,
            is_personal=True
        )
    except Exception as e:
        logger.error(f'User: {from_user_id} Inline request: {expression} Response: {res} Error: {e}')
    return JSONResponse(content={
            "type": "empty",
            "body": ''
            })
