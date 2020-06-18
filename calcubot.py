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
		expression	= expression.lower()
		bad_words	= check(expression)
		if bad_words=='':
			res = eval(expression)

			if inline:
				answer	= [
					str(res) + ' = ' + expression,
					expression + ' = ' + str(res),
					str(res)
				]
				r0 = types.InlineQueryResultArticle('0', answer[0], types.InputTextMessageContent( answer[0] ))
				r1 = types.InlineQueryResultArticle('1', answer[1], types.InputTextMessageContent( answer[1] ))
				r2 = types.InlineQueryResultArticle('2', answer[2], types.InputTextMessageContent( answer[2] ))
				return [r0,r1,r2]
			else:
				return str(res) + ' = ' + expression
		else:
			if inline:
				answer	= ['Wrong symbols: '+bad_words]
				r0 = types.InlineQueryResultArticle('0', answer[0], types.InputTextMessageContent( answer[0] ))
				return [r0]
			else:
				return 'Wrong symbols: '+bad_words
		
	except Exception as e:
		
		if inline:
			r = types.InlineQueryResultArticle('0', str(e), types.InputTextMessageContent( str(e) ))
			return [r]
		else:
			return e
		
def check(expression):
	granted_symbols	= "abcdefghijklmnopqrstuvwxyz123456789()[]{}'""+-*/="
	for ex in [expression[i] for i in range(len(expression))]:
		if granted_symbols.find(ex)==-1:
			return ex
	return ''
		