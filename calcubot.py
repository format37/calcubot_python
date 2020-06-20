import telebot
import math
import pandas
import numpy
import random
from telebot import types
import re
from scipy.interpolate import make_interp_spline, BSpline
from matplotlib import pyplot as plt
import uuid

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
If you feel require to add new words or any bugs found, just write me PM.\n\
Alex\n\
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

def calcubot_plot(SCRIPT_PATH,expression,god_mode,granted_words):

	try:
		message=''
		answer_max_lenght	= 4095
		check_result	= check(expression,answer_max_lenght,god_mode,granted_words)
		if check_result=='':
			in_y = eval(expression)
			fig = plt.figure()
			for line_number in range(0,len(in_y)):
				data_x = numpy.array( [i for i in range(0,len(in_y[line_number]))] )
				data_y = numpy.array(in_y[line_number])
				xnew = numpy.linspace(data_x.min(),data_x.max(),300) #300 represents number of points to make between T.min and T.max
				spl = make_interp_spline(data_x, data_y) #BSpline object
				power_smooth = spl(xnew)
				plt.plot(xnew,power_smooth)

			filename = str(uuid.uuid4()) + '.png'
			filepath = SCRIPT_PATH + 'plots/' + filename
			fig.savefig(filepath, dpi=100)
			plt.close()
		else:
			return message,''
		
		return message,filepath
		
	except Exception as e:		
		return str(e),''

def calcubot_eval(inline, expression,god_mode,granted_words):
	try:
		answer_max_lenght	= 4095
		check_result	= check(expression,answer_max_lenght,god_mode,granted_words)
		if check_result=='':
			
			parts = expression.split('%%')
			if len(parts)<2:
				# simple expression
				res = eval(expression)
			else:
				# expressions included into text message (relevant only for god_mode)
				answer = []
				for i in range(0,len(parts)):
					if i%2:
						answer.append( str(eval(parts[i])) )
					else:
						answer.append(parts[i])
				res=''.join(answer)

			expression	= expression.replace('%%','')
			
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
	not_letters	= ",.0123456789 ()[]{}:'+-*&%/\="+'"'
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
