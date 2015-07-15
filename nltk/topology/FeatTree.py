from _collections_abc import Iterable
import copy
from enum import Enum

from nltk import Tree, TYPE
from nltk.featstruct import EXPRESSION, unify
from nltk.grammar import FeatStructNonterminal

__author__ = 'Denis Krusko: kruskod@gmail.com'

GRAM_FUNC_FEATURE = 'GramFunc'
PRODUCTION_ID_FEATURE = 'ProdId'


class AutoNumber(Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __str__(self):
        return self.name


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
    NP = ()
    DP = ()
    QP = ()
    n = ()
    REL_PRO = ()
    DEM_PRO = ()
    pers_pro = ()
    PP = ()
    ADJP = ()
    ADVP = ()
    v = ()
    # leaves
    # S0 = ()


class GF(AutoNumber):
    det = ()
    mod = ()
    hd = ()
    subj = ()
    dobj = ()
    iobj = ()
    Pred = ()
    cmp = ()
    prt = ()


class FeatTree(Tree):
    def __init__(self, node, children=None):
        self._hclabel = None
        if isinstance(node, Tree):
            self._label = node._label
            list.__init__(self, node)
            self.ph = PH[self._label[TYPE]]
            self.gf = None
            self.tag = None
            self.topologies = []
            if GRAM_FUNC_FEATURE in self._label:
                self.gf = GF[self._label[GRAM_FUNC_FEATURE]]
            # make all leaves also FeatTree
            if not self.ishead():
                for index, child in enumerate(self):
                    if isinstance(child, Tree):
                        self[index] = FeatTree(child)
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
        if hasattr(self, '_hcLabel') and self._hcLabel:
            return self._hcLabel
        else:
            if self.ishead():
                head = self
            else:
                # find hd
                head = find_head(self)
            if head:
                # get all features of the hd child
                self._hclabel = copy.deepcopy(self.label())
                # merge hd features with the node features
                head_label = copy.deepcopy(head[0].label())
                del head_label[TYPE]
                self._hclabel.update(head_label)
                return self._hclabel
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

        if EXPRESSION in features_map:
            top_fstruct = FeatStructNonterminal()
            top_fstruct.update(features_map)
            return unify(self.label, top_fstruct)
        else:
            for key, val in features_map.items():
                if key in self._label:
                    if val != self._label[key]:
                        return False
            return True

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
        out = '(' + str(self.gorn) + ')'+ repr(self.hclabel())
        if self.topologies:
            fields = [[]]
            max_length = 0

            # initialize the field matrix
            for top in self.topologies:
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
            #------------------------------------------plus cell border---plus 1 for the | at the line beginning
            border = '\r\n' + '-' * ((len(fields[0]) * (max_length +1)) + 1) + '\r\n'
            format_expr = '{:^' + str(max_length) + '}|'
            table = border
            for row in fields:
                row_line = '|'
                for col in row:
                    row_line += format_expr.format(col)
                table += row_line + border
            # do recursive for children
            app = '\r\n'
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
        if isinstance(child, Tree):
            label = child.label()
            if GRAM_FUNC_FEATURE in label and label[GRAM_FUNC_FEATURE] == 'hd':
                return child
    return None
