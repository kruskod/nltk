import itertools

from nltk.topology.orderedSet import OrderedSet

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

class STATUS(AutoNumber):
    Infin = ()  # Infinitive
    Fin = ()  # Finite verb
    PInfin = ()  # Pre-INFINitive
    PastP = ()  # Past participle

class VCAT(AutoNumber):
    VE = ()  # VP Extraposition
    VR = ()  # Verb Raising
    VT = ()  # Third Construction
    VF = ()  # Finite Complementation
    VS = ()  # Simple Verbs
    VRSehen = ()
    PastPAuxSein = ()
    Passive = ()

#
# class MOOD(AutoNumber):
#     indicative = ()
#     subjunctive = ()
#     imperative = ()

#Declarative sentense wh = false
class FeatTree(Tree):
    def __init__(self, node, children=None, parent=None, gf = None):
        self._hcLabel = None
        if isinstance(node, Tree):
            Tree.__init__(self, node._label, children = node)
            # list.__init__(self, node)
            self.ph = PH[self._label[TYPE]]
            self.gf = gf
            self.parent = parent
            self.shared = False
            self.tag = None
            self.topologies = []
            # make all leaves also FeatTree
            if not self.ishead():
                for index, child in enumerate(self):
                    # nodes with GF at this level
                    child_gf = GF[child._label[TYPE]]
                    feat_child = FeatTree(child[0], children=None, parent = self, gf=child_gf)
                    if feat_child:
                        self[index] = feat_child
                    else:
                        raise ValueError
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

    def fields(self):
        fields = set()
        if self.parent:
            for top in self.parent.topologies:
                for field,field_edges in top.items():
                    if self.gorn in (edge.gorn for edge in field_edges):
                        fields.add(field.ft)
        return fields

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

    def short_str(self):
        return ((str(self.gf) + " ") if self.gf else "") + "{}({})".format(self.ph, self.gorn)

    def __str__(self):
        out = "\r\n({}) {} ".format(self.gorn, self.gf if self.gf else '') +  repr(self.label())
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
                fields_length = []
                max_length = 0
                for field, field_edges in top.items():
                    line = str(field.ft) + (str(field.mod) if field.mod else '')
                    fields[0].append(line)
                    fields_length.append(len(line))
                    if len(line) > max_length:
                        max_length = len(line)
                counter = 0
                while True:
                    has_items = False
                    fields.append([])
                    index = 0
                    for field, field_edges in top.items():
                        if len(field_edges) > counter:
                            has_items = True
                            edge = field_edges[counter]
                            line = "{} {} ({})".format(edge.gf, edge.ph, edge.gorn)
                            if len(line) > max_length:
                                max_length = len(line)
                            if len(line) > fields_length[index]:
                                fields_length[index] = len(line)
                        else:
                            line = ''
                        fields[counter + 1].append(line)
                        index +=1
                    if not has_items:
                        del fields[-1]
                        break
                    counter += 1

                # generate a pretty string from the matrix
                # ------------------------------------------plus cell border---plus 1 for the | at the line beginning
                border = '\r\n' + '-' * (sum(fields_length) + len(fields_length) + 1) + '\r\n'
                table = border
                label_expr = '|{:^' + str(sum(fields_length) + len(fields_length) - 1) + '}|'

                ## "\r\nAlternative: {} \r\n".format(alternative_number) + "=" * (len(fields[0]) * max_length) +

                out +=  border + label_expr.format(str(top.tag))
                for row in fields:
                    row_line = '|'
                    for index, col in enumerate(row):
                        format_expr = '{:^' + str(fields_length[index]) + '}|'
                        row_line += format_expr.format(col)
                    table += row_line + border
                # do recursive for children
                # app = ''
                # for ast in self:
                #     app += str(ast)
                out += table# + app
        else:
            out += '\n'
        return out

    def bfs(self, visited=OrderedSet()):
        queue = [self]
        while queue:
            vertex = queue.pop(0)
            if vertex.topologies:
                if vertex not in visited:
                    visited.add(vertex)
                    queue.extend(set(vertex) - visited)
            else:
                visited.add(vertex)
        return visited

    def __hash__(self):
        return self.gorn

    def share(self):
        """ 1. go to bottom till reach head
            2. go up and look what you can share with a topology above
            3. create share edges and put them in topology above
            4. pass control back to the stack

            Note: the head of a lexical frame does not participate in topology sharing: it cannot be
            promoted outside of its own topology, nor can the slot serving as its landing site.

        :return None
        """

        # 1 step
        for child in self:
            child.parent = self
            if not child.ishead():
                child.share()

        # 2 step
        if GF.cmp == self.gf and PH.S == self.ph:
            parent = self.parent
            if parent and PH.S == parent.ph:
                #set sharing area using status and vcat features
                #TODO add check on interrogative and declarative sentence
                status = get_feature(self._hcLabel, STATUS_FEATURE)
                vcat = get_feature(self._hcLabel, VCAT_FEATURE)
                ls = rs = ()
                # sharing rules from the article Dutch and German verb clusters in Performance Grammar, G.Kempen & K.Harbusch 10.2002
                if STATUS.Infin.name in status:
                    if VCAT.VE.name in vcat:
                        ls = (1,)
                        rs = range(0,2)
                    elif VCAT.VT.name in vcat or VCAT.Passive.name in vcat:
                        ls = range(1,7)
                        rs = range(0,2)
                    elif VCAT.VR.name in vcat or VCAT.VRSehen.name in vcat:
                        ls = (5,)
                        rs = (1,)
                elif STATUS.Fin.name in status:
                    ls = (1,)

                if ls or rs:
                    # 3 step
                    # in this implementation I don't remove initial parent topology,
                    # but just adding new sharing edges to it
                    shared_parent_topologies = []
                    shared_topologies = []

                    while self.topologies:
                        topology = self.topologies.pop()

                        # if we should share from both sides
                        if ls and rs:
                            last_number_left_shared_fields = -1

                            for left_span in ls:
                                left_shared_topology = copy.copy(topology)
                                fields = list(left_shared_topology.keys())
                                # We must share left_span, right_span edges
                                left_span_fields = fields[:left_span] if left_span > 0 else tuple()
                                number_left_shared_fields = number_shared_fields(left_span_fields, left_shared_topology)

                                if last_number_left_shared_fields < number_left_shared_fields:
                                    last_number_left_shared_fields = number_left_shared_fields

                                    left_shared_parent_topologies = copy.copy(parent.topologies)

                                    # promote shared fields from the left periphery to the parent topology
                                    share_edges(left_span_fields, left_shared_topology, left_shared_parent_topologies)

                                    last_number_right_shared_fields = -1
                                    for right_span in rs:
                                        right_span_fields = fields[-right_span:] if right_span > 0 else tuple()

                                        number_right_shared_fields = number_shared_fields(right_span_fields, left_shared_topology)

                                        if last_number_right_shared_fields < number_right_shared_fields:
                                            last_number_right_shared_fields = number_right_shared_fields

                                            right_shared_topology = copy.copy(left_shared_topology)
                                            right_shared_parent_topologies = copy.copy(left_shared_parent_topologies)

                                            # share right_span_fields with the parent topologies
                                            share_edges(right_span_fields, right_shared_topology, right_shared_parent_topologies)

                                            # save share trace to restore sharing process
                                            right_shared_topology.shared_trace += '{},{}|'.format(left_span,right_span)
                                            for shar_top in right_shared_parent_topologies:
                                                shar_top.shared_trace += right_shared_topology.shared_trace

                                            shared_parent_topologies.extend(right_shared_parent_topologies)
                                            shared_topologies.append(right_shared_topology)
                        elif ls:
                            last_number_left_shared_fields = -1

                            for left_span in ls:
                                if left_span > 0:
                                    left_shared_topology = copy.copy(topology)
                                    fields = list(left_shared_topology.keys())
                                    # We must share left_span edges
                                    left_span_fields = fields[:left_span]

                                    number_left_shared_fields = number_shared_fields(left_span_fields, left_shared_topology)

                                    if last_number_left_shared_fields < number_left_shared_fields:
                                        last_number_left_shared_fields = number_left_shared_fields

                                        left_shared_parent_topologies = copy.copy(parent.topologies)

                                        # promote shared fields from the left periphery to the parent topology
                                        share_edges(left_span_fields, left_shared_topology, left_shared_parent_topologies)

                                        # save share trace to restore sharing process
                                        left_shared_parent_topologies.shared_trace += '{},|'.format(left_span)
                                        for shar_top in left_shared_parent_topologies:
                                                shar_top.shared_trace += left_shared_parent_topologies.shared_trace

                                        shared_parent_topologies.extend(left_shared_parent_topologies)
                                        shared_topologies.append(left_shared_topology)
                                else:
                                    shared_parent_topologies.extend(parent.topologies)
                                    shared_topologies.append(topology)
                        elif rs:
                            last_number_right_shared_fields = -1

                            for right_span in rs:
                                if right_span > 0:
                                    right_shared_topology = copy.copy(topology)
                                    fields = list(right_shared_topology.keys())
                                    right_span_fields = fields[-right_span:]
                                    number_right_shared_fields = number_shared_fields(right_span_fields, right_shared_topology)

                                    if last_number_right_shared_fields < number_right_shared_fields:
                                        last_number_right_shared_fields = number_right_shared_fields

                                        right_shared_parent_topologies = copy.copy(parent.topologies)

                                        # share right_span_fields with the parent topologies
                                        share_edges(right_span_fields, right_shared_topology, right_shared_parent_topologies)

                                        # save share trace to restore sharing process
                                        right_shared_topology.shared_trace += ',{}|'.format(right_span)
                                        for shar_top in right_shared_parent_topologies:
                                                shar_top.shared_trace += right_shared_topology.shared_trace

                                        shared_parent_topologies.extend(right_shared_parent_topologies)
                                        shared_topologies.append(right_shared_topology)

                                else:
                                    shared_parent_topologies.extend(parent.topologies)
                                    shared_topologies.append(topology)

                    if shared_parent_topologies:
                        self.parent.topologies = shared_parent_topologies
                        self.topologies = shared_topologies

                    # 4 step


    def alternatives(self):
        result = set()
        for topology in self.topologies:
            # print("\nInitial topology: \n" + repr(topology))
            # split topology to topologies with only one item in one field
            unified_topologies = [copy.copy(topology),]
            has_duplicate = True
            while(has_duplicate):
                has_duplicate = False
                forks = []
                for index, top in enumerate(unified_topologies):
                    for field, field_edges in top.items():
                        if len(field_edges) > 1:
                            has_duplicate = True
                            del unified_topologies[index]
                            for edge in field_edges:
                                new_topology = copy.copy(topology)
                                new_topology[field] = [edge,]
                                forks.append(new_topology)
                if forks:
                     unified_topologies.extend(forks)

            # print("\nHandling duplicates:")
            # for unified_topology in unified_topologies:
            #     print(repr(unified_topology))

            for unified_topology in unified_topologies:
                places = dict()
                # fill places for node . f.e. NP -> F1, F2
                for field, field_edges in unified_topology.items():
                    for field_node in field_edges:
                        if field_node not in places:
                            places[field_node] = set()
                        places[field_node].add(field)

                if (len(places) < len(self)): # not all nodes were used for topology - topology is wrong
                    continue

                generated_topologies = [unified_topology,]
                for field_node, fields in places.items():
                    forks = []
                    if len(fields) > 1:
                        while generated_topologies:
                            top = generated_topologies.pop()
                            for field in fields:
                                new_topology = copy.deepcopy(top)
                                for field_to_free in fields:
                                    if field_to_free != field:
                                        new_topology[field_to_free].remove(field_node)
                                forks.append(new_topology)
                    generated_topologies.extend(forks)
                result.update(generated_topologies)

        # topologies validation, that all needed fields are filled
        self.topologies = []
        for topology in sorted(result, key=repr):
            if topology.isvalid():
                self.topologies.append(topology)

        # self.topologies = result
        if not self.ishead():
            for child in self:
                # nodes with GF at this level
                if isinstance(child, FeatTree):
                    child.alternatives()
        # print("\nAfter generation:")
        # for top in result:
        #     print(repr(top))

    def split_alternatives(self):
        """
        split multiple topologies to separate trees
        :return:
        """
        if not self.ishead():
            alternatives = []

            for top in self.topologies:
                children_index = []

                # update edges in topology
                for edge in self:
                    for top_edges in top.values():
                        for index, top_edge in enumerate(top_edges):
                            if top_edge.gorn == edge.gorn:
                                del top_edges[index]
                                top_edges.append(edge)

                for index, field_edges in enumerate(top.values()):
                    for edge in field_edges:
                        children_index.append((index,edge))
                children_order = [tup[1] for tup in sorted(children_index, key=lambda x: x[0])]
                new_self = copy.copy(self)
                list.__init__(new_self, children_order)
                top.edge = new_self
                new_self.topologies = [copy.copy(top),]
                alternatives.append(new_self)

            child_alternatives = []
            for child in self:
                if not child.ishead():
                    child_alternatives.append(child.split_alternatives())

            if not child_alternatives:
                return alternatives

            forks = []
            for alternative in alternatives:
                for variation in itertools.product(*child_alternatives):
                    new_self = copy.copy(alternative)
                    for child in variation:
                        new_child = copy.copy(child)
                        new_child.parent = new_self
                        for index, altern_child in enumerate(new_self):
                            if altern_child.gorn == new_child.gorn:
                                new_self[index] = new_child
                                # update topology edges
                                for topology in new_self.topologies:
                                    for edge_list in topology.values():
                                        if altern_child in edge_list:
                                            edge_list.remove(altern_child)
                                            edge_list.append(new_child)
                                            break
                                    else:
                                        raise Exception("Edge in topology not found:", altern_child)
                                break
                        else:
                            raise Exception("Child not found", new_child)
                    forks.append(new_self)
            return forks

            # for gorn, child_alternative in child_alternatives.items():
            #     forks = []
            #     while(alternatives):
            #         self_alternative = alternatives.pop()
            #         for index, edge in enumerate(self_alternative):
            #             if isinstance(edge, FeatTree) and gorn == edge.gorn:
            #                 for child_alternative in child_alternative:
            #                     new_self = copy.copy(self_alternative)
            #                     new_child = copy.copy(child_alternative)
            #                     new_child.parent = new_self
            #                     new_self[index] = new_child
            #                     #TODO update link on child in topologies or refactor topology structure
            #                     forks.append(new_self)
            #                 break
            #         else:
            #             forks.append(self_alternative)
            #     alternatives.extend(forks)
            #return alternatives

    def split_shared_topologies(self):
        """
        split shared topologies to separate trees
        :return:
        """
        if not self.ishead():
            alternatives = []

            for top in self.topologies:
                new_self = copy.copy(self)
                top.edge = new_self
                new_self.topologies = [copy.copy(top),]
                alternatives.append(new_self)

            child_alternatives = []
            for child in self:
                if not child.ishead():
                    child_alternatives.append(child.split_shared_topologies())

            if child_alternatives:
                return alternatives

            forks = []
            for alternative in alternatives:
                for variation in itertools.product(*child_alternatives):
                    new_self = copy.copy(alternative)
                    allowed_variation = True
                    for child in variation:

                        # check that variation is connected with parent topology
                        # update this algorithm if needed

                        if not child.topologies[0].shared_trace in alternative.topologies[0].shared_trace:
                            allowed_variation = False
                            break

                        new_child = copy.copy(child)
                        new_child.parent = new_self
                        for index, altern_child in enumerate(new_self):
                            if altern_child.gorn == new_child.gorn:
                                new_self[index] = new_child
                                # update topology edges
                                for topology in new_self.topologies:
                                    for edge_list in topology.values():
                                        if altern_child in edge_list:
                                            edge_list.remove(altern_child)
                                            edge_list.append(new_child)
                                            break
                                break
                        else:
                            raise Exception("Child not found", new_child)
                    if allowed_variation:
                        forks.append(new_self)
            return forks

def number_shared_fields(share_fields, base_topology):
    """
    set shared property for fields
    :param share_fields:  topology fields to share
    :param base_topology: topology with share_fields
    :return: actual number of fields to share (except fields with head edges, etc.)
    """
    number_shared_fields = 0
    for field in share_fields:
        field.shared = True
        field_edges = base_topology[field]
        if field_edges:
            for edge in field_edges:
                if edge.ishead():
                    field.shared = False
                    break
            else:
                number_shared_fields += 1
    return number_shared_fields


def share_edges(share_fields, base_topology, parent_topologies):
    """

    :param share_fields: topology fields to share
    :param base_topology: topology with share_fields
    :param parent_topologies: where to share
    :return: None
    """
    for field in share_fields:
        if field.shared:
            field_edges = base_topology[field]
            if field_edges:
                for edge in field_edges:
                    edge.shared = True
                base_topology[field] = list()
                for parent_topology in parent_topologies:
                    parent_field_edges = parent_topology[field]
                    # check that we do not promote to the parent field
                    for edge in parent_field_edges:
                        if edge.ishead():
                            break
                    else:
                        parent_topology[field] = list(parent_field_edges + field_edges)

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
        # working code. disabled to not simplify dictionaries
        # singlefied = list()
        # pool = [feat.copy(),]
        #
        # while (pool):
        #     feat_dict = pool.pop()
        #     for key, val in feat_dict.items():  # looking for cases like {'a':(1,2)}
        #         if isinstance(val, tuple):
        #             for sub_val in val:
        #                 feat_copy = feat_dict.copy()
        #                 feat_copy[key] = sub_val
        #                 pool.append(feat_copy)
        #             break
        #     else:
        #         singlefied.append(feat_dict)
        #
        # if singlefied:
        #     return singlefied
        # else:
        #     return feat
        return feat
    else:
        raise ValueError("wrong type of argument:", feat)



        # #Add subject-verb agreement
        # if NUMBER_FEATURE in lhs or PERSON_FEATURE in lhs:
        #     for nt in rhs:
        #         if nt[TYPE] == 'hd':
        #             if NUMBER_FEATURE not in nt and NUMBER_FEATURE in lhs:
        #                 nt[NUMBER_FEATURE] = lhs[NUMBER_FEATURE]
        #             if PERSON_FEATURE not in nt and PERSON_FEATURE in lhs:
        #                 nt[PERSON_FEATURE] = lhs[PERSON_FEATURE]
        #             break
        # if INHERITED_FEATURE in lhs:
        #     lhs = lhs.filter_feature(INHERITED_FEATURE)
        # return Production(lhs, rhs)


# def simplify_fstruct(fstruct):
#     '''
#     inherited features should not be simplified, because they should be treated further
#     :param fstruct:
#     :return:
#     '''
#     if is_nonterminal(fstruct):
#         if EXPRESSION in fstruct:
#             fstructs = []
#             for ex in simplify_expression(fstruct[EXPRESSION]):
#                 fstructcopy = copy.deepcopy(fstruct)
#                 del fstructcopy[EXPRESSION]
#                 fstructcopy.update(ex)
#                 fstructs.append(fstructcopy)
#         else:
#             fstructs = list((fstruct,))
#         #disabled because to many tree will be generated if singlefy all features
#
#         # singlefied = list()
#         # for nt in fstructs:
#         #     inh_feat = nt.get_feature(INHERITED_FEATURE)
#         #     if inh_feat:
#         #         nt = nt.filter_feature(INHERITED_FEATURE)
#         #     pool = set((nt,))
#         #     # simplify nonterminal until it can not be simplified further
#         #     while (pool):
#         #         nonterminals_buffer = simplify_expression(pool.pop())
#         #         if isinstance(nonterminals_buffer, FeatStructNonterminal):
#         #             if inh_feat:
#         #                 nonterminals_buffer.add_feature({INHERITED_FEATURE:inh_feat})
#         #             singlefied.append(nonterminals_buffer)
#         #         else:
#         #             pool.update(nonterminals_buffer)
#         # return singlefied
#         return fstructs
#     else:
#         return (fstruct,)

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
    fstructs.append(simplify_fstruct(cproduction.lhs()))
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
from nltk.topology.compassFeat import GRAM_FUNC_FEATURE, SLOT_FEATURE, BRANCH_FEATURE, INHERITED_FEATURE, STATUS_FEATURE, \
    VCAT_FEATURE
from nltk.grammar import FeatStructNonterminal, is_nonterminal, Production
