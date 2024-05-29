from fastapi import FastAPI, Request, Header # , HTTPException
from fastapi.responses import JSONResponse # , FileResponse
import logging
import subprocess
import ast
import telebot
from telebot.types import ReplyParameters
import os

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

bot_token = os.environ['BOT_TOKEN']
bot = telebot.TeleBot(bot_token)

# {'message_id': 11015390, 'from': {'id': 106129214, 'is_bot': False, 'first_name': 'Alex', 'username': 'format37', 'language_code': 'en', 'is_premium': True}, 'chat': {'id': 106129214, 'first_name': 'Alex', 'username': 'format37', 'type': 'private'}, 'date': 1716907673, 'text': '1+6'}

class From:
    def __init__(self, from_user):
        self.id = from_user['id']
        self.is_bot = from_user['is_bot']
        self.first_name = from_user['first_name']
        self.username = from_user['username']
        self.language_code = from_user['language_code']
        self.is_premium = from_user['is_premium']

class Chat:
    def __init__(self, chat):
        self.id = chat['id']
        self.first_name = chat['first_name']
        self.username = chat['username']
        self.type = chat['type']

class Message:
    def __init__(self, message):
        logger.info(f'### [Message]: {str(message)}')
        
        self.message_id = message['message_id']        
        
        self.from_user = From(message['from'])
        self.chat = Chat(message['chat'])

        self.text = message['text']
        self.date = message['date']
        self.type = 'message'



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
    # logger.info(f'call_message. bot: {str(bot)}')
    message = await request.json()
    logger.info(f'[call_message]: {str(message)}')

    maintance_message = """Hello,

This bot is currently undergoing maintenance related to migration to another server and refactoring. Please wait until June 3, 2023, for the bot to resume its normal functionality.
I appreciate that you are using this bot and thank you for your patience and understanding during this maintenance period.

Warm regards,
Alex"""

    bot.send_message(message['chat']['id'], response)

    # return JSONResponse(content={
    #         "type": "empty",
    #         "body": ''
    #     })    

    # Empty message
    if 'text' not in message:
        pass
        # return JSONResponse(content={
        #     "type": "empty",
        #     "body": ''
        # })    
    expression = message['text']
    # Start or help
    if expression.startswith('/start') or expression.startswith('/help'):
        pass
        """link = 'https://rtlm.info/help.mp4'
        bot.send_video(message.chat.id, link,
                            reply_to_message_id=str(message))"""
        # return JSONResponse(content={
        #     "type": "text",
        #     "body": 'This is a Python interpreter. Just type your expression and get the result. For example: 2+2'
        # })
    start_from_cl = expression.startswith('/cl')
    # Not private chat
    if not start_from_cl and not message['chat']['type'] == 'private':
        pass
        # return JSONResponse(content={
        #     "type": "empty",
        #     "body": ''
        # })
    # Blocked user
    if await is_blocked_user(str(message['from']['id'])):
        return JSONResponse(content={
            "type": "empty",
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
            pass
            # return JSONResponse(content={
            #     "type": "text",
            #     "body": body
            # })
        else:
            logger.info(f'[start_from_cl] User: {message["from"]["id"]} Request: {expression}')

    
    answer_max_lenght = 4095
    user_id = str(message['from']['id'])
    res = str(await secure_eval(expression, 'native'))[:answer_max_lenght]    
    response = f'{res} = {expression}'
    prefix = 'cl ' if start_from_cl else ''
    reply_to_message_id = message['message_id']
    # logging.info(f'{prefix}User: {user_id} Request: {expression} Response: {response}, message_id: {message_id}')
    
    # message_instance = Message(message)
    # bot.reply_to(message_instance, response)
    reply_parameters = ReplyParameters(message_id=reply_to_message_id)
    # bot.send_message(
    #     chat_id=message['chat']['id'],
    #     text="This is a reply to your message.",
    #     reply_parameters=reply_parameters
    # )
    logging.info(f'Sending message to chat id: {message["chat"]["id"]}, response: {response}')
    logger.info(f'chat id type: {type(message["chat"]["id"])}')
    logger.info(f'response type: {type(response)}')
    bot.send_message(message['chat']['id'], response)

    # return JSONResponse(content={
    #     "type": "text",
    #     "body": response
    # })
    # Return empty
    

    return JSONResponse(content={
            "type": "empty",
            "body": ''
        })

    
# Post inline query
@app.post("/inline")
async def call_inline(request: Request, authorization: str = Header(None)):
    message = await request.json()
    # from_user_id = inline_query.from_user.id
    # inline_query_id = inline_query.id
    from_user_id = message['from_user_id']
    inline_query_id = message['inline_query_id']
    expression = message['query']
    # Blocked user
    if await is_blocked_user(from_user_id):
        return JSONResponse(content={
            "type": "inline",
            "body": []
        })
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
        # result_message = json.loads(result.text)
        # answer = result_message['body']
        # if result_message['type'] != 'inline':
        #     logger.error(f'Inline: Invalid response type: {result_message["type"]}')
        #     return JSONResponse(content={"status": "ok"})
        inline_elements = []
        for i in range(len(answer)):    
            element = telebot.types.InlineQueryResultArticle(
                str(i),
                answer[i],
                telebot.types.InputTextMessageContent(answer[i]),
            )
            inline_elements.append(element)
        
        logger.info(f'[answer_inline_query] inline_query_id: {inline_query_id} inline_elements: {inline_elements}')
        bot.answer_inline_query(
            inline_query_id,
            inline_elements,
            cache_time=0,
            is_personal=True
        )
    except Exception as e:
        logger.error(f'User: {from_user_id} Inline request: {expression}  Error processing inline query: {str(e)}')

    # return JSONResponse(content={
    #         "type": "inline",
    #         "body": answer
    #         })

    # Return empty
    return JSONResponse(content={
            "type": "empty",
            "body": ''
        })

