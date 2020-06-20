from scipy.interpolate import make_interp_spline, BSpline
from matplotlib import pyplot as plt
import numpy
import math
import uuid

from calcubot import calcubot_plot,calcubot_words

CALCUBOT_WORDS = calcubot_words(CALCUBOT_SCRIPT_PATH)
msg='[ [math.sin(i)*pow(i,4) for i in range(10,30)],[math.sin(-i)*pow(i,4) for i in range(10,30)] ]'
answer,filepath	= calcubot_plot(CALCUBOT_SCRIPT_PATH, msg,True,CALCUBOT_WORDS)
print(answer,filepath)

'''
def plot(SCRIPT_PATH,in_y):
    fig = plt.figure()
    for line_number in range(0,len(in_y)):
        data_x = numpy.array( [i for i in range(0,len(in_y[line_number]))] )
        data_y = numpy.array(in_y[line_number])
        xnew = numpy.linspace(data_x.min(),data_x.max(),300) #300 represents number of points to make between T.min and T.max
        spl = make_interp_spline(data_x, data_y) #BSpline object
        power_smooth = spl(xnew)
        plt.plot(xnew,power_smooth)
    
    #fig.show()
    filename = str(uuid.uuid4()) + '.png'
    fig.savefig(SCRIPT_PATH + 'plots/' + filename, dpi=100)
    plt.close()
    
plot('/home/format37_gmail_com/projects/calcubot_python/', [ [math.sin(i)*pow(i,4) for i in range(10,30)],[math.sin(-i)*pow(i,4) for i in range(10,30)] ])
'''


