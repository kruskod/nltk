import itertools

__author__ = 'Denis Krusko: kruskod@gmail.com'

from enum import Enum
from nltk.tree import Tree

class AutoNumber(Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class OP(AutoNumber):
    OR = ()
    AND = ()
    # ANDNOT = ()


class TAG(AutoNumber):
    dobjrel = ()
    focuscmp = ()
    focusdobj = ()
    focusiobj = ()
    imperative = ()
    inf = ()
    iobjrel = ()
    main = ()
    modf0 = ()
    np = ()
    pp = ()
    sub = ()
    subrel = ()
    subv2 = ()


class FT(AutoNumber):
    ADJP1 = ()
    ADJP2 = ()
    E1 = ()
    E2 = ()
    F0 = ()
    F1 = ()
    M1 = ()
    M1a = ()
    M1b = ()
    M2a = ()
    M2b = ()
    M2c = ()
    M3 = ()
    M4a = ()
    M4b = ()
    M4c = ()
    M5 = ()
    M6a = ()
    M6b = ()
    NP1 = ()
    NP2 = ()
    NP3 = ()
    NP4 = ()
    PP1 = ()
    PP2 = ()
    PP3 = ()


class PH(AutoNumber):
    S = ()
    AP = ()
    CP = ()
    NP = ()
    DP = ()
    QP = ()
    n = ()
    rel_pro = ()
    DEM_PRO = ()
    pers_pro = ()
    poss_pro = ()
    PP = ()
    ADJP = ()
    ADVP = ()
    prep = ()
    v = ()
    adj = ()
    co_conj = ()
    # leaves
    # S0 = ()


class GF(AutoNumber):
    det = ()
    mod = ()
    hd = ()
    subj = ()
    obj = ()
    dobj = ()
    iobj = ()
    Pred = ()
    cmp = ()
    cmpr = ()
    prt = ()

# class STATUS(AutoNumber):
#     Infin = ()  # Infinitive
#     Fin = ()  # Finite verb
#     PInfin = ()  # Pre-INFINitive
#     PastP = ()  # Past participle
#
#
# class MOOD(AutoNumber):
#     indicative = ()
#     subjunctive = ()
#     imperative = ()
#
#
# class VCAT(AutoNumber):
#     VE = ()  # VP Extraposition
#     VR = ()  # Verb Raising
#     VT = ()  # Third Construction
#     VF = ()  # Finite Complementation
#     VS = ()  # Simple VerbsVS
#     VRSehen = ()
#     PastPAuxSein = ()

class Share:
    german = {
        'status': ('Fin', 'Infin', 'PInfin')
    }

class TopTree(Tree):

    def label(self, label):
        self._label = label
        return self

    def anti(self, anti):
        self._anti = anti
        return self

    def position(self, position):
        if not self._position:
            self._position = []
        self._position.append(position)
        return self

#Declarative sentense wh = false
class FeatTree(Tree):
    def __init__(self, node, children=None, parent=None):
        self._hcLabel = None
        if isinstance(node, Tree):
            self._label = node._label
            list.__init__(self, node)
            self.ph = PH[self._label[TYPE]]

            if parent:
                self.gf = GF[parent._label[TYPE]]
                self.parent = parent
            else:
                self.gf = None
                self.parent = None
            self.tag = None
            self.topologies = []
            # make all leaves also FeatTree
            if not self.ishead():
                for index, child in enumerate(self):
                    # nodes with GF at this level
                    if isinstance(child, Tree):
                        feat_child = FeatTree(child[0], children=None, parent= child)
                        if feat_child:
                            self[index] = feat_child
                        else:
                            raise ValueError
            # else: we have already children

            #     leaves = []
            #     for child in self:
            #         leaves.append(list(child))
            #     list.__init__(self, leaves)
        else:
            if children is None:
                raise TypeError("%s: Expected a node value and child list " % type(self).__name__)
            elif isinstance(children, str):
                raise TypeError("%s() argument 2 should be a list, not a "
                                "string" % type(self).__name__)
            else:
                list.__init__(self, children)
                self._label = node
        self.numerate()

    def ishead(self):
        return self.gf == GF.hd

    def hclabel(self):
        if self._hcLabel:
            return self._hcLabel
        else:
            if self.ishead():
                self._hcLabel = self
            else:
                # find hd
                head = find_head(self)
                if head:
                    # get all features of the hd child
                    self._hcLabel = copy.deepcopy(self.label())
                    # merge hd features with the node features
                    head_label = copy.deepcopy(head.label())
                    del head_label[TYPE]
                    self._hcLabel = unify(self.label(), head_label, rename_vars=False)
            return self._hcLabel
        return None

    def numerate(self, gorn=0):
        self.gorn = gorn
        gorn *= 10
        counter = 1
        for child in self:
            if (isinstance(child, FeatTree)):
                child.numerate(gorn + counter)
            counter += 1

    def has_feature(self, features_map):
        """make new FeatStructNonTerminal and try to unify"""

        top_fstruct = FeatStructNonterminal()
        top_fstruct.update(features_map)
        if unify(self._label, top_fstruct):
            return True
        else:
            return False

    def fit(self, gf=None, ph=None):
        assert isinstance(gf, GF)
        assert isinstance(ph, PH) or (isinstance(ph, Iterable) and not [phi for phi in ph if not isinstance(phi, PH)])

        if self.gf == gf:
            if isinstance(ph, Iterable):
                for phi in ph:
                    if self.ph == phi:
                        return True
            elif self.ph == ph:
                return True
        return False

    def has_child(self, gf=None, ph=None):
        assert isinstance(gf, GF)
        assert isinstance(ph, PH) or (isinstance(ph, Iterable) and not [phi for phi in ph if not isinstance(phi, PH)])

        for child in self:
            if child.gf == gf:
                if isinstance(ph, Iterable):
                    for phi in ph:
                        if child.ph == phi:
                            return True
                elif child.ph == ph:
                    return True
        return False

    def __str__(self):
        out = '(' + str(self.gorn) + ')' + repr(self.label())
        # print leaves
        if self:
            leaves_str = ''.join(
                leaf for leaf in self if not isinstance(leaf, FeatTree))
            if leaves_str:
                out += ' -> ' + leaves_str
        # print all topologies
        if self.topologies:
            # initialize the field matrix
            for top in self.topologies:

                fields = [[]]
                max_length = 0
                for type, field in top.items():
                    line = str(type) + (str(field.mod) if field.mod else '')
                    fields[0].append(line)
                    if len(line) > max_length:
                        max_length = len(line)
                counter = 0
                while True:
                    has_items = False
                    fields.append([])
                    for type, field in top.items():
                        if len(field.edges) > counter:
                            has_items = True
                            edge = field.edges[counter]
                            line = str(edge.ph) + '(' + str(edge.gorn) + ')'
                            if len(line) > max_length:
                                max_length = len(line)
                        else:
                            line = ''
                        fields[counter + 1].append(line)
                    if not has_items:
                        del fields[-1]
                        break
                    counter += 1

                # generate a pretty string from the matrix
                # ------------------------------------------plus cell border---plus 1 for the | at the line beginning
                border = '\r\n' + '-' * ((len(fields[0]) * (max_length + 1)) + 1) + '\r\n'
                format_expr = '{:^' + str(max_length) + '}|'
                table = border
                label_expr = '|{:^' + str(len(fields[0]) * (max_length + 1) - 1) + '}|'
                out += border + label_expr.format(str(top.tag))
                for row in fields:
                    row_line = '|'
                    for col in row:
                        row_line += format_expr.format(col)
                    table += row_line + border
                # do recursive for children
                app = ''
                for ast in self:
                    app += str(ast)
                out += table + app
        else:
            out += '\n'
        return out

    def __hash__(self):
        return hash(self)


def find_head(root):
    for child in root:
        if isinstance(child, FeatTree):
            if child.gf == GF.hd:
                return child
        elif isinstance(child, Tree):
            label = child.label()
            if GRAM_FUNC_FEATURE in label and label[GRAM_FUNC_FEATURE] == 'hd':
                return child
    return None

# def simplify_expression(feat):
#     # check arguments
#     if isinstance(feat, (tuple,list)):
#         if isinstance(feat[0], OP) and len(feat) == 2:  # type of operator in expression
#             operator = feat[0]
#             expressions = simplify_expression(feat[1])
#
#             if operator == OP.OR:
#                 return expressions
#             elif operator == OP.AND:  # combine all features from all expressions
#                 result = expressions[0]
#                 for ex in expressions[1:]:
#                     for key, val in ex.items():
#                         if key in result:
#                             if val != result[key]:
#                                 raise ValueError("Contradiction in the expresion:{} in {}".format(expressions, feat))
#                         else:
#                             result[key] = val
#                 return result
#             else:
#                 raise ValueError("unknown operator:{} in {}".format(operator, feat))
#         else:
#             result = []
#             for feat_d in feat:
#                 part_res = simplify_expression(feat_d)
#                 if isinstance(part_res, dict):
#                     result.append(part_res)
#                 else:
#                     result.extend(part_res)
#             return result
#     elif isinstance(feat, dict):
#         result = []
#         for key, val in feat.items():  # looking for cases like {'a':(1,2)}
#             if isinstance(val, tuple):
#                 for sub_val in val:
#                     feat_copy = feat.copy()
#                     feat_copy[key] = sub_val
#                     result.append(feat_copy)
#         if result:
#             return simplify_expression(tuple(result))
#         else:
#             return feat
#     else:
#         raise ValueError("wrong type of argument:", feat)

def pprint_expression(feat):
    """
    :param feat: expression
    :return: formatted expression in string format
    """
    result = ''
    if isinstance(feat, (tuple,list)):
        if isinstance(feat[0], OP):
            result = '{} ('.format(feat[0])
            for exp in feat[1]:
                result += pprint_expression(exp) + '\n'
            result = result[:-1] + ')'
    elif isinstance(feat, dict) and len(feat) > 0:
        result = '['
        for key in sorted(feat.keys()):
            result += '{}:{},'.format(key, feat[key])
        result = result[:-1] + ']'
    return result


def simplify_expression(feat):
    # check arguments
    if isinstance(feat, (tuple,list)):
        if isinstance(feat[0], OP):
            operator = feat[0]
            expressions = []
            for f in feat[1]:
                expressions.append(simplify_expression(f))
            if operator == OP.AND:  # combine all features from all expressions
                # 1 step: combine all maps to one AND map
                result = {}
                for ex in expressions:
                    if isinstance(ex, dict):
                        for key, val in ex.items():
                            if key in result:
                                if val != result[key]:
                                    raise ValueError("Contradiction in the expresion:{} in {}".format(expressions, feat))
                            else:
                                result[key] = val
                # 2 step: if threre are OR list/tuples, combine them using distribution
                dist = []
                for ex in expressions:
                    if isinstance(ex, (tuple,list)):
                        for e in ex:
                            res_copy = result.copy()
                            for key, val in e.items():
                                if key in res_copy:
                                    if val != res_copy[key]:
                                        raise ValueError("Contradiction in the expresion:{} in {}".format(expressions, feat))
                                else:
                                    res_copy[key] = val
                            dist.append(res_copy)
                if dist:
                    return dist
                else:
                    return result
            elif operator == OP.OR:
                result = []
                for ex in expressions:
                    if isinstance(ex, dict):
                        result.append(ex)
                    else:
                        result.extend(ex)
                return result
            else:
                raise ValueError("unknown operator:{} in {}".format(operator, feat))

    elif isinstance(feat, dict):
        result = []
        for key, val in feat.items():  # looking for cases like {'a':(1,2)}
            if isinstance(val, tuple):
                for sub_val in val:
                    feat_copy = feat.copy()
                    feat_copy[key] = sub_val
                    result.append(feat_copy)
        if result:
            return result
        else:
            return feat
    else:
        raise ValueError("wrong type of argument:", feat)

def simplify_fstruct(fstruct):
     if is_nonterminal(fstruct) and EXPRESSION in fstruct:
        fstructs = []
        for ex in simplify_expression(fstruct[EXPRESSION]):
            fstructcopy = copy.deepcopy(fstruct)
            del fstructcopy[EXPRESSION]
            fstructcopy.update(ex)
            fstructs.append(fstructcopy)
        return fstructs
     else:
        return (fstruct,)

def open_disjunction(production):

    cproduction = copy.deepcopy(production)
    # open disjunction in the left part of expression
    fstructs = []
    fstructs.append(simplify_fstruct(production.lhs()))
    fstructs.extend(map(simplify_fstruct,cproduction.rhs()))

    for productions in itertools.product(*fstructs):
        yield Production(productions[0],productions[1:])

def minimize_expression(feat):
    if not feat:
        return feat

    common_keys = feat[0].keys()
    for exp in feat[1:]:
        common_keys = common_keys & exp.keys()

    if not common_keys:
        return feat

    min_exp = {}
    expressions = list(copy.deepcopy(feat))

    for key in common_keys:
        val = expressions[0][key]
        merge_allowed = True
        for exp in expressions[1:]:
            if val != exp[key]:
                merge_allowed = False
        if merge_allowed:
            min_exp[key] = val
            for exp in expressions:
                del exp[key]
                if not exp:
                    # minimize by prinzip A OR (A & 1) = A
                    return min_exp

    # there is no common values to combine
    if not min_exp:
        return combine_expression(feat)

    # if we have only one key with different values, we combine values in a set

    last_value_combine_allowed = True
    for exp in expressions:
        if len(exp) != 1:
            last_value_combine_allowed = False
            break

    if last_value_combine_allowed:
        common_val = set()
        last_key = None
        for exp in expressions:
            key, val = list(exp.items())[0]
            if key != last_key:
                if not last_key:
                    last_key = key
                else: # we have single element in every dictionary but with different keys
                    last_value_combine_allowed = False
                    break
            if isinstance(val, tuple):
                common_val.update(val)
            else:
                common_val.add(val)
        if last_value_combine_allowed: # merging is finished, return a single result
            min_exp[last_key] = tuple(common_val)
            return min_exp

    #if we have other features/values, we combine them in or expression
    return (OP.AND, (min_exp, combine_expression(expressions)))

def combine_expression(feat_list):
    return (OP.OR, tuple(feat_list))

def get_feature(featStructNonTerm, feature):
    result = set()
    if EXPRESSION in featStructNonTerm:
        simp_expressions = simplify_expression(featStructNonTerm[EXPRESSION])
        for exp in simp_expressions:
            if feature in exp:
                result.add(exp[feature])
        return result
    else:
        if feature in featStructNonTerm:
            result.add(featStructNonTerm[feature])
    return result

def minimize_nonterm(nt):
    if not is_nonterminal(nt):
        return nt
    nt = nt.filter_feature(SLOT_FEATURE)
    if EXPRESSION in nt:
        simpl_expres = minimize_expression(simplify_expression(nt[EXPRESSION]))
        if isinstance(simpl_expres, dict):
            nt.pop(EXPRESSION, None)
            nt.update(simpl_expres)
        else:
            nt[EXPRESSION] = simpl_expres
    return nt

def demo_simplifier(exp = (OP.OR, ((OP.OR, ({'a': (1, 2, 3, 4, 5), 'b': 2}, {'a': 2, 'c': 3})), (OP.AND, ({'b': 3, 'a': 5, 'c': 4}, {'c': 4}))))):
    #test = (OP.AND, ({'a': 0}, (OP.OR, ({'b':1},{'b':2}))))
    simplified_expression = simplify_expression(exp)
    for i in simplified_expression:
        print(i)
    min_expression = minimize_expression(simplified_expression)
    print(min_expression)

if __name__ == "__main__":
    demo_simplifier()
    demo_simplifier(exp = (OP.OR, ({'a': 2, 'b': 3}, {'a': 2, 'c': 3}, {'a': 2, 'c': 4})))

from _collections_abc import Iterable
import copy
# from nltk.tree import Tree
from nltk.featstruct import EXPRESSION, unify, TYPE
from nltk.topology.compassFeat import GRAM_FUNC_FEATURE, SLOT_FEATURE, BRANCH_FEATURE
from nltk.grammar import FeatStructNonterminal, is_nonterminal, Production
