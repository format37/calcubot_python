from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse, FileResponse
import os
import logging
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import subprocess

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

def secure_eval(expression, mode):
    ExpressionOut = subprocess.Popen(
    ['python3', 'calculate_'+mode+'.py',expression],
    stdout=subprocess.PIPE, 
    stderr=subprocess.STDOUT)
    stdout,stderr = ExpressionOut.communicate()
    return( stdout.decode("utf-8").replace('\n','') )

@app.post("/message")
async def call_message(request: Request, authorization: str = Header(None)):
    logger.info('call_message')

    # Return empty if message is in group
    message = await request.json()
    if not message['chat']['type'] == 'private':
        return JSONResponse(content={
                "type": "empty",
                "body": ''
            })

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    if token:
        logger.info(f'Bot token: {token}')
        pass
    else:
        answer = 'Bot token not found. Please contact the administrator.'
        return JSONResponse(content={
            "type": "text",
            "body": str(answer)
        })
    
    answer = 'System is in a maintenance state. Please wait until Feb. 29 2024'
    expression = message['text']
    if expression.startswith('/cl '):
        expression = expression[4:]
    answer_max_lenght = 4095
    user_id = str(message['from']['id'])
    logging.info(f'User: {user_id} Request: {expression}')
    res = str(secure_eval(expression, 'native'))[:answer_max_lenght]
    response = json.dumps(res + ' = ' + expression)        
    # Logging info to docker logs: User and response
    logging.info(f'User: {user_id} Response: {response}')
    return JSONResponse(content={
        "type": "text",
        "body": str(response)
    })
    
# Post inline query
@app.post("/inline")
async def call_inline(request: Request, authorization: str = Header(None)):
    logger.info('call_inline')
    message = await request.json()
    logger.info(f'inlint content: {message}')
    title = 'Maintance'
    message_text = 'System is in a maintenance state. Please wait until Feb. 29 2024'    
    return JSONResponse(content={
        "title": title,
        "message_text": message_text,
        })
