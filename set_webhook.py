import telebot
import json
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():

    with open('config.json') as config_file:
            config = json.load(config_file)

    bot = telebot.TeleBot(config['TOKEN'])

    with open('config.json') as config_file:
            config = json.load(config_file)

    server_api_uri = config['SERVER_API_URI']
    server_file_url = config['SERVER_FILE_URL']
    if server_api_uri != '':
        telebot.apihelper.API_URL = server_api_uri
        logger.info(f'Setting API_URL: {server_api_uri} for bot {config["TOKEN"]}')
    if server_file_url != '':
        telebot.apihelper.FILE_URL = server_file_url
        logger.info(f'Setting FILE_URL: {server_file_url} for bot {config["TOKEN"]}')

    webhook_url = f"{config['WEBHOOK_HOST']}:{config['WEBHOOK_PORT']}/{config['TOKEN']}/"
    logger.info(f'Setting webhook url: {webhook_url}')

    bot.remove_webhook()
    with open('/cert/webhook_cert.pem', 'rb') as cert_file:
        certificate = telebot.types.InputFile(cert_file)
    bot.set_webhook(url=webhook_url, max_connections=100, certificate=certificate)

if __name__ == '__main__':
    main()
