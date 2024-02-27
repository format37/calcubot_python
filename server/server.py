from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse, FileResponse
import os
import logging
import json
import re
import pandas as pd
import matplotlib.pyplot as plt

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
    return JSONResponse(content={
        "type": "text",
        "body": str(answer)
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
