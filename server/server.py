# import os
# import requests
from aiohttp import web
import telebot
import json
import logging
import subprocess
# from datetime import datetime as dt
import asyncio
import tracemalloc
tracemalloc.start()


def default_bot_init(config):
    logger.info(f'default_bot_init')
    API_TOKEN = config['TOKEN']
    bot_object = telebot.TeleBot(API_TOKEN)

    server_api_uri = config['SERVER_API_URI']
    server_file_url = config['SERVER_FILE_URL']
    if server_api_uri != '':
        telebot.apihelper.API_URL = server_api_uri
        logger.info(f'Setting API_URL: {server_api_uri} for bot {config["TOKEN"]}')
    if server_file_url != '':
        telebot.apihelper.FILE_URL = server_file_url
        logger.info(f'Setting FILE_URL: {server_file_url} for bot {config["TOKEN"]}')

    webhook_url = f"http://{config['WEBHOOK_HOST']}:{config['WEBHOOK_PORT']}/{config['TOKEN']}/"
    logger.info(f'Setting webhook url: {webhook_url}')

    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot_object.remove_webhook()

    # Set webhook
    wh_res = bot_object.set_webhook(url=webhook_url, max_connections=100)
    logger.info(f'webhook set: {wh_res}')

    return bot_object


# Global variables ++
logging.basicConfig(level=logging.INFO)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Read unsecure words from file
with open('unsecure_words.txt') as f:
    calcubot_unsecure_words = f.readlines()
calcubot_unsecure_words = [x.strip() for x in calcubot_unsecure_words]

# Read blocked users from file
with open('blocked_users.txt') as f:
    blocked_users = f.readlines()
blocked_users = [x.strip() for x in blocked_users]

with open('config.json') as config_file:
    config = json.load(config_file)
bot = default_bot_init(config)
# Global variables --


async def call_test(request):
    logging.info('call_test')
    content = "get ok"
    return web.Response(text=content, content_type="text/html")


# Process webhook calls
async def handle(request):
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    return web.Response(status=403)


# @bot.message_handler(commands=['help', 'start'])
# def send_help(message):
#     # if granted_user(message.from_user.id):
#         # link = 'https://service.icecorp.ru/help.mp4'
#         # calcubot.send_video(message.chat.id, link,
#         #                     reply_to_message_id=str(message))
#     bot.send_message(message.chat.id, '2+2')


async def is_blocked_user(user_id):
    return user_id in blocked_users


async def calcubot_security(request):
    # Check is request sequre:
    for word in calcubot_unsecure_words:
        if word in request:
            return False
    return True


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


async def handle_message(message):
    logger.info(f'handle_message')
    await calcubot_send_user(message)

@bot.message_handler(func=lambda message: asyncio.run(handle_message(message)), content_types=['text'])
async def handle_message_wrapper(message):
    logger.info(f'handle_message_wrapper')
    pass

# @bot.message_handler(func=lambda message: True, content_types=['text'])
# @bot.message_handler(func=lambda message: asyncio.run(True), content_types=['text'])
async def calcubot_send_user(message):
    logger.info(f'calcubot_send_user')
    # Empty message+
    if 'text' not in message:
        logger.info(f'Empty message')
        pass
        # return JSONResponse(content={
        #     "type": "empty",
        #     "body": ''
        # })    
    expression = message['text']
    # Start or help
    if expression.startswith('/start') or expression.startswith('/help'):
        logger.info(f'Start or help')
        # Send message "2+2"
        bot.send_message(message.chat.id, '2+2')
        # Return ok, http 200
        return web.Response(content='ok', status_code=200)
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
        logger.info(f'Not private chat')
        pass
        # return web.Response(content='ok', status_code=200)
        # return JSONResponse(content={
        #     "type": "empty",
        #     "body": ''
        # })
    # Blocked user
    if await is_blocked_user(str(message['from']['id'])):
        logger.info(f'Blocked user: {message["from"]["id"]}')
        # Return ok, http 200
        return web.Response(content='ok', status_code=200)

    if start_from_cl:
        logger.info(f'start_from_cl expression: {expression}')
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
    # reply_parameters = ReplyParameters(message_id=reply_to_message_id)
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
    

    # return JSONResponse(content={
    #         "type": "empty",
    #         "body": ''
    #     })
    # bot.reply_to(message, 'Service unavailable')

@bot.inline_handler(func=lambda chosen_inline_result: True)
def calcubot_query_text(inline_query):

    message_text_prepared = inline_query.query.strip()
    if message_text_prepared != '':
        # url = 'http://localhost:' + \
        #     os.environ.get('CALCUBOT_PORT')+'/message'
        # data = {
        #     "message": inline_query.query,
        #     "inline": 1
        # }
        # request_str = json.dumps(data)
        # answer = json.loads(requests.post(url, json=request_str).text)

        answer = ['a', 'b', 'c']

        # answer 0
        r0 = telebot.types.InlineQueryResultArticle(
            '0',
            answer[0],
            telebot.types.InputTextMessageContent(answer[0]),
        )

        # answer 1
        r1 = telebot.types.InlineQueryResultArticle(
            '1',
            answer[1],
            telebot.types.InputTextMessageContent(answer[1]),
        )

        # answer 2
        r2 = telebot.types.InlineQueryResultArticle(
            '2',
            answer[2],
            telebot.types.InputTextMessageContent(answer[2]),
        )

        answer = [r0, r1, r2]

        bot.answer_inline_query(
            inline_query.id,
            answer,
            cache_time=0,
            is_personal=True
        )
    else:
        answer = ['Empty expression..']
        responce = [
            telebot.types.InlineQueryResultArticle(
                'result',
                answer[0],
                telebot.types.InputTextMessageContent(answer[0])
            )
        ]
        bot.answer_inline_query(inline_query.id, responce)

def main():
    logging.info('Init')
    app = web.Application()
    app.router.add_post('/{token}/', handle)
    app.router.add_route('GET', '/test', call_test)
    # Build ssl context
    # context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)
    with open('config.json') as config_file:
        config = json.load(config_file)
    logging.info('Starting')
    # Start aiohttp server
    web.run_app(
        app,
        host=config['WEBHOOK_HOST'],
        port=int(config['WEBHOOK_PORT']),
        # ssl_context=context
    )


if __name__ == "__main__":
    main()
