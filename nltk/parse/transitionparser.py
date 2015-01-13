'''
# Natural Language Toolkit: Implement Arc-Standard and Arc-eager transition based parser
#
# Author: Long Duong <longdt219@gmail.com>
#
# Copyright (C) 2001-2015 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
'''
import tempfile , pickle, os, copy, operator
from nltk.parse.api import ParserI
import scipy.sparse as sparse
import numpy as np  
from sklearn.datasets import load_svmlight_file
from sklearn import svm
from nltk.parse import DependencyGraph
from evaluate import DependencyEvaluator 

class Configuration(object):
    """
        Class for holding configuration which is the partial analysis of the input sentence. 
        The transition based parser aims at finding set of operators that transfer the initial
        configuration to the terminal configuration.  
          
        The configuration include 
            - Stack  : for storing partially proceeded words 
            - Buffer : for storing remaining input words 
            - Set of arcs : for storing partially built dependency tree
        
        This class also provide method to represent a configuration as list of features.    
    """
    def __init__(self,dep_graph):
        """
        :param dep_graph: the representation of an input in the form of dependency graph. 
        :type dep_graph: DependencyGraph where the dependencies is not specified.  
        """
        # dep_graph.nodes contain list of token for a sentence 
        self.stack = [0]  # The root element 
        self.buffer = range(1,len(dep_graph.nodes)) #  The rest is in the buffer 
        self.arcs = [] # empty set of arc
        self._tokens = dep_graph.nodes
        self._maxAddress = len(self.buffer) #  
        
    def __str__(self):
        return 'Stack : ' + str(self.stack) + '  Buffer : ' + str(self.buffer) + '   Arcs : ' + str(self.arcs)
    
    def _check_informative(self, feat, flag=False):
        """
        Check whether a feature is informative  
        The flag control whether "_" is informative or not  
        """
        if feat is None: return False
        if feat == ''  : return False
        if flag == False:
            if feat == '_' : return False
        return True 
    
    def extract_features(self):
        """
        Extract the set of features for the current configuration. Implement standard features as describe in 
        Table 3.2 (page 31) in Dependency Parsing book by Sandra Kubler, Ryan McDonal, Joakim Nivre.
        Please note that these features are very basic.     
        :return: list(str)
        """ 
        result = [] 
        # Todo : can come up with more complicated features set for better performance.
        if len(self.stack) >0:
            # Stack 0 
            stack_idx0 = self.stack[len(self.stack)-1] 
            token = self._tokens[stack_idx0]
            if self._check_informative(token['word'], True):
                result.append('STK_0_FORM_' + token['word'])
            if 'lemma' in token and self._check_informative(token['lemma']):
                result.append('STK_0_LEMMA_' + token['lemma'])
            if self._check_informative(token['tag']):
                result.append('STK_0_POS_' + token['tag'])
            if 'feats' in token and self._check_informative(token['feats']):
                feats = token['feats'].split("|")
                for feat in feats:
                    result.append('STK_0_FEATS_' + feat)
            # Stack 1
            if len(self.stack) > 1:
                stack_idx1 = self.stack[len(self.stack)-2] 
                token = self._tokens[stack_idx1]
                if self._check_informative(token['tag']):
                    result.append('STK_1_POS_' + token['tag'])
                    
            # Left most, right most dependency of stack[0]
            leftMost = 1000000 
            rightMost = -1
            depLeftMost = '' 
            depRightMost = ''
            for (wi,r,wj) in self.arcs:
                if wi == stack_idx0:
                    if (wj > wi) and (wj > rightMost) : 
                        rightMost = wj
                        depRightMost = r  
                    if (wj < wi) and (wj < leftMost ) : 
                        leftMost = wj 
                        depLeftMost = r 
            if self._check_informative(depLeftMost): 
                result.append('STK_0_LDEP_' + depLeftMost)
            if self._check_informative(depRightMost):    
                result.append('STK_0_RDEP_' + depRightMost)
                
        # Check Buffered 0 
        if len(self.buffer) > 0 : 
            # Buffer 0 
            buffer_idx0 = self.buffer [0] 
            token = self._tokens[buffer_idx0]
            if self._check_informative(token['word'], True):
                result.append('BUF_0_FORM_' + token['word'])
            if 'lemma' in token and self._check_informative(token['lemma']):
                result.append('BUF_0_LEMMA_' + token['lemma'])
            if self._check_informative(token['tag']):
                result.append('BUF_0_POS_' + token['tag'])
            if 'feats' in token and self._check_informative(token['feats']):
                feats = token['feats'].split("|")
                for feat in feats:
                    result.append('BUF_0_FEATS_' + feat)
            # Buffer 1 
            if len(self.buffer) > 1:
                buffer_idx1 = self.buffer[1] 
                token = self._tokens[buffer_idx1]
                if self._check_informative(token['word'], True):
                    result.append('BUF_1_FORM_' + token['word'])
                if self._check_informative(token['tag']):
                    result.append('BUF_1_POS_' + token['tag'])
            if len(self.buffer) > 2 : 
                buffer_idx2 = self.buffer[2] 
                token = self._tokens[buffer_idx2]
                if self._check_informative(token['tag']):
                    result.append('BUF_2_POS_' + token['tag'])
            if len(self.buffer) > 3 : 
                buffer_idx3 = self.buffer[3] 
                token = self._tokens[buffer_idx3]
                if self._check_informative(token['tag']):
                    result.append('BUF_3_POS_' + token['tag'])
                        # Left most, right most dependency of stack[0]
            leftMost = 1000000 
            rightMost = -1
            depLeftMost = '' 
            depRightMost = ''
            for (wi,r,wj) in self.arcs:
                if wi == buffer_idx0:
                    if (wj > wi) and (wj > rightMost) : 
                        rightMost = wj
                        depRightMost = r  
                    if (wj < wi) and (wj < leftMost) : 
                        leftMost = wj 
                        depLeftMost = r 
            if self._check_informative(depLeftMost): 
                result.append('BUF_0_LDEP_' + depLeftMost)
            if self._check_informative(depRightMost):    
                result.append('BUF_0_RDEP_' + depRightMost)
                
        return result 

class Transition(object):
    """
        This class define a set of transition which is applied to a configuration to get another configuration 
        Note that for different parsing algorithm, the transition is different.   
    """
    # Define set of transition  
    LEFT_ARC = 'LEFTARC' 
    RIGHT_ARC = 'RIGHTARC' 
    SHIFT = 'SHIFT'
    REDUCE = 'REDUCE'
    
    def __init__(self, alg_option):
        """
        :param alg_option: the algorithm option of this parser. Currently support `arc-standard` and `arc-eager` algorithm
        :type alg_option: str 
        """
        self._algo = alg_option
        if alg_option not in [TransitionParser.ARC_STANDARD, TransitionParser.ARC_EAGER]:
            raise ValueError(" Currently we only support %s and %s " % (TransitionParser.ARC_STANDARD, TransitionParser.ARC_EAGER))
        
        
    def left_arc(self, conf, relation):
        """
        Note that the algorithm for left-arc is quite similar except for precondition for both arc-standard and arc-eager  
            :param configuration: is the current configuration 
            :return : A new configuration or -1 if the pre-condition is not satisfied  
        """
        if (len(conf.buffer) <= 0) or (len(conf.stack) <=0):
            return -1
        if conf.buffer[0] == 0:
            # here is the Root element 
            return -1

        idx_wi = conf.stack[len(conf.stack) -1]
        
        flag = True
        if self._algo == TransitionParser.ARC_EAGER:
            for (idxParent,r,idxChild) in conf.arcs:
                if idxChild == idx_wi : flag = False

        if flag:
            conf.stack.pop()
            idx_wj = conf.buffer[0] 
            conf.arcs.append((idx_wj,relation,idx_wi))
        else:
            return -1 
                
    def right_arc(self, conf, relation):
        """
        Note that the algorithm for right-arc is DIFFERENT for arc-standard and arc-eager 
            :param configuration: is the current configuration 
            :return : A new configuration or -1 if the pre-condition is not satisfied  
        """
        if (len(conf.buffer) <= 0) or (len(conf.stack) <=0):
            return -1
        if self._algo == TransitionParser.ARC_STANDARD:
            idx_wi = conf.stack.pop()
            idx_wj = conf.buffer[0] 
            conf.buffer[0] = idx_wi
            conf.arcs.append((idx_wi,relation,idx_wj))
        else : # arc-eager  
            idx_wi = conf.stack[len(conf.stack) -1]
            idx_wj = conf.buffer.pop(0)
            conf.stack.append(idx_wj)
            conf.arcs.append((idx_wi,relation,idx_wj))
            
    def reduce (self, conf):
        """
        Note that the algorithm for reduce is only available for arc-eager 
            :param configuration: is the current configuration 
            :return : A new configuration or -1 if the pre-condition is not satisfied  
        """

        if self._algo != TransitionParser.ARC_EAGER: return -1 
        if len(conf.stack) <=0: return -1

        idx_wi = conf.stack[len(conf.stack) -1]
        flag = False
        for (idxParent,r,idxChild) in conf.arcs:
            if idxChild == idx_wi : flag = True 
        if flag: conf.stack.pop() # reduce it
        else: return -1
                
    def shift (self, conf):
        """
        Note that the algorithm for right-arc is the SAME for arc-standard and arc-eager 
            :param configuration: is the current configuration 
            :return : A new configuration or -1 if the pre-condition is not satisfied  
        """
        if len(conf.buffer) <=0 : return -1
        idx_wi = conf.buffer.pop(0)
        conf.stack.append(idx_wi)
     
class TransitionParser(ParserI):
    """
    Class for transition based parser. Implement 2 algorithms which are "arc-standard" and "arc-eager"
    """
    ARC_STANDARD = 'arc-standard'
    ARC_EAGER = 'arc-eager'
    
    def __init__(self, algorithm):
        """
        :param algorithm: the algorithm option of this parser. Currently support `arc-standard` and `arc-eager` algorithm
        :type algorithm: str 
        """
        if not(algorithm in [self.ARC_STANDARD,self.ARC_EAGER]) :
            raise ValueError(" Currently we only support %s and %s " % (self.ARC_STANDARD, self.ARC_EAGER))
        self._algorithm = algorithm
    
        self._dictionary = {} 
        self._transition = {}
        self._matchTransition = {}
    
    def _get_dep_relation(self,idx_parent,idx_child, depgraph):
        pNode = depgraph.nodes[idx_parent]
        cNode = depgraph.nodes[idx_child]
        
        if cNode['word'] is None: return None # Root word  
        
        if cNode['head'] == pNode['address']:
            return cNode['rel']
        else:
            return None
        
    def _convert_to_binary_features(self,  features):
        """
        :param features: list of feature string which is needed to convert to binary features
        :type features: list(str)
        :return : string of binary features in libsvm format  which is 'featureID:value' pairs   
        """
        unsorted_result = []
        for feature in features:
            self._dictionary.setdefault(feature, len(self._dictionary))
            unsorted_result.append(self._dictionary[feature])
            
        # Default value of each feature is 1.0 
        return ' '.join(str(featureID) +':1.0' for featureID in sorted(unsorted_result))

    def _is_projective(self, depgraph):
        arc_list = []
        for key in depgraph.nodes:
            node = depgraph.nodes[key]
            if 'head' in node:
                childIdx     = node['address']
                parentIdx  = node['head']
                arc_list.append((parentIdx,childIdx))
        
        for (parentIdx,childIdx) in arc_list:
            # Ensure that childIdx < parentIdx 
            if childIdx > parentIdx:
                temp = childIdx 
                childIdx = parentIdx
                parentIdx = temp  
            for k in range(childIdx+1, parentIdx):
                for m in range(len(depgraph.nodes)):
                    if (m < childIdx) or (m > parentIdx): 
                        if (k,m) in arc_list: return False 
                        if (m,k) in arc_list: return False 
        return True

    
    def _write_to_file(self, key, binary_features, input_file):
        """
        write the binary features to input file and update the transition dictionary  
        """
        self._transition.setdefault(key , len( self._transition) + 1)
        self._matchTransition[self._transition[key]] = key 
                     
        input_str =  str( self._transition[key]) + ' ' + binary_features  + '\n'  
        input_file.write(input_str.encode('utf-8')) 
                 
    def _create_training_examples_arc_std(self, depgraphs, input_file):
        """
        Create the training example in the libsvm format and write it to the input_file. 
        Reference : Page 32, Chapter 3. Dependency Parsing by Sandra Kubler, Ryan McDonal and Joakim Nivre (2009)
        """ 
        operation = Transition(self.ARC_STANDARD)
        countProj = 0 
        training_seq = []
         
        for depgraph in depgraphs:
            if not self._is_projective(depgraph):
                continue 
            
            countProj += 1 
            Conf = Configuration(depgraph)
            while len(Conf.buffer) > 0:
                b0 = Conf.buffer[0]
                features = Conf.extract_features()
                binary_features = self._convert_to_binary_features(features)
                
                if len(Conf.stack) > 0:  
                    s0 = Conf.stack[len(Conf.stack)-1]
                    # Left-arc operation
                    rel = self._get_dep_relation(b0, s0, depgraph) 
                    if  rel is not None :                  
                        key = Transition.LEFT_ARC +':' + rel
                        self._write_to_file(key, binary_features, input_file)
                        operation.left_arc(Conf, rel)
                        training_seq.append(key)
                        continue
                    
                    # Right-arc operation 
                    rel = self._get_dep_relation(s0, b0, depgraph)
                    if rel is not None:
                        precondition = True 
                        # Get the max-index of buffer
                        maxID = Conf._maxAddress

                        for w in range(maxID+1):
                            if w != b0: 
                                relw = self._get_dep_relation(b0, w, depgraph)
                                if relw is not None: 
                                    if (b0,relw,w) not in Conf.arcs:
                                        precondition = False
                                        
                        if precondition:
                            key = Transition.RIGHT_ARC + ':' + rel; 
                            self._write_to_file(key, binary_features, input_file)   
                            operation.right_arc(Conf, rel)
                            training_seq.append(key)
                            continue                           
                    
                # Shift operation as the default 
                key = Transition.SHIFT;
                self._write_to_file(key, binary_features, input_file)
                operation.shift(Conf)
                training_seq.append(key)
        
        print (" Number of training examples : " + str (len (depgraphs)))
        print (" Number of valid (projective) examples : " + str (countProj))
        return training_seq

    def _create_training_examples_arc_eager(self, depgraphs, input_file):
        """
        Create the training example in the libsvm format and write it to the input_file. 
        Reference : 'A Dynamic Oracle for Arc-Eager Dependency Parsing' by Joav Goldberg and Joakim Nivre 
        """ 
        operation = Transition(self.ARC_EAGER)
        countProj = 0 
        training_seq = []
        
        for depgraph in depgraphs:
            if not self._is_projective(depgraph):
                continue 
            
            countProj += 1 
            Conf = Configuration(depgraph)
            while len(Conf.buffer) > 0:
                b0 = Conf.buffer[0]
                features = Conf.extract_features()
                binary_features = self._convert_to_binary_features(features)
                
                if len(Conf.stack) > 0:  
                    s0 = Conf.stack[len(Conf.stack)-1]
                    # Left-arc operation
                    rel = self._get_dep_relation(b0, s0, depgraph) 
                    if  rel is not None :                  
                        key = Transition.LEFT_ARC +':' + rel
                        self._write_to_file(key, binary_features, input_file)
                        operation.left_arc(Conf, rel)
                        training_seq.append(key)
                        continue
                    
                    # Right-arc operation 
                    rel = self._get_dep_relation(s0, b0, depgraph)
                    if rel is not None:
                        key = Transition.RIGHT_ARC + ':' + rel; 
                        self._write_to_file(key, binary_features, input_file)
                        operation.right_arc(Conf, rel)
                        training_seq.append(key)
                        continue                           

                    # reduce operation 
                    flag = False 
                    for k in range(s0):
                        if self._get_dep_relation(k, b0, depgraph) is not None : flag = True 
                        if self._get_dep_relation(b0, k, depgraph) is not None : flag = True
                    if flag:
                        key = Transition.REDUCE;
                        self._write_to_file(key, binary_features, input_file)
                        operation.reduce(Conf) 
                        training_seq.append(key)
                        continue
                        
                # Shift operation as the default 
                key = Transition.SHIFT;
                self._write_to_file(key, binary_features, input_file)
                operation.shift(Conf)
                training_seq.append(key)
        
        print (" Number of training examples : " + str (len (depgraphs)))
        print (" Number of valid (projective) examples : " + str (countProj))
        return training_seq
    
    def train(self, depgraphs, modelfile):
        """
        :param depgraphs : list of DependencyGraph as the training data 
        :type depgraphs : DependencyGraph 
        :param modelfile : file name to save the trained model 
        :type modelfile : str   
        """
        
        try : 
            input_file = tempfile.NamedTemporaryFile(prefix='transition_parse.train',
                                                 dir=tempfile.gettempdir(),
                                                 delete=False)
            
            if self._algorithm == self.ARC_STANDARD: 
                self._create_training_examples_arc_std(depgraphs, input_file)
            else:
                self._create_training_examples_arc_eager(depgraphs, input_file)
            
            #print input_file.name
            input_file.close()
            # Using the temporary file to train the libsvm classifier
            x_train, y_train = load_svmlight_file(input_file.name)
            # The parameter is set according to the paper : Algorithms for Deterministic Incremental Dependency Parsing by Joakim Nivre
            # Todo : because of probability = True => very slow due to cross-validation. Need to improve the speed here  
            model = svm.SVC(kernel = 'poly', degree = 2, coef0 = 0, gamma=0.2, C=0.5,  verbose=True, probability=True)
            model.fit(x_train,y_train)
            # Save the model to file name (as pickle) 
            pickle.dump(model, open(modelfile,'wb'))
        finally: 
            os.remove(input_file.name)
            
            
    def parse(self, depgraphs, modelFile):
        """
            :param depgraphs: the list of test sentence, each sentence is represented as a dependency graph where the 'head' information is dummy  
            :type depgraphs: list(DependencyGraph)
            :param modelfile : the model file 
            :type modelfile : str 
            :return : list (DependencyGraph) with the 'head' and 'rel' information 
        """
        result = [] 
        # First load the model  
        model = pickle.load(open(modelFile,'rb'))
        operation = Transition(self._algorithm)
        countBreak = 0 
        
         
        for depgraph in depgraphs:
                       
            Conf = Configuration(depgraph)
            while len(Conf.buffer) > 0:               
                features = Conf.extract_features()
                col = []
                row = []
                data = []
                for feature in features:  
                    if feature in self._dictionary:
                        col.append(self._dictionary[feature])
                        row.append(0)
                        data.append(1.0)
                npCol = np.array(sorted(col)) # NB : index must be sorted 
                npRow = np.array(row)
                npData = np.array(data)
                
                #print str(npCol)  + '   ' + str (len(self._dictionary))
                x_test = sparse.csr_matrix((npData, (npRow,npCol)),   shape = (1,len(self._dictionary)))
                
                # It's best to use decision function as follow BUT it's not supported yet for sparse SVM 
                # Using decision funcion to build the votes array 
                #dec_func = model.decision_function(x_test)[0]
                #votes = {}
                #k = 0 
                #for i in range(len(model.classes_)):
                #    for j in range(i+1, len(model.classes_)):
                #        #if  dec_func[k] > 0:
                #            votes.setdefault(i,0) 
                #            votes[i] +=1 
                #        else:
                #           votes.setdefault(j,0)
                #           votes[j] +=1 
                #        k +=1 
                # Sort votes according to the values 
                #sorted_votes = sorted(votes.items(), key=operator.itemgetter(1), reverse=True)
                
                # We will use predict_proba instead of decision_function
                probDict = {} 
                predProb = model.predict_proba(x_test)[0]
                for i in range(len(predProb)):
                    probDict[i] =predProb[i] 
                sorted_Prob = sorted(probDict.items(), key=operator.itemgetter(1), reverse=True)

                # Note that SHIFT is always a valid operation 
                for (y_pred_idx, confidence) in sorted_Prob: 
                    #y_pred = model.predict(x_test)[0]
                    # From the prediction match to the operation
                    y_pred = model.classes_[y_pred_idx]
                     
                    if  y_pred in self._matchTransition:
                        strTransition = self._matchTransition[y_pred]
                        baseTransition = strTransition.split(":")[0]
                     
                        if baseTransition == Transition.LEFT_ARC:
                            if operation.left_arc(Conf, strTransition.split(":")[1]) != -1 :
                                break 
                        elif baseTransition == Transition.RIGHT_ARC:
                            if operation.right_arc(Conf, strTransition.split(":")[1]) != -1 :
                                break   
                        elif baseTransition == Transition.REDUCE:
                            if operation.reduce(Conf) != -1:
                                break  
                        elif baseTransition == Transition.SHIFT :
                            if operation.shift(Conf) != -1:
                                break   
                    else:
                        raise ValueError("The predicted transition is not recognized, expected errors")                
            
            # Finish with operations build the dependency graph from Conf.arcs
            
            new_depgraph = copy.deepcopy(depgraph) 
            for key in new_depgraph.nodes:
                node = new_depgraph.nodes[key]
                node['rel'] = '' 
                # With the default, all the token depend on the Root 
                node['head'] = 0   
            for (head,rel,child) in Conf.arcs:
                cNode = new_depgraph.nodes[child]
                cNode['head'] = head 
                cNode['rel'] = rel 
            result.append(new_depgraph)
            
        return result
           
def demo():
    """
    >>> from nltk.parse import DependencyGraph, DependencyEvaluator
    >>> from nltk.parse.transitionparser import TransitionParser, Configuration, Transition
    >>> gold_sent = DependencyGraph(\"""
    ... Economic  JJ     2      ATT
    ... news  NN     3       SBJ
    ... has       VBD       0       ROOT
    ... little      JJ      5       ATT
    ... effect   NN     3       OBJ
    ... on     IN      5       ATT
    ... financial       JJ       8       ATT
    ... markets    NNS      6       PC
    ... .    .      3       PU
    ... \""")
    
    >>> conf = Configuration(gold_sent)
    
    ###################### Check the Initial Feature ########################
       
    >>> print conf.extract_features()
    [u'STK_0_POS_TOP', u'BUF_0_FORM_Economic', u'BUF_0_LEMMA_Economic', u'BUF_0_POS_JJ', u'BUF_1_FORM_news', u'BUF_1_POS_NN', u'BUF_2_POS_VBD', u'BUF_3_POS_JJ']
    
    ###################### Check The Transition #######################
    Check the Initialized Configuration
    >>> print conf 
    Stack : [0]  Buffer : [1, 2, 3, 4, 5, 6, 7, 8, 9]   Arcs : []
    
    A. Do some transition checks for ARC-STANDARD 
    
    >>> operation = Transition('arc-standard')
    >>> operation.shift(conf)
    >>> operation.left_arc(conf, "ATT")
    >>> operation.shift(conf)
    >>> operation.left_arc(conf,"SBJ")
    >>> operation.shift(conf)
    >>> operation.shift(conf)
    >>> operation.left_arc(conf, "ATT")
    >>> operation.shift(conf)
    >>> operation.shift(conf)
    >>> operation.shift(conf)
    >>> operation.left_arc(conf, "ATT")
    
    Middle Configuration and Features Check 
    >>> print conf 
    Stack : [0, 3, 5, 6]  Buffer : [8, 9]   Arcs : [(2, 'ATT', 1), (3, 'SBJ', 2), (5, 'ATT', 4), (8, 'ATT', 7)]
    
    >>> print conf.extract_features()
    [u'STK_0_FORM_on', u'STK_0_LEMMA_on', u'STK_0_POS_IN', u'STK_1_POS_NN', u'BUF_0_FORM_markets', u'BUF_0_LEMMA_markets', u'BUF_0_POS_NNS', u'BUF_1_FORM_.', u'BUF_1_POS_.', 'BUF_0_LDEP_ATT']
    
    >>> operation.right_arc(conf, "PC")
    >>> operation.right_arc(conf, "ATT")
    >>> operation.right_arc(conf, "OBJ")
    >>> operation.shift(conf)
    >>> operation.right_arc(conf, "PU")
    >>> operation.right_arc(conf, "ROOT")
    >>> operation.shift(conf)
    
    Terminated Configuration Check  
    >>> print conf
    Stack : [0]  Buffer : []   Arcs : [(2, 'ATT', 1), (3, 'SBJ', 2), (5, 'ATT', 4), (8, 'ATT', 7), (6, 'PC', 8), (5, 'ATT', 6), (3, 'OBJ', 5), (3, 'PU', 9), (0, 'ROOT', 3)]

    
    B. Do some transition checks for ARC-EAGER 
    
    >>> conf = Configuration(gold_sent)
    >>> operation = Transition('arc-eager')
    >>> operation.shift(conf)
    >>> operation.left_arc(conf,'ATT')
    >>> operation.shift(conf)
    >>> operation.left_arc(conf,'SBJ')
    >>> operation.right_arc(conf,'ROOT')
    >>> operation.shift(conf)
    >>> operation.left_arc(conf,'ATT')
    >>> operation.right_arc(conf,'OBJ')
    >>> operation.right_arc(conf,'ATT')
    >>> operation.shift(conf)
    >>> operation.left_arc(conf,'ATT')
    >>> operation.right_arc(conf,'PC')
    >>> operation.reduce(conf)
    >>> operation.reduce(conf)
    >>> operation.reduce(conf)
    >>> operation.right_arc(conf,'PU')
    >>> print conf 
    Stack : [0, 3, 9]  Buffer : []   Arcs : [(2, 'ATT', 1), (3, 'SBJ', 2), (0, 'ROOT', 3), (5, 'ATT', 4), (3, 'OBJ', 5), (5, 'ATT', 6), (8, 'ATT', 7), (6, 'PC', 8), (3, 'PU', 9)]
    
    ###################### Check The Training Function #######################
    
    A. Check the ARC-STANDARD training 
    >>> import tempfile
    >>> import os 
    >>> input_file = tempfile.NamedTemporaryFile(prefix='transition_parse.train', dir=tempfile.gettempdir(), delete=False)
            
    >>> parserStd = TransitionParser('arc-standard')
    >>> parserStd._create_training_examples_arc_std([gold_sent], input_file)
     Number of training examples : 1
     Number of valid (projective) examples : 1
    ['SHIFT', u'LEFTARC:ATT', 'SHIFT', u'LEFTARC:SBJ', 'SHIFT', 'SHIFT', u'LEFTARC:ATT', 'SHIFT', 'SHIFT', 'SHIFT', u'LEFTARC:ATT', u'RIGHTARC:PC', u'RIGHTARC:ATT', u'RIGHTARC:OBJ', 'SHIFT', u'RIGHTARC:PU', u'RIGHTARC:ROOT', 'SHIFT']
    
    >>> parserStd.train([gold_sent],'temp.arcstd.model') 
     Number of training examples : 1
     Number of valid (projective) examples : 1
    ...
    >>> os.remove(input_file.name)
    
    B. Check the ARC-EAGER training 
    
    >>> input_file = tempfile.NamedTemporaryFile(prefix='transition_parse.train', dir=tempfile.gettempdir(),delete=False)
    >>> parserEager = TransitionParser('arc-eager')
    >>> parserEager._create_training_examples_arc_eager([gold_sent], input_file)
     Number of training examples : 1
     Number of valid (projective) examples : 1
    ['SHIFT', u'LEFTARC:ATT', 'SHIFT', u'LEFTARC:SBJ', u'RIGHTARC:ROOT', 'SHIFT', u'LEFTARC:ATT', u'RIGHTARC:OBJ', u'RIGHTARC:ATT', 'SHIFT', u'LEFTARC:ATT', u'RIGHTARC:PC', 'REDUCE', 'REDUCE', 'REDUCE', u'RIGHTARC:PU']
    
    >>> parserEager.train([gold_sent],'temp.arceager.model') 
     Number of training examples : 1
     Number of valid (projective) examples : 1
    ...
    
    >>> os.remove(input_file.name)
    
    ###################### Check The Parsing Function ########################
    
    A. Check the ARC-STANDARD parser
     
    >>> result = parserStd.parse([gold_sent], 'temp.arcstd.model') 
    >>> de = DependencyEvaluator(result, [gold_sent])
    >>> print de.eval()
    (0.125, 0.0)
    
    B. Check the ARC-EAGER parser
    >>> result = parserEager.parse([gold_sent], 'temp.arceager.model') 
    >>> de = DependencyEvaluator(result, [gold_sent])
    >>> print de.eval()
    (0.0, 0.0)      
    
    Note that result is very poor because of only 1 single training example. 
    """
if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
    