from nltk.featstruct import pair_checker
from nltk.topology.topology import GramFunc

TOPOLOGY = "TOPOLOGY"
TAG = "TAG"
END = "END"
MODIFIERS = ['*', '!']
OPERATORS = ['OR', 'AND NOT', 'AND']
#

def topology_loader(file_name):
    with open(file_name, "rt") as topology_file:
        topologies = {}
        topology = None
        try:

            for line in topology_file:
                #look for comments
                index = line.find("//")
                if index >= 0:
                    line = line[:index]
                line = line.strip()
                if line and not line.startswith("ON") and not line.startswith("ERROR"):
                    # new topology
                    semi_index = line.rfind(';')
                    if not semi_index:
                        semi_index = len(line)
                    if line.startswith(TOPOLOGY):

                        topology = Topoology()
                        features_ind = pair_checker(line, len(TOPOLOGY))

                        if features_ind:
                            start_feat, end_feat = features_ind
                            topology.features = line[start_feat + 1: end_feat]
                            #print("features: ", topology.features)
                            topology.name = line[len(TOPOLOGY):start_feat].strip()
                        else:
                            topology.name = line[len(TOPOLOGY):].strip()
                        continue
                    #set tag to topology
                    elif line.startswith(TAG):
                        topology.tag = line[len(TAG): semi_index]
                    # end of topology
                    elif line == END:
                        if topology:
                            topologies[topology.name] = topology
                            print(topology)
                    # topology field
                    else:
                        index = line.find(":")
                        if index > 0:
                            field = Field()
                            mod = line[index - 1]
                            if mod in MODIFIERS:
                                field.mod = mod
                                field.name = line[:index - 1].strip()
                            else:
                                field.name = line[:index].strip()
                            gram_funcs = line[index + 1:].split(',')
                            for func in gram_funcs:
                                gram_func_name, expression = func.split(':', maxsplit=1)
                                elements = []
                                start_expr = 0
                                while (start_expr < len(expression)):
                                    element_ind = pair_checker(expression, start_expr)
                                    if element_ind:
                                        start_element_ind, end_element_ind = element_ind
                                        elements.append(expression[start_element_ind: end_element_ind + 1])
                                        start_expr = end_element_ind + 1
                                    else:
                                        break
                                #print(elements)
                                expr_elements = pair_checker(expression)
                                for operator in OPERATORS:
                                    if operator in expression:
                                        #parse expression
                                        elements = expression.split(operator)
                                        print(elements)

                                # except:
                                #     print(line)
                                gram_func = GramFunc(name=gram_func_name)
                                field.add_gramfunc(gram_func)
                            topology.addField(field)
        except:
            print("Error!\n", line)

if __name__ == "__main__":
    print(topology_loader("../../examples/grammars/book_grammars/wordPositions.pg"))