from fastapi import FastAPI, Request, Response
import telebot
from telebot import types
import logging
import json
import requests
import os
import time

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize FastAPI
app = FastAPI()

# Initialize bot variable
bot = None

garden_queue = -1

# Your routes would go here
@app.get("/")
async def read_root():
    return Response("ok", status_code=200)

@app.get("/test")
async def call_test():
    logger.info('Test endpoint called')
    return Response("ok", status_code=200)

# Simple text message handler function
def handle_text_message(message, bot_config):
    start_time = time.time()
    if message.chat.type != 'private' and 'group_starters' in bot_config:
        granted_message = False
        for group_starter in bot_config['group_starters']:
            if message.text.startswith(group_starter):
                granted_message = True
                break
        if not granted_message:
            return Response("ok", status_code=200)

    logger.info(f'[{len(bot_config["group_starters"])}] handle_text_message {message.chat.type} message from {message.chat.id}: {message.text}')
    body = message.json
    
    # BOT_PORT = bot_config['PORT']

    # message_url = f'http://localhost:{BOT_PORT}/message'
    # headers = {'Authorization': f'Bearer {bot.token}'}
    # result = requests.post(message_url, json=body, headers=headers, timeout=1)

    end_time = time.time()
    logger.info(f'handle_text_message: Time taken: {end_time - start_time}')

    return Response("ok", status_code=200)


def handle_inline_query(inline_query, bot_config):
    start_time = time.time()
    
    results = []
    BOT_PORT = bot_config['PORT']
    inline_query_url = f'http://localhost:{BOT_PORT}/inline'
    headers = {'Authorization': f'Bearer {bot.token}'}
    body = {
        "from_user_id": inline_query.from_user.id,
        "inline_query_id": inline_query.id,
        "query": inline_query.query
    }

    message_text = 'Inline is temporarily disabled. Please try again later.'
    curent_r = telebot.types.InlineQueryResultArticle(
        '0',
        message_text,
        telebot.types.InputTextMessageContent(message_text),
    )
    results.append(curent_r)

    bot.answer_inline_query(inline_query.id, results, cache_time=0, is_personal=True)

    end_time = time.time()
    logger.info(f'handle_inline_query: Time taken: {end_time - start_time}')
    return Response("ok", status_code=200)

# Initialize bot
async def init_bot(bot_config):
    global bot
    bot = telebot.TeleBot(bot_config['TOKEN'])

    content_types=[
        'text',
        'photo',
        'document',
        'audio',
        'video',
        'sticker',
        'contact',
        'location',
        'venue',
        'voice',
        'video_note',
        'new_chat_members',
        'left_chat_member',
        'new_chat_title',
        'new_chat_photo',
        'delete_chat_photo',
        'group_chat_created',
        'supergroup_chat_created',
        'channel_chat_created',
        'migrate_to_chat_id',
        'migrate_from_chat_id',
        'pinned_message',
        'invoice',
        'successful_payment',
        'connected_website',
        'passport_data',
        'proximity_alert_triggered',
        'dice',
        'poll',
        'poll_answer',
        'my_chat_member',
        'chat_member'
    ]
    
    @bot.message_handler(content_types=content_types)
    def message_handler(message):
        handle_text_message(message, bot_config)

    @bot.callback_query_handler(func=lambda call: True)
    def callback_query_handler(call):
        pass

    @bot.inline_handler(func=lambda query: True)
    def inline_query_handler(query):
        handle_inline_query(query, bot_config)

    with open('config.json') as config_file:
        config = json.load(config_file)

    logger.info(f'Garden Queue: {garden_queue}')

    server_api_uri = config['SERVER_API_URI']
    server_file_url = config['SERVER_FILE_URL']
    if server_api_uri != '':
        telebot.apihelper.API_URL = server_api_uri
        logger.info(f'Setting API_URL: {server_api_uri} for bot {bot_config["TOKEN"]}')
    if server_file_url != '':
        telebot.apihelper.FILE_URL = server_file_url
        logger.info(f'Setting FILE_URL: {server_file_url} for bot {bot_config["TOKEN"]}')
    
    webhook_url = f"https://{config['WEBHOOK_HOST']}:{config['WEBHOOK_PORT']}/{bot_config['TOKEN']}/"
    logger.info(f'Setting webhook url: {webhook_url}')
    if garden_queue == 0:
        bot.remove_webhook()
        with open('/cert/webhook_cert.pem', 'rb') as cert_file:
            certificate = types.InputFile(cert_file)
        bot.set_webhook(url=webhook_url, max_connections=100, certificate=certificate)
    else:
        pid = int(os.getpid())
        time_to_sleep = 1+pid/10
        logger.info(f'### Sleeping for {time_to_sleep} seconds')
        time.sleep(time_to_sleep)

@app.post("/{token}/")
async def handle_request(token: str, request: Request):
    if token == bot.token: 
        if bot is None or bot == "":
            logger.error(f'[x] handle_request: Bot is inactive')
            return Response("ok", status_code=200)
        request_body_dict = await request.json()
        try:
            update = telebot.types.Update.de_json(request_body_dict)
            bot.process_new_updates([update])
            return Response("ok", status_code=200)
        except Exception as e:
            logger.error(f'[x] handle_request: Error processing request: {str(e)}')
            return Response("ok", status_code=200)
    else:
        logger.error(f'[x] handle_request: Invalid token: {token}')
        return Response("ok", status_code=200)


def fill_id_garden():
    garden_folder = './id_garden'
    pid = os.getpid()
    logger.info(f'garden PID: {pid}')
    with open(f'{garden_folder}/{pid}', 'w') as f:
        f.write('')
    instances = os.getenv('INSTANCES', '1')
    logger.info(f'garden waiting for reaching {instances} instances')
    while len(os.listdir(garden_folder)) < int(instances):
        time.sleep(1)
    queue = sorted(os.listdir(garden_folder)).index(str(pid))
    logger.info(f'garden Queue: {queue}')
    return queue

async def main():
    global garden_queue
    garden_queue = fill_id_garden()

    with open('bot_config.json') as bot_file:
        bot_config = json.load(bot_file)

    if int(bot_config['active']):
        await init_bot(bot_config)
        logger.info(f'Bot initialized with webhook')
    else:
        logger.info(f'Bot is inactive')

@app.on_event("startup")
async def startup_event():
    await main()