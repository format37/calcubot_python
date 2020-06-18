import telebot
import math
import pandas as pd
import numpy as np
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
		answer_max_lenght	= 4096
		check_result	= check(expression,answer_max_lenght)
		if check_result=='':
			res = eval(expression)			

			if inline:
				answer	= [
					(str(res) + ' = ' + expression)[:answer_max_lenght],
					expression + ' = ' + str(res)[:answer_max_lenght],
					str(res)[:answer_max_lenght]
				]
				r0 = types.InlineQueryResultArticle('0', answer[0][:30], types.InputTextMessageContent( answer[0] ))
				r1 = types.InlineQueryResultArticle('1', answer[1][:30], types.InputTextMessageContent( answer[1] ))
				r2 = types.InlineQueryResultArticle('2', answer[2][:30], types.InputTextMessageContent( answer[2] ))
				return [r0,r1,r2]
			else:
				return (str(res) + ' = ' + expression)[:answer_max_lenght]
		else:
			if inline:
				answer	= [check_result]
				r0 = types.InlineQueryResultArticle('0', answer[0], types.InputTextMessageContent( answer[0] ))
				return [r0]
			else:
				return check_result
		
	except Exception as e:
		
		if inline:
			r = types.InlineQueryResultArticle('0', str(e), types.InputTextMessageContent( str(e) ))
			return [r]
		else:
			return e
		
def check(expression,answer_max_lenght):
	
	if len(expression)>answer_max_lenght:
		return 'expression lenght exceeds '+answer_max_lenght+' symbols'
	
	not_letters	= ",.0123456789 ()[]{}:'+-*/="+'"'
	granted_symbols	= "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"+not_letters
	for ex in [expression[i] for i in range(len(expression))]:
		if granted_symbols.find(ex)==-1:
			return 'wrong symbol: '+ex
		
	return ''