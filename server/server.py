#!/usr/bin/env python
# -*- coding: utf-8 -*-
# import ssl
import os
# from urllib import request
import requests
from aiohttp import web
import telebot
import json
import logging
# import pandas as pd
from datetime import datetime as dt
import re
# import pickle
# import csv
# import tempfile
# import uuid

# init logging
logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.WARNING)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

WEBHOOK_HOST = os.environ.get('WEBHOOK_HOST', '')
# 443, 80, 88 or 8443 (port need to be 'open')
# WEBHOOK_PORT = os.environ.get('WEBHOOK_PORT', '')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr
# WEBHOOK_SSL_CERT = 'webhook_cert.pem'
# WEBHOOK_SSL_PRIV = 'webhook_pkey.pem'

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

async def call_test(request):
    logging.info('call_test')
    content = "get ok"
    return web.Response(text=content, content_type="text/html")


def default_bot_init(config):
    logger.info(f'default_bot_init')
    API_TOKEN = config['TOKEN']
    bot_object = telebot.TeleBot(API_TOKEN)

    # WEBHOOK_URL_BASE = "http://{}:{}".format(
    #     os.environ.get('WEBHOOK_HOST', ''),
    #     os.environ.get('WEBHOOK_PORT', '')
    # )
    # WEBHOOK_URL_PATH = "/{}/".format(API_TOKEN)
    webhook_url = f"{config['WEBHOOK_URL']}/{config['TOKEN']}/"
    logger.info(f'Setting webhook url: {webhook_url}')

    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot_object.remove_webhook()

    # Set webhook
    # wh_res = bot_object.set_webhook(
    #     url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH, certificate=open(WEBHOOK_SSL_CERT, 'r'))
    # print(bot_token_env, 'webhook set', wh_res)
    wh_res = bot_object.set_webhook(url=webhook_url, max_connections=100)
    # print('webhook set', wh_res)
    logger.info(f'webhook set: {wh_res}')
    # print(WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)

    return bot_object


# Process webhook calls
async def handle(request):
    # for bot in bots:
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()

    return web.Response(status=403)


with open('config.json') as config_file:
    config = json.load(config_file)

# === calcubot ++
bot = default_bot_init(config)
# bots.append(calcubot)

# Global dictionary for blocked users
calcubot_blocked_users = {}

# def calcubot_sequrity(request, user_id):
#     # Check is request sequre:
#     for word in calcubot_unsecure_words:
#         if word in request:
#             add_to_blocked_csv(user_id)
#             return False
#     return True


# def collect_logs():
#     try:
#         # read all files in logs/
#         path = 'calcubot_logs/'
#         files = os.listdir(path)

#         # create a list of dataframes
#         dfs = []
#         for file in files:
#             with open(path + '/' + file, 'r') as f:
#                 # read file to a list of strings
#                 lines = f.readlines()
#                 user = file[:-4]
#                 text = ''
#                 # create a list of lists
#                 for line in lines:
#                     # check, is line starts from re like: 2022-10-27 13:33:43.906742;
#                     if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6};', line):
#                         if len(text) > 0:
#                             record = [[user, date, text]]
#                             df = pd.DataFrame(
#                                 record, columns=['user', 'date', 'request'])
#                             dfs.append(df)
#                         first_semicolon = line.find(';')
#                         left = line[:first_semicolon]
#                         date = dt.strptime(left, '%Y-%m-%d %H:%M:%S.%f')
#                         # print(date)
#                         text = line[first_semicolon + 1:]
#                     else:
#                         text += line
#                 if len(text) > 0:
#                     record = [[user, date, text]]
#                     df = pd.DataFrame(
#                         record, columns=['user', 'date', 'request'])
#                     dfs.append(df)

#         # concat all dfs to a single one
#         df = pd.concat(dfs)
#         df.to_csv('requests.csv')
#         return 'requests.csv'
#     except Exception as e:
#         logger.error(e)
#         return 'error'

@bot.message_handler(commands=['help', 'start'])
def send_help(message):
    # if granted_user(message.from_user.id):
        # link = 'https://service.icecorp.ru/help.mp4'
        # calcubot.send_video(message.chat.id, link,
        #                     reply_to_message_id=str(message))
    bot.send_message(message.chat.id, '2+2')


@bot.message_handler(func=lambda message: True, content_types=['text'])
def calcubot_send_user(message):
    # if granted_user(message.from_user.id):
    #     url = 'http://localhost:'+os.environ.get('CALCUBOT_PORT')+'/message'
    #     reaction = True
    #     # check is it group ?
    #     if message.chat.type == 'group' or message.chat.type == 'supergroup':
    #         # check, does message contains '/cl ' ?
    #         if not message.text.startswith('/cl '):
    #             reaction = False

    #     if message.from_user.id == 106129214 and message.text.startswith('/logs'):
    #         file = collect_logs()
    #         if file == 'error':
    #             calcubot.reply_to(message, 'error')
    #         else:
    #             calcubot.send_document(message.chat.id, open(file, 'rb'))
    #             reaction = False

    #     if reaction:
    #         reaction = calcubot_sequrity(message.text, message.from_user.id)
    #         if not reaction:
    #             calcubot.reply_to(message, 'You are blocked for a day')

    #     if reaction:
    #         try:
    #             # append datetime and expression to calcubot_logs/[user_id].csv
    #             # splitter is ;
    #             with open('calcubot_logs/'+str(message.from_user.id)+'.csv', 'a') as f:
    #                 f.write(str(dt.now())+';'+str(message.text)+'\n')
    #         except Exception as e:
    #             logger.error(e)
                
    #         data = {
    #             "message": message.text,
    #             "user_id": message.from_user.id,
    #             "inline": 0
    #         }
    #         request_str = json.dumps(data)
    #         answer = json.loads(requests.post(url, json=request_str).text)
    #         calcubot.reply_to(message, answer)
    # else:
    bot.reply_to(message, 'Service unavailable')


@bot.inline_handler(func=lambda chosen_inline_result: True)
def calcubot_query_text(inline_query):
    # if granted_user(inline_query.from_user.id) and calcubot_sequrity(inline_query.query, inline_query.from_user.id):

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
        )  # updated
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
    # else:
    #     answer = ['Service unavailable']
    #     responce = [
    #         telebot.types.InlineQueryResultArticle(
    #             'result',
    #             answer[0],
    #             telebot.types.InputTextMessageContent(answer[0])
    #         )
    #     ]
    #     calcubot.answer_inline_query(inline_query.id, responce)

# === calcubot --

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
        host=WEBHOOK_LISTEN,
        port=config['WEBHOOK_PORT'],
        # ssl_context=context
    )


if __name__ == "__main__":
    main()
