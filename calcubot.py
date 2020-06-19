import telebot
import math
import pandas
import numpy
import random
from telebot import types
import re

def calcubot_init(WEBHOOK_HOST,WEBHOOK_PORT,WEBHOOK_SSL_CERT, SCRIPT_PATH):

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

def calcubot_about():
	return "\
Expression words are limited for security reasons.\n\
Available are listed here:\n\
https://github.com/format37/calcubot_python/blob/master/words.txt\n\
If you feel that you need other words or any bugs found, just write me PM.\n\
Alexey Yurasov\n\
@format37"


def calcubot_help():
	return "\
Hi there!\n\
I am console calculator, based on python3 eval() function.\n\
There are 3 ways to calculate an expression:\n\
1. In personal message to me:\n\
2+2\n\
2. In group:\n\
/cl 2+2\n\
3. Inline mode. In any group or personal message to any user:\n\
@calcubot 2+2\n\
And then select wich answer to send.\n\
Good luck!"

def calcubot_eval(inline, expression,god_mode,granted_words):
	try:
		god_mode	= False
		answer_max_lenght	= 4096
		check_result	= check(expression,answer_max_lenght,god_mode,granted_words)
		if check_result=='':
			res = eval(expression)			

			if inline:
				answer	= [
					(str(res) + ' = ' + expression)[:answer_max_lenght],
					expression + ' = ' + str(res)[:answer_max_lenght],
					str(res)[:answer_max_lenght]
				]
				r0 = types.InlineQueryResultArticle('0', answer[0], types.InputTextMessageContent( answer[0] ))
				r1 = types.InlineQueryResultArticle('1', answer[1], types.InputTextMessageContent( answer[1] ))
				r2 = types.InlineQueryResultArticle('2', answer[2], types.InputTextMessageContent( answer[2] ))
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
			r = types.InlineQueryResultArticle('0', str(e), types.InputTextMessageContent( str(e)+': '+expression ))
			return [r]
		else:
			return e

def calcubot_words(SCRIPT_PATH):
	with open(SCRIPT_PATH+'words.txt','r') as words_file:
		words=words_file.read().splitlines()
	return words
	
		
def check(expression, answer_max_lenght, god_mode, granted_words):
	
	# len
	if len(expression)>answer_max_lenght:
		return 'Expression lenght exceeds '+answer_max_lenght+' symbols'
	
	if god_mode:
		return ''	
	
	# symbols
	not_letters	= ",.0123456789 ()[]{}:'+-*/\="+'"'
	letters	= "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
	contains_letters	= False
	granted_symbols	= letters + not_letters
	for sym in [expression[i] for i in range(len(expression))]:
		if granted_symbols.find(sym)==-1:
			return 'Declined symbol: '+sym
		if not contains_letters and not letters.find(sym)==-1:
			contains_letters=True
	
	if not contains_letters:
		return ''
	
	# words
	words = re.findall(r'\w+', expression)
	expression_words=[]
	for word in words:
		if len(word)>1:
			check_word	= True
			for letter in [word[i] for i in range(len(word))]:
				if letter in [letters[i] for i in range(len(letters))]:
					pass
				else:
					check_word	= False
			if check_word:
				expression_words.append(word)
	
	for expression_word in expression_words:
		if expression_word not in granted_words:
			return 'Declined word: '+expression_word			
		
	return ''