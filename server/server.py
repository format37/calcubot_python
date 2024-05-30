import os
import requests
from aiohttp import web
import telebot
import json
import logging
from datetime import datetime as dt


logging.basicConfig(level=logging.INFO)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def call_test(request):
    logging.info('call_test')
    content = "get ok"
    return web.Response(text=content, content_type="text/html")


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


# Process webhook calls
async def handle(request):
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    return web.Response(status=403)

with open('config.json') as config_file:
    config = json.load(config_file)
bot = default_bot_init(config)

@bot.message_handler(commands=['help', 'start'])
def send_help(message):
    # if granted_user(message.from_user.id):
        # link = 'https://service.icecorp.ru/help.mp4'
        # calcubot.send_video(message.chat.id, link,
        #                     reply_to_message_id=str(message))
    bot.send_message(message.chat.id, '2+2')

@bot.message_handler(func=lambda message: True, content_types=['text'])
def calcubot_send_user(message):
    
    bot.reply_to(message, 'Service unavailable')

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
