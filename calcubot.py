import telebot
from telebot import types

def calcubot_init(WEBHOOK_HOST,WEBHOOK_PORT,WEBHOOK_SSL_CERT):

	SCRIPT_PATH     = '/home/format37_gmail_com/projects/calcubot_python/'

	with open(SCRIPT_PATH+'token.key','r') as file:
		API_TOKEN=file.read().replace('\n', '')
		file.close()
	calcubot = telebot.TeleBot(API_TOKEN)

	WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
	WEBHOOK_URL_PATH = "/{}/".format(API_TOKEN)

	# Remove webhook, it fails sometimes the set if there is a previous webhook
	calcubot.remove_webhook()

	# Set webhook
	wh_res = calcubot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,certificate=open(WEBHOOK_SSL_CERT, 'r'))
	print('calcubot webhook set',wh_res)
	print(WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)

	return calcubot

def calcubot_eval(inline, expression):
	try:
		res = eval(expression)
		
		if inline:
			r0 = types.InlineQueryResultArticle('0', 'Result0', types.InputTextMessageContent( str(res) + ' = ' + expression ))
			r1 = types.InlineQueryResultArticle('1', 'Result1', types.InputTextMessageContent( expression + ' = ' + str(res) ))
			r2 = types.InlineQueryResultArticle('2', 'Result2', types.InputTextMessageContent( str(res) ))
			return [r0,r1,r2]
		else:
			return str(res) + ' = ' + expression
		
	except Exception as e:
		
		if inline:
			r = types.InlineQueryResultArticle('0', 'ResultE', types.InputTextMessageContent( e ))
			return [e]
		else:
			return e