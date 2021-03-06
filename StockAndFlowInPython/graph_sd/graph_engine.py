import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
import numpy as np


# define constants
STOCK = 'stock'
FLOW = 'flow'
VARIABLE = 'variable'
PARAMETER = 'parameter'
CONNECTOR = 'connector'
ALIAS = 'alias'


# Define functions
def linear(x, a=1, b=0):
    return a * float(x) + b


def addition(x, y):
    return float(x) + float(y)


def subtraction(x, y):
    return float(x) - float(y)


def division(x, y):
    return float(x) / float(y)


def multiplication(x, y):
    return float(x) * float(y)


# Make alias for function names
LINEAR = linear
SUBTRACTION = subtraction
DIVISION = division
ADDITION = addition
MULTIPLICATION = multiplication

function_names = [LINEAR, SUBTRACTION, DIVISION, ADDITION, MULTIPLICATION]


# Define equation-text converter

name_operator_mapping = {ADDITION: '+', SUBTRACTION: '-', MULTIPLICATION: '*', DIVISION: '/'}


def equation_to_text(equation):
    if type(equation) == int or type(equation) == float:
        return str(equation)
    try:
        equation[0].isdigit()  # if it's a number
        return str(equation)
    except AttributeError:
        if equation[0] in [ADDITION, SUBTRACTION, MULTIPLICATION, DIVISION]:
            return str(equation[1]) + name_operator_mapping[equation[0]] + str(equation[2])
        elif equation[0] == LINEAR:
            return str(equation[1])


class UidManager(object):
    def __init__(self):
        self.uid = 0

    def get_new_uid(self):
        self.uid += 1
        return self.uid

    def current(self):
        return self.uid


class NameManager(object):
    def __init__(self):
        self.stock_id = 0
        self.flow_id = 0
        self.variable_id = 0
        self.parameter_id = 0

    def get_new_name(self, element_type):
        if element_type == STOCK:
            self.stock_id += 1
            return 'stock_'+str(self.stock_id)
        elif element_type == FLOW:
            self.flow_id += 1
            return 'flow_' + str(self.flow_id)
        elif element_type == VARIABLE:
            self.variable_id += 1
            return 'variable_' + str(self.variable_id)
        elif element_type == PARAMETER:
            self.parameter_id += 1
            return 'parameter_' + str(self.parameter_id)


class DataFeeder(object):  # TODO: use multi-process to create a real data buffer
    def __init__(self, data_source=None):
        if data_source is not None:
            self.initialise(data_source=data_source)

    def initialise(self, data_source):
        self.time_series = pd.read_csv(data_source)
        self.buffers_list = dict()
        self.buffers_iter = dict()

    def set_var_source(self, var_name, csv_column):
        self.buffers_list[var_name] = self.time_series[csv_column].tolist()
        self.buffers_iter[var_name] = iter(self.time_series[csv_column].tolist())

def name_handler(name):
    return name.replace(' ', '_').replace('\n', '_')


class Structure(object):
    def __init__(self, sfd=None, uid_manager=None, name_manager=None, uid_element_name=None):
        if sfd is None:
            self.sfd = nx.DiGraph()
            self.uid_manager = UidManager()
            self.name_manager = NameManager()
            self.uid_element_name = dict()
        else:
            self.sfd = sfd
            self.uid_manager = uid_manager
            self.name_manager = name_manager
            self.uid_element_name = uid_element_name

        self.default_simulation_time = 25
        self.default_dt = 0.25

        self.set_predefined_structure = {'basic_stock_inflow': self.basic_stock_inflow,
                                         'basic_stock_outflow': self.basic_stock_outflow,
                                         'first_order_positive': self.first_order_positive,
                                         'first_order_negative': self.first_order_negative
                                         }

        self.data_feeder = DataFeeder()

    def add_element(self, element_name, element_type, flow_from=None, flow_to=None, x=0, y=0, function=None, value=None, points=None, external=False):
        uid = self.uid_manager.get_new_uid()
        # this 'function' is a list, containing the function it self and its parameters
        # this 'value' is also a list, containing historical value throughout this simulation
        self.sfd.add_node(element_name, uid=uid, element_type=element_type, flow_from=flow_from, flow_to=flow_to, pos=[x, y], function=function, value=value, points=points, external=external)
        print('SdEngine: adding element:', element_name, 'function:', function, 'value:', value)

        # # automatically confirm dependencies, if a function is used for this variable
        # if function is not None and type(function) is not str:
        #     self.add_function_dependencies(element_name, function)

        self.uid_element_name[uid] = element_name

        return uid

    def add_causality(self, from_element, to_element, uid=0, angle=None, polarity=None, display=True):  # confirm one causality
        self.sfd.add_edge(from_element, to_element, uid=uid, angle=angle, polarity=polarity, display=display)  # display as a flag for to or not to display

    def add_function_dependencies(self, element_name, function):  # confirm bunch of causality found in a function
        for from_variable in function[1:]:
            if type(from_variable) == str:
                print('SdEngine: adding dependencies, from {} to {}'.format(from_variable, element_name))
                self.add_causality(from_element=from_variable, to_element=element_name, uid=self.uid_manager.get_new_uid())

    def get_element_by_uid(self, uid):
        # print("Uid_Element_Name, ", self.uid_element_name)
        return self.sfd.nodes[self.uid_element_name[uid]]

    def get_element_name_by_uid(self, uid):
        return self.uid_element_name[uid]

    def print_elements(self):
        print('SdEngine: All elements in this SFD:')
        print(self.sfd.nodes.data())

    def print_element(self, name):
        print('SdEngine: Attributes of element {}:'.format(name))
        print(self.sfd.nodes[name])

    def print_causal_links(self):
        print('SdEngine: All causal links in this SFD:')
        print(self.sfd.edges)

    def print_causal_link(self, from_element, to_element):
        print('SdEngine: Causality from {} to {}:'.format(from_element, to_element))
        print(self.sfd[from_element][to_element])

    def all_certain_type(self, element_type):
        # able to handle both single type and multiple types
        elements = list()
        if type(element_type) != list:
            element_types = [element_type]
        else:
            element_types = element_type

        for ele_tp in element_types:
            for node, attributes in self.sfd.nodes.data():
                if attributes['element_type'] == ele_tp:
                    elements.append(node)
        # print(elements, "Found for", element_types)
        return elements

    def set_external(self, element_name):
        self.sfd.nodes[element_name]["external"] = True

    def get_coordinate(self, name):
        """
        Get the coordinate of a specified variable
        :param name:
        :return: coordinate of the variable in a tuple
        """
        return self.sfd.nodes[name]['pos']

    def calculate(self, name):
        """
        Core function for simulation, based on recursion
        :param name: Name of the element to calculate
        """
        if self.sfd.nodes[name]['external'] is True:
            # if the variable is using external data source
            return next(self.data_feeder.buffers_iter[name])

        elif type(name) == int or type(name) == float:
            # if the name is actually a constant:
            return name

        elif self.sfd.nodes[name]['element_type'] == STOCK:
            # if the node is a stock
            return self.sfd.nodes[name]['value'][-1]  # just return its latest value, update afterwards.
        elif self.sfd.nodes[name]['function'] is None:
            # if the node does not have a function and not a stock, then it's constant
            # if this node is a constant, still extend its value list by its last value

            # However, if this variable is participating in more than 1 calculation, its value could be extended twice.
            # use 'visited' to fix this problem.
            if name not in self.visited:
                self.sfd.nodes[name]['value'].append(self.sfd.nodes[name]['value'][-1])
                self.visited.append(name)
            return self.sfd.nodes[name]['value'][-1]  # use its latest value
        else:  # it's not a constant value but a function  #
            # params = self.sfd.nodes[name]['function'][1:]  # extract all parameters needed by this function
            params = [param for param in self.sfd.nodes[name]['function'][1:]]  # take params without the operator
            for j in range(len(params)):  # use recursion to find the values of params, then -
                params[j] = self.calculate(params[j])  # replace the param's name with its value.
            new_value = self.sfd.nodes[name]['function'][0](*params)  # calculate the new value for this step

            # However, if this variable is participating in mor than 1 calculation, its value could be extended twice.
            # use 'visited' to solve this problem.
            if name not in self.visited:
                self.sfd.nodes[name]['value'].append(new_value)  # confirm this new value to this node's value list
                self.visited.append(name)
            return new_value  # return the new value to where it was called

    def step(self, dt=0.25):
        """
        Core function for simulation. Calculating all flows and adjust stocks accordingly based on recursion.
        """
        # have a dictionary for flows and their values in this default_dt, to be added to /subtracted from stocks afterward.
        flows_dt = dict()

        # find all flows in the model
        for element in self.all_certain_type(FLOW):  # loop through all elements in this SFD,
            flows_dt[element] = 0  # make a position for it in the dict of flows_dt, initializing it with 0

        # have a list for all visited (calculated) variables (F/V/P) in this model
        self.visited = list()

        # calculate flows
        for flow in flows_dt.keys():
            flows_dt[flow] = dt * self.calculate(flow)
        # print('All flows default_dt:', flows_dt)

        # calculate all not visited variables and parameters in this model, in order to update their value list
        # because all flows and stocks must be visited, only V and P are considered.
        for element in self.all_certain_type([VARIABLE, PARAMETER]):
            if element not in self.visited:
                self.calculate(element)

        # calculating changes in stocks
        # have a dictionary of affected stocks and their changes, for one flow could affect 2 stocks.
        affected_stocks = dict()
        for flow in flows_dt.keys():
            successors = list(self.sfd.successors(flow))  # successors of a flow into a list
            # print('Successors of {}: '.format(flow), successors)
            for successor in successors:
                if self.sfd.nodes[successor]['element_type'] == STOCK:  # flow may also affect elements other than stock
                    direction_factor = 1  # initialize
                    if successor not in affected_stocks.keys():  # if this flow hasn't been calculated, create a new key
                        if self.sfd.nodes[flow]['flow_from'] == successor:  # if flow influences this stock negatively
                            direction_factor = -1
                        elif self.sfd.nodes[flow]['flow_to'] == successor:  # if flow influences this stock positively
                            direction_factor = 1
                        else:
                            print("SdEngine: Strange! {} seems to influence {} but not found in graph's attributes.".format(flow, successor))
                        if successor in affected_stocks.keys():  # this stock may have been added by other flows
                            affected_stocks[successor] += flows_dt[flow] * direction_factor
                        else:
                            affected_stocks[successor] = flows_dt[flow] * direction_factor
                    else:  # otherwise update this flow's value on top of results of previous calculation (f2 = f1 + f0)
                        if self.sfd.nodes[flow]['flow_from'] == successor:  # if flow influences this stock negatively
                            direction_factor = -1
                        elif self.sfd.nodes[flow]['flow_to'] == successor:  # if flow influences this stock positively
                            direction_factor = 1
                        else:
                            print("SdEngine: Strange! {} seems to influence {} but not found in graph's attributes.".format(flow, successor))
                        if successor in affected_stocks.keys():  # this stock may have been added by other flows
                            affected_stocks[successor] += flows_dt[flow] * direction_factor
                        else:
                            affected_stocks[successor] = flows_dt[flow] * direction_factor

        # updating affected stocks values
        for stock in affected_stocks.keys():
            # calculate the new value for this stock and confirm it to the end of its value list
            self.sfd.nodes[stock]['value'].append(self.sfd.nodes[stock]['value'][-1] + affected_stocks[stock])
            # print('Stock ', stock, ': {:.4f}'.format(self.sfd.nodes[stock]['value'][-1]))

        # for those stocks not affected, extend its 'values' by the same value as it is
        for node in self.sfd.nodes:
            if self.sfd.nodes[node]['element_type'] == STOCK:
                if node not in affected_stocks.keys():
                    self.sfd.nodes[node]['value'].append(self.sfd.nodes[node]['value'][-1])
                    # print('Stock ', node, ': {:.4f}'.format(self.sfd.nodes[node]['value'][-1]))

    def clear_a_run(self):
        """
        Clear values for all nodes
        :return:
        """
        for node in self.sfd.nodes:
            if self.sfd.nodes[node]['element_type'] == STOCK:
                self.sfd.nodes[node]['value'] = [self.sfd.nodes[node]['value'][0]]  # for stock, keep its initial value
            else:
                if self.sfd.nodes[node]['function'] is None:  # it's a constant parameter
                    self.sfd.nodes[node]['value'] = [self.sfd.nodes[node]['value'][0]]
                else:  # it's not a constant parameter
                    self.sfd.nodes[node]['value'] = list()  # for other variables, reset its value to empty list
            # print('SdEngine: reset value of', node, 'to', self.sfd.nodes[node]['value'])

    # Add elements on a stock-and-flow level (work with model file handlers)
    def add_stock(self, name=None, equation=None, x=0, y=0):
        """
        :param name: name of the stock
        :param equation: initial value
        :param x: x
        :param y: y
        :return: uid of the stock
        """
        uid = self.add_element(name, element_type=STOCK, x=x, y=y, value=equation)
        # print('SdEngine: added stock:', name, 'to graph.')
        return uid

    def add_flow(self, name=None, equation=None, x=0, y=0, points=None, flow_from=None, flow_to=None):
        # Decide if the 'equation' is a function or a constant number
        # if type(equation) in [int, float] or type(equation[0]) in [int, float]:  # TODO: need to refine: need []?
        if type(equation[0]) in [int, float]:
            # if equation starts with a number
            function = None
            value = equation  # it's a constant
        else:
            function = equation  # it's a function
            value = list()
        if name is None:
            name = self.name_manager.get_new_name(element_type=FLOW)
        uid = self.add_element(name, element_type=FLOW, flow_from=flow_from, flow_to=flow_to, x=x, y=y, function=function, value=value, points=points)

        self.create_stock_flow_connection(name, flow_from=flow_from, flow_to=flow_to)
        # print('SdEngine: added flow:', name, 'to graph.')
        return uid

    def create_stock_flow_connection(self, flow_name, flow_from=None, flow_to=None):
        """
        Connect stock and flow.
        :param flow_name: The flow's name
        :param flow_from: The stock this flow coming from
        :param flow_to: The stock this flow going into
        :return:
        """
        # If the flow influences a stock, create the causal link
        if flow_from is not None:  # Just set up
            self.sfd.nodes[flow_name]['flow_from'] = flow_from
            self.add_causality(flow_name, flow_from, display=False, polarity='negative')
        if flow_to is not None:  # Just set up
            self.sfd.nodes[flow_name]['flow_to'] = flow_to
            self.add_causality(flow_name, flow_to, display=False, polarity='positive')

    def remove_stock_flow_connection(self, flow_name, stock_name):
        """
        Disconnect stock and flow
        :param flow_name: The flow's name
        :param stock_name: The stock this flow no longer connected to
        :return:
        """
        if self.sfd.nodes[flow_name]['flow_from'] == stock_name:
            self.sfd.remove_edge(flow_name, stock_name)
            self.sfd.nodes[flow_name]['flow_from'] = None
        if self.sfd.nodes[flow_name]['flow_to'] == stock_name:
            self.sfd.remove_edge(flow_name, stock_name)
            self.sfd.nodes[flow_name]['flow_to'] = None

    def add_aux(self, name=None, equation=None, x=0, y=0):
        # Decide if this aux is a parameter or variable
        # if type(equation) in [int, float] or type(equation[0]) in [int, float]:  # TODO: need to refine: need []?
        if type(equation[0]) in [int, float]:  # TODO: need to refine: need []?
            # if equation starts with a number, it's a parameter
            if name is None:
                name = self.name_manager.get_new_name(element_type=PARAMETER)
            uid = self.add_element(name, element_type=PARAMETER, x=x, y=y, function=None, value=equation)
        else:
            # It's a variable, has its own function
            if name is None:
                name = self.name_manager.get_new_name(element_type=VARIABLE)
            uid = self.add_element(name, element_type=VARIABLE, x=x, y=y, function=equation, value=list())
            # Then it is assumed to take information from other variables, therefore causal links should be created.
            # Already implemented in structure's add_element function, not needed here.
            # for info_source_var in equation[1]:
            #     if info_source_var in self.structures[structure_name].sfd.nodes:  # if this info_source is a var
            #         self.structures[structure_name].add_causality(info_source_var, name)
        # print('SdEngine: added aux', name, 'to graph.')
        return uid

    def get_equation(self, name):
        if self.sfd.nodes[name]['element_type'] == STOCK:
            # if the node is a stock
            return self.sfd.nodes[name]['value'][0]  # just return its first value (initial).
        elif self.sfd.nodes[name]['function'] is None:
            # if the node does not have a function and not a stock, then it's constant
            return self.sfd.nodes[name]['value'][0]  # use its latest value
        else:  # it's not a constant value but a function  #
            return self.sfd.nodes[name]['function']

    def replace_equation(self, name, new_equation):
        """
        Replace the equation of a variable.
        :param name: The name of the variable
        :param new_equation: The new equation
        :param structure_name: The structure the variable is in
        :return:
        """
        # step 1: remove all incoming connectors into this variable (node)
        # step 2: replace the equation of this variable in the graph representation
        # step 3: confirm connectors based on the new equation (only when the new equation is a function not a number
        print("SdEngine: Replacing equation of {}".format(name))
        # step 1:
        to_remove = list()
        for u, v in self.sfd.in_edges(name):
            print("In_edge found:", u, v)
            to_remove.append((u, v))
        self.sfd.remove_edges_from(to_remove)
        print("SdEngine: Edges removed.")
        # step 2:
        if type(new_equation[0]) is int or type(new_equation[0]) is float:
            # If equation starts with a number, it's a constant value
            self.sfd.nodes[name]['function'] = None
            self.sfd.nodes[name]['value'] = new_equation
            print("SdEngine: Equation replaced.")
        else:
            # It's a variable, has its own function
            self.sfd.nodes[name]['function'] = new_equation
            self.sfd.nodes[name]['value'] = list()
            print("SdEngine: Equation replaced.")
            # step 3:
            if new_equation is not None and type(new_equation) is not str:
                self.add_function_dependencies(name, new_equation)
                print("SdEngine: New edges created.")

    # Add elements to a structure in a batch (something like a script)
    # Enable using of multi-dimensional arrays.
    def add_elements_batch(self, elements):
        for element in elements:
            if element[0] == STOCK:
                self.add_stock(name=element[1],
                               equation=element[2],
                               x=element[5],
                               y=element[6],)
            elif element[0] == FLOW:
                self.add_flow(name=element[1],
                              equation=element[2],
                              flow_from=element[3],
                              flow_to=element[4],
                              x=element[5],
                              y=element[6],
                              points=element[7])
            elif element[0] == PARAMETER or element[0] == VARIABLE:
                self.add_aux(name=element[1],
                             equation=element[2],
                             x=element[5],
                             y=element[6])
            elif element[0] == CONNECTOR:
                self.add_connector(angle=element[1],
                                   from_element=element[2],
                                   to_element=element[3],
                                   polarity=element[4])

    def add_alias(self, uid, of_element, x=0, y=0):
        self.add_element(uid, element_type=ALIAS, x=x, y=y, function=of_element)
        # print('SdEngine: added alias of', of_element, 'to graph.\n')

    def delete_element(self, name):
        """
        Delete an element
        :param name:
        :return:
        """
        self.sfd.remove_node(name)
        print("SdEngine: {} is removed from the graph.".format(name))

    def add_connector(self, from_element, to_element, angle=0, polarity=None, display=True):
        uid = self.uid_manager.get_new_uid()
        self.add_causality(from_element, to_element, uid=uid, angle=angle, polarity=polarity, display=display)

    def delete_connector(self, from_element, to_element):
        self.sfd.remove_edge(from_element, to_element)

    # Set the model to a first order negative feedback loop
    def first_order_negative(self):
        # adding a structure that has been pre-defined using multi-dimensional arrays.
        self.sfd.graph['structure_name'] = 'first_order_negative'
        self.add_elements_batch([
            # 2020-05-13: I believe the [] should be kept for even numbers, for they are regarded as an equation here.
            # 0type,    1name        2value/equation                            3flow_from, 4flow_to,   5x,     6y,     7pts,
            [STOCK,     'stock0',    [100],                                     None,       None,       213,    174,    None],
            [FLOW,      'flow0',     [LINEAR, 'quotient0'],                     'stock0',   None,       302,    171,    [[236, 171], [392, 171]]],
            [VARIABLE,  'quotient0', [DIVISION, 'gap0',   'at0'],               None,       None,       302,    220,    None],
            [PARAMETER, 'goal0',     [20],                                      None,       None,       270,    300,    None],
            [VARIABLE,  'gap0',      [SUBTRACTION, 'stock0', 'goal0'],          None,       None,       252,    250,    None],
            [PARAMETER, 'at0',       [5],                                       None,       None,       362,    102,    None],
            # 0type     1angle       2from         3to          4polarity
            [CONNECTOR, 289,        'stock0',     'gap0',      'positive'],
            [CONNECTOR, 85,         'goal0',      'gap0',      'negative'],
            [CONNECTOR, 35,         'gap0',       'quotient0', 'positive'],
            [CONNECTOR, 200,        'at0',        'quotient0', 'negative'],
            [CONNECTOR, 35,         'quotient0',  'flow0',     'positive']
            ])

    # Set the model to a first order negative feedback loop
    def first_order_positive(self):
        # adding a structure that has been pre-defined using multi-dimensional arrays.
        self.sfd.graph['structure_name'] = 'first_order_positive'
        self.add_elements_batch([
            # 0type,    1name        2value/equation                            3flow_from, 4flow_to,   5x,     6y,     7pts,
            [STOCK,     'stock0',    [1],                                       None,       None,       213,    174,    None],
            [FLOW,      'flow0',     [LINEAR, 'product0'],                      None,       'stock0',   120,    172,    [[49, 172], [191, 172]]],
            [VARIABLE,  'product0',  [MULTIPLICATION, 'stock0', 'fraction0'],   None,       None,       158,    102,    None],
            [PARAMETER, 'fraction0', [0.1],                                     None,       None,       61,     97,     None],
            # 0type     1angle       2from         3to          4polarity
            [CONNECTOR, 93,         'stock0',     'product0',  'positive'],
            [CONNECTOR, 195,         'product0',   'flow0',     'positive'],
            [CONNECTOR, 38,         'fraction0',  'product0',  'positive']
        ])

    # Set the model to one stock + one outflow
    def basic_stock_outflow(self):
        self.sfd.graph['structure_name'] = 'basic_stock_outflow '
        self.add_elements_batch([
            # 0type,    1name/uid,   2value/equation/angle                      3flow_from, 4flow_to,   5x,     6y,     7pts,
            [STOCK,     'stock0',    [100],                                     None,       None,       213,    174,    None],
            [FLOW,      'flow0',     [4],                                       'stock0',   None,       302,    171,    [[236, 171], [392, 171]]],
        ])

    # Set the model to one stock + one inflow
    def basic_stock_inflow(self):
        self.sfd.graph['structure_name'] = 'basic_stock_inflow'
        self.add_elements_batch([
            # 0type,    1name/uid,   2value/equation/angle                      3flow_from, 4flow_to,   5x,     6y,     7pts,
            [STOCK,     'stock0',    [1],                                       None,       None,       375,    250,    None],
            [FLOW,      'flow0',     [4],                                       None,       'stock0',   120,    172,    [[49, 172], [191, 172]]],
        ])

    # Reset a structure
    def reset_a_structure(self):
        self.sfd.clear()

    # Simulate a structure based on a certain set of parameters
    def simulate(self, simulation_time=0, dt=0.25):
        # print('SdEngine: Simulating...')
        if simulation_time == 0:
            # determine how many steps to run; if not specified, use maximum steps
            total_steps = int(self.default_simulation_time / self.default_dt)
        else:
            total_steps = int(simulation_time/dt)

        # main iteration
        for i in range(total_steps):
            # stock_behavior.append(structure0.sfd.nodes['stock0']['value'])
            # print('Step: {} '.format(i), end=' ')
            self.step(dt)

    # Return a behavior
    def get_behavior(self, name):
        # print(self.structures[structure_name].sfd.nodes[name]['value'])
        return self.sfd.nodes[name]['value']

    # Draw results
    def display_results(self, names=None, rtn=False):
        if names is None:
            names = list(self.sfd.nodes)

        self.figure_0 = plt.figure(figsize=(6.4, 4.8),
                                   facecolor='whitesmoke',
                                   edgecolor='grey',
                                   dpi=80)

        plt.xlabel('Steps {} (Time: {} / Dt: {})'.format(int(self.default_simulation_time/self.default_dt),
                                                         self.default_simulation_time,
                                                         self.default_dt))
        plt.ylabel('Behavior')
        y_axis_minimum = 0
        y_axis_maximum = 0
        for name in names:
            if self.sfd.nodes[name]['external'] is True:
                values = self.data_feeder.buffers_list[name]
            elif self.sfd.nodes[name]['value'] is not None:  # otherwise, dont's plot
                values = self.sfd.nodes[name]['value']
            else:
                continue  # no value found for this variable
            # print("SdEngine: getting min/max for", name)
            # set the range of axis based on this element's behavior
            # 0 -> end of period (time), 0 -> 100 (y range)


            name_minimum = min(values)
            name_maximum = max(values)
            if name_minimum == name_maximum:
                name_minimum *= 2
                name_maximum *= 2
                # print('SdEngine: Centered this straight line')

            if name_minimum < y_axis_minimum:
                y_axis_minimum = name_minimum

            if name_maximum > y_axis_maximum:
                y_axis_maximum = name_maximum

            # print("SdEngine: Y range: ", y_axis_minimum, '-', y_axis_maximum)
            plt.axis([0, self.default_simulation_time / self.default_dt, y_axis_minimum, y_axis_maximum])
            # print("SdEngine: Time series of {}:".format(name))
            # for i in range(len(values)):
            #     print("SdEngine: {0} at DT {1} : {2:8.4f}".format(name, i+1, values[i]))
            plt.plot(values, label=name)
        plt.legend()
        if rtn:  # if called from external, return the figure without show it.
            return self.figure_0
        else:  # otherwise, show the figure.
            plt.show()

    # Draw graphs with customized labels and colored connectors
    def draw_graphs_with_function_value_polarity(self, rtn=False):
        self.figure2 = plt.figure(num='cld')

        plt.clf()
        # generate node labels
        node_attrs_function = nx.get_node_attributes(self.sfd, 'function')
        node_attrs_value = nx.get_node_attributes(self.sfd, 'value')
        custom_node_labels = dict()
        for node, attr in node_attrs_function.items():
            # when element only has a value but no function
            if attr is None:
                attr = node_attrs_value[node][0]
            # when the element has a function
            else:
                attr = equation_to_text(attr)
            custom_node_labels[node] = "{}={}".format(node, attr)

        # generate edge polarities
        edge_attrs_polarity = nx.get_edge_attributes(self.sfd, 'polarity')
        custom_edge_colors = list()
        for edge, attr in edge_attrs_polarity.items():
            color = 'k'  # black
            if attr == 'negative':
                color = 'b'  # blue
            custom_edge_colors.append(color)

        # generate node positions
        pos = nx.get_node_attributes(self.sfd, 'pos')

        nx.draw_networkx(G=self.sfd,
                         labels=custom_node_labels,
                         font_size=10,
                         node_color='skyblue',
                         edge_color=custom_edge_colors,
                         pos=pos,
                         ax=plt.gca())

        plt.gca().invert_yaxis()
        plt.axis('off')  # turn off axis for structure display

        if rtn:
            return self.figure2
        else:
            plt.show()

    # # Draw network with FancyArrowPatch
    # # Thanks to https://groups.google.com/d/msg/networkx-discuss/FwYk0ixLDuY/dtNnJcOAcugJ
    # @staticmethod
    # def draw_network(G, pos, ax):
    #     for n in G:
    #         # print('SdEngine: Engine is drawing network element for', n)
    #         circle = Circle(pos[n], radius=5, alpha=0.2, color='c')
    #         # ax.add_patch(circle)
    #         G.node[n]['patch'] = circle
    #         x, y = pos[n]
    #         ax.text(x, y, n, fontsize=11, horizontalalignment='left', verticalalignment='center')
    #     seen = {}
    #     # TODO: Undertsand what happens here and rewrite it in a straight forward way
    #     if len(list(G.edges)) != 0:  # when there's only one stock in the model, don't draw edges
    #         for (u, v, d) in G.edges(data=True):
    #             n1 = G.node[u]['patch']
    #             n2 = G.node[v]['patch']
    #             rad = - 0.5
    #             if (u, v) in seen:
    #                 rad = seen.get((u, v))
    #                 rad = (rad + np.sign(rad)*0.1)*-1
    #             alpha = 0.5
    #             color = 'r'
    #
    #             edge = FancyArrowPatch(n1.center, n2.center, patchA=n1, patchB=n2,
    #                                    arrowstyle='-|>',
    #                                    connectionstyle='arc3,rad=%s' % rad,
    #                                    mutation_scale=15.0,
    #                                    linewidth=1,
    #                                    alpha=alpha,
    #                                    color=color)
    #             seen[(u, v)] = rad
    #             ax.add_patch(edge)
    #         return edge


def main():
    structure0 = Structure()
    structure0.first_order_negative()
    structure0.simulate(simulation_time=100)
    structure0.draw_graphs_with_function_value_polarity()
    structure0.display_results()


if __name__ == '__main__':
    main()
