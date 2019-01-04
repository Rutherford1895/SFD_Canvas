"""
Main function of the program
"""

from dtw import dtw
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from similarityCalc import similarity_calc
from sdClasses import Stock, Flow, Aux, Time
import globalElements as glbele

glbele._init()

'''
from tkinter import *

class Panel(Frame):
    def __init__(self,master):
        super().__init__(master)
        self.master = master
        self.pack(fill=BOTH,expand=1)

if __name__ == '__main__':
    root = Tk()
    wid = 1152
    hei = 864
    root.wm_title("Conceptualization Panel")
    root.geometry(str(wid)+"x"+str(hei)+"+100+100")
    Panel = Panel(root)
    root.mainloop()
'''

'''
case_numerical_data_filename = './case/tea_cup_model.csv'
case_numerical_data = pd.read_csv(case_numerical_data_filename)

tea_cup_behavior = np.array(case_numerical_data["tea-cup"].tolist()).reshape(-1,1)
print(tea_cup_behavior)

similarity_calc(tea_cup_behavior)
'''

glbele.set_value('stock1', Stock(name='stock1', x=489, y=245, eqn=str(100), inflow='flow1'))
glbele.set_value('flow1', Flow(name='flow1', x=381.75, y=245, pts=[(285, 245), (466.5, 245)], eqn="(globalElements.get_value('goal1')()-globalElements.get_value('stock1')())/globalElements.get_value('at1')()"))
glbele.set_value('at1', Aux(name='at1', x=341.5, y=156.5, eqn=str(5)))
glbele.set_value('goal1', Aux(name='goal1', x=348, y=329, eqn=str(1)))

glbele.set_value('time1', Time(end=25, start=1, dt=0.125))

dependencies = []
dependencies.append({'flow1': ['stock1', 'at1', 'goal1']})

glbele.get_value('flow1')()
'''
for key in variables.keys():
    print("Element: ", key)
    variables[key]()
'''


# Generate lists of flows and stocks

flows = {}
stocks = []
for element in glbele.get_keys():
    if type(glbele.get_value(element)) == Flow:
        flows[element] = 0
    if type(glbele.get_value(element)) == Stock:
        stocks.append(element)

print(flows)
print(stocks)

# Run the model

for step in range(glbele.get_value('time1').steps):
    print('After step: ', step)

    # 1. Calculate all flows as recursion, which trace back to stocks or exogenous params.
    for flow in flows:
        flows[flow] = glbele.get_value(flow)()
        print(flow, flows[flow])

    # 2. Change stocks with flows
    for stock in stocks:
        try:
            glbele.get_value(stock).change_in_stock(flows[glbele.get_value(stock).inflow]*glbele.get_value('time1').dt)
        except:
            pass
        try:
            glbele.get_value(stock).change_in_stock(flows[glbele.get_value(stock).outflow]*glbele.get_value('time1').dt*(-1))
        except:
            pass

    glbele.get_value('time1').current_step += 1

plt.plot(glbele.get_value('stock1').behavior)
plt.show()

