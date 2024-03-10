from fastapi import FastAPI, Request, Header # , HTTPException
from fastapi.responses import JSONResponse # , FileResponse
import logging
import subprocess
# import re
import ast

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
        'getattr',
        'with',
        'token'
    ]

incomplete_expression_patterns = [
    r'\(\)',  # empty parentheses
    r'\([^\)]*$',  # unclosed parenthesis
    r'^[^\(]*\)',  # unopened parenthesis
    r'(?<!\*)\*{3,}(?!\*)',  # sequences of 3 or more '*' that are not '**'
    r'[-+*/%]$',  # expression ends with an operator
    r'^[*/+%]',  # expression starts with non-sign operator
    r'\d*\.\d*\.',  # multiple decimal points in a number
    r'\.\D',  # decimal point not followed by a digit
    r'\D\.',  # decimal point not preceded by a digit
    r'(?<=[^\d\s])(//)(?=[^\d\s])',  # '//' not between two numbers
]

# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

"""async def is_complete_expression(expression):
    if expression.strip() == '':
        return False
    for pattern in incomplete_expression_patterns:
        if re.search(pattern, expression):
            return False
    return True"""
async def is_complete_expression(expression):
    try:
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
    if 'text' not in message:
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
    start_from_cl = expression.startswith('/cl')
    if not start_from_cl and not message['chat']['type'] == 'private':
        return JSONResponse(content={
            "type": "text",
            "body": ''
        })

    if start_from_cl:
        expression = expression[4:]
        if expression.strip() == '':
            if message['chat']['type'] == 'private':
                body = 'This is a Python interpreter. Just type your expression and get the result. For example: 2+2'
            else:
                body = 'This is a Python interpreter. Just type your expression and get the result. For example: /cl 2+2'
            logger.info(f'[start_from_cl] User: {message["from"]["id"]} Request: {expression}')
            return JSONResponse(content={
                "type": "text",
                "body": body
            })
        else:
            logger.info(f'[start_from_cl] User: {message["from"]["id"]} Request: {expression}')
    answer_max_lenght = 4095
    user_id = str(message['from']['id'])
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
    message = await request.json()
    from_user_id = message['from_user_id']
    expression = message['query']

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
    return JSONResponse(content={
            "type": "inline",
            "body": answer
            })
