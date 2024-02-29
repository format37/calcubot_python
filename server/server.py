from fastapi import FastAPI, Request, Header # , HTTPException, 
from fastapi.responses import JSONResponse # , FileResponse
# import os
import logging
import json
# import re
# import pandas as pd
# import matplotlib.pyplot as plt
import subprocess
import telebot
# Initialize FastAPI
app = FastAPI()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@app.get("/test")
async def call_test():
    logger.info('call_test')
    return JSONResponse(content={"status": "ok"})

async def secure_eval(expression, mode):
    ExpressionOut = subprocess.Popen(
    ['python3', 'calculate_'+mode+'.py',expression],
    stdout=subprocess.PIPE, 
    stderr=subprocess.STDOUT)
    stdout,stderr = ExpressionOut.communicate()
    return( stdout.decode("utf-8").replace('\n','') )

@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    # logger.info('call_message')
    message = await request.json()
    if 'text' not in message:
        return JSONResponse(content={
            "type": "text",
            "body": ''
        })
    expression = message['text']
    start_from_cl = expression.startswith('/cl ')
    if not start_from_cl and not message['chat']['type'] == 'private':
        return JSONResponse(content={
            "type": "text",
            "body": ''
        })

    """"""
    
    
    # logger.info(f'expression: {expression} start_from_cl: {start_from_cl}')
    # if start_from_cl or message['chat']['type'] == 'private':
    if start_from_cl:
        expression = expression[4:]
    answer_max_lenght = 4095
    user_id = str(message['from']['id'])
    # logging.info(f'User: {user_id} Request: {expression}')
    res = str(await secure_eval(expression, 'native'))[:answer_max_lenght]    
    response = f'{res} = {expression}'
    # Logging info to docker logs: User and response
    logging.info(f'User: {user_id} Request: {expression} Response: {response}')
    return JSONResponse(content={
        "type": "text",
        "body": response
    })
    
# Post inline query
@app.post("/inline")
async def call_inline(request: Request, authorization: str = Header(None)):
    logger.info('call_inline')
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    if token:
        # logger.info(f'Bot token: {token}')
        pass
    else:
        # answer = 'Bot token not found. Please contact the developer.'
        """return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })"""
        return JSONResponse(content={
            "type": "empty",
            "body": ''
            })
    logger.info(f'Bot token: {token}')

    message = await request.json()
    bot = telebot.TeleBot(token)
    from_user_id = message['from_user_id']
    inline_query_id = message['inline_query_id']
    expression = message['query']

    logger.info(f'User: {from_user_id} Request: {expression}')

    answer_max_lenght       = 4095
    res = str(await secure_eval(expression, 'inline'))[:answer_max_lenght]
    answer  = [
                res + ' = ' + expression,
                expression + ' = ' + res,
                res
            ]
    inline_elements = []
    for i in range(len(answer)):    
        element = telebot.types.InlineQueryResultArticle(
            '0',
            answer[i],
            telebot.types.InputTextMessageContent(answer[0]),
        )
        inline_elements.append(element)
    
    bot.answer_inline_query(
        inline_query_id,
        inline_elements,
        cache_time=0,
        is_personal=True
    )

    """message_text = json.dumps(answer)
    logger.info(f'For user: {from_user_id} Inline result: {message_text}')

    title = 'Solution'
    # message_text = 'System is in a maintenance state. Please wait until Feb. 29 2024'    
    return JSONResponse(content={
        "title": title,
        "message_text": message_text,
        })"""
