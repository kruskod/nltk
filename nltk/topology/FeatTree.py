import itertools

from nltk.compat import unicode_repr
from nltk.topology.orderedSet import OrderedSet
from yaep.tools.permutations import values_combinations

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
    cp = ()
    dp = ()
    qp = ()
    advp = ()
    adjp = ()
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
    CP1 = ()
    DP1 = ()
    QP1 = ()
    ADVP1 = ()
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
    dem_pro = ()
    pers_pro = ()
    poss_pro = ()
    indef_pro = ()
    PP = ()
    ADJP = ()
    ADVP = ()
    adv = ()
    prep = ()
    v = ()
    adj = ()
    co_conj = ()
    art = ()
    crd = ()
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
    q = () # ein - Quantifier

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

    def __init__(self, label=None, hclabel=None, children=tuple(), gf=None, ph=None, parent=None, gorn=None):
        self._hcLabel = hclabel
        self.ph = ph
        self.gf = gf
        self.tag = None
        self.topologies = None
        self._label = label
        self.parent = parent
        self.gorn = gorn
        list.__init__(self, children)

    @classmethod
    def from_tree(cls, node, gf=None, parent=None):
        assert isinstance(node, Tree)

        label = node.label()
        feat_tree = cls(label, gf=gf, parent=parent)
        feat_tree.ph = PH[label[TYPE]]
        feat_tree.topologies = []

        # convert all Tree leaves to FeatTree
        if not feat_tree.ishead():
            for child in node:
                # nodes with GF at this level
                child_gf = GF[child.label()[TYPE]]
                feat_child = FeatTree.from_tree(child[0], gf=child_gf, parent=feat_tree)
                assert feat_child, "All leaves should be processed correctly to build a correct tree"
                feat_tree.append(feat_child)

        feat_tree.numerate()
        return feat_tree

    @classmethod
    def from_node(cls, node, gf=None, parent=None):
        from yaep.parse.parse_tree_generator import LeafNode
        assert isinstance(node, LeafNode)

        label = node.label()
        feat_tree = cls(label, gf=gf, parent = parent)
        feat_tree.ph = PH[label[TYPE]]
        feat_tree.topologies = []

        # convert all Tree leaves to FeatTree
        if not feat_tree.ishead():
            for child in node.children():
                # nodes with GF at this level
                child_gf = GF[child.label()[TYPE]]
                feat_child = FeatTree.from_node(child[0], gf=child_gf, parent=feat_tree)
                assert feat_child, "All leaves should be processed correctly to build a correct tree"
                feat_tree.append(feat_child)
        else:
            for child in node.children():
                feat_tree.append(child.label())
        feat_tree.numerate()
        return feat_tree

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

    def label(self):
        return self._label

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

    def find_edge(self, gorn):
        if self.gorn == gorn:
            return self
        for edge in self:
            if isinstance(edge, FeatTree):
                edge = edge.find_edge(gorn)
                if edge:
                    return edge

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
        return "({}){} {}".format(self.gorn, self.gf if self.gf else "", self.ph)

    def short_str_with_features(self):
        return "({}){} {}".format(self.gorn, self.gf if self.gf else "", repr(self.label()))

    def pretty_print(self, level):
        padding = '\n' + '\t' * level
        children_str = " ".join(c.pretty_print(level + 1) if isinstance(c, FeatTree) else c for c in self)
        out = "{}([{}] {}{} {})".format(padding, self.gorn, str(self.gf) + ' ' if self.gf else '', unicode_repr(self.label()), children_str if self else '')
        return out

    def __str__(self):
        out = "\r\n({}) {} ".format(self.gorn, self.gf if self.gf else '') + repr(self.label())
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
                            edge = self.find_edge(field_edges[counter])
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

    def major_constituents(self):
        for child in self:
            if self.ph == PH.S:
                yield child
            if not isinstance(child, str):
                yield from child.major_constituents()

    def bfs(self, visited=None):
        if visited is None:
            visited = OrderedSet()
        queue = [self]
        while queue:
            vertex = queue.pop(0)
            if vertex not in visited:
                if vertex.topologies:
                    queue.extend(set(vertex) - visited)
                visited.add(vertex)
        return visited

    def __hash__(self):
        return self.gorn

    def leaves(self):
        """
        Read shared leaves from the FeatTree with topologies.

            >>> t = FeatTree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.leaves()
            ['the', 'dog', 'chased', 'the', 'cat']

        :return: a list containing this tree's leaves.
            The order reflects the order of the
            leaves in the tree's hierarchical structure.
        :rtype: list
        """
        assert len(self.topologies) == 1, "It should be only one topology for the tree"
        topology = self.topologies[0]
        leaves = []
        for ft, field_gorns in topology.items():
            if field_gorns and not topology.field_map[ft].shared_to:
                for gorn in field_gorns:
                    vertex = self.find_edge(gorn)
                    if vertex.topologies:
                        leaves.extend(vertex.leaves())
                    else:
                        leaves.append(vertex[0])
        return leaves


    def share(self, parent=None):
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
                child.share(self)

        # 2 step
        if GF.cmp == self.gf and PH.S == self.ph:
            if parent and PH.S == parent.ph:
                #set sharing area using status and vcat features
                # TODO add check on interrogative and declarative sentence
                status = get_feature(self._hcLabel, STATUS_FEATURE)
                vcat = get_feature(self._hcLabel, VCAT_FEATURE)
                ls = rs = ()
                # sharing rules from the article Dutch and German verb clusters in Performance Grammar, G.Kempen & K.Harbusch 10.2002
                if STATUS.Infin.name in status:
                    if VCAT.VE.name in vcat or VCAT.VS.name in vcat:
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
                                left_shared_topology = copy.deepcopy(topology)

                                fields = list(left_shared_topology.keys())
                                # We must share left_span, right_span edges
                                left_span_fields = fields[:left_span] if left_span > 0 else tuple()
                                number_left_shared_fields = number_shared_fields(self, left_span_fields, left_shared_topology)

                                if last_number_left_shared_fields < number_left_shared_fields:
                                    last_number_left_shared_fields = number_left_shared_fields

                                    left_shared_parent_topologies = copy.deepcopy(parent.topologies)

                                    # promote shared fields from the left periphery to the parent topology
                                    left_shared_topology.ls = left_span
                                    share_edges(parent, left_span_fields, left_shared_topology, left_shared_parent_topologies)

                                    last_number_right_shared_fields = -1
                                    for right_span in rs:
                                        right_span_fields = fields[-right_span:] if right_span > 0 else tuple()

                                        number_right_shared_fields = number_shared_fields(self, right_span_fields, left_shared_topology)

                                        if last_number_right_shared_fields < number_right_shared_fields:
                                            last_number_right_shared_fields = number_right_shared_fields

                                            right_shared_topology = copy.deepcopy(left_shared_topology)
                                            right_shared_parent_topologies = copy.deepcopy(left_shared_parent_topologies)

                                            # share right_span_fields with the parent topologies
                                            right_shared_topology.rs = right_span
                                            share_edges(parent, right_span_fields, right_shared_topology, right_shared_parent_topologies)

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
                                    left_shared_topology = copy.deepcopy(topology)

                                    fields = list(left_shared_topology.keys())
                                    # we must share left_span edges
                                    left_span_fields = fields[:left_span]

                                    number_left_shared_fields = number_shared_fields(self, left_span_fields, left_shared_topology)

                                    if last_number_left_shared_fields < number_left_shared_fields:
                                        last_number_left_shared_fields = number_left_shared_fields

                                        left_shared_parent_topologies = copy.deepcopy(parent.topologies)

                                        left_shared_topology.ls = left_span
                                        # promote shared fields from the left periphery to the parent topology
                                        share_edges(parent, left_span_fields, left_shared_topology, left_shared_parent_topologies)

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
                                    right_shared_topology = copy.deepcopy(topology)

                                    fields = list(right_shared_topology.keys())
                                    right_span_fields = fields[-right_span:]
                                    number_right_shared_fields = number_shared_fields(self, right_span_fields, right_shared_topology)

                                    if last_number_right_shared_fields < number_right_shared_fields:
                                        last_number_right_shared_fields = number_right_shared_fields

                                        right_shared_parent_topologies = copy.deepcopy(parent.topologies)

                                        right_shared_topology.rs = right_span
                                        # share right_span_fields with the parent topologies
                                        share_edges(parent, right_span_fields, right_shared_topology, right_shared_parent_topologies)

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
        """
        split topologies with several possible word order on different topologies with only possible word order
        :return: None
        """
        unified_topologies =[]
        for topology in self.topologies:
            topology_field_keys = tuple(topology.keys())
            clean_topology = copy.deepcopy(topology)
            clean_topology.clear_gorns()
            for combination in values_combinations(topology.values()):
                new_topology = copy.deepcopy(clean_topology)
                for field_index, gorn in combination:
                    new_topology[topology_field_keys[field_index]] = (gorn,)
                unified_topologies.append(new_topology)

        # topologies validation, that all needed fields are filled
        self.topologies = []
        for topology in unified_topologies:
            if topology.isvalid():
                self.topologies.append(topology)
            else:
                print("invalid topology:", topology)

        if not self.ishead():
            for child in self:
                # nodes with GF at this level
                if isinstance(child, FeatTree):
                    child.alternatives()


    def split_alternatives(self):
        """
        split tree topologies to the separate trees
        :return:
        """
        if not self.ishead():
            alternatives = []

            for top in self.topologies:
                children_index = []

                for index, field_gorns in enumerate(top.values()):
                    for gorn in field_gorns:
                        for edge in self:
                            if edge.gorn == gorn:
                                children_index.append((index, edge))
                                break
                        else:
                            raise AssertionError("Gorn numbers:{} should must correspond edges: {}".format(field_gorns, self))
                children_order = [tup[1] for tup in sorted(children_index, key=lambda x: x[0])]
                new_self = FeatTree(self.label(), hclabel=self.hclabel(), children=children_order, gf=self.gf, ph=self.ph, parent=self.parent, gorn=self.gorn)
                # new_self = copy.copy(self)
                # list.__init__(new_self, children_order)
                copy_topology = copy.deepcopy(top)
                copy_topology.edge = new_self
                new_self.topologies = [copy_topology,]
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
                    new_self = copy.deepcopy(alternative)
                    for child in variation:
                        new_child = copy.deepcopy(child)
                        for index, altern_child in enumerate(new_self):
                            if altern_child.gorn == new_child.gorn:
                                new_self[index] = new_child
                                break
                        else:
                            raise Exception("Child not found", new_child)
                    forks.append(new_self)
            return forks

    def split_shared_topologies(self):
        """
        split shared topologies to separate trees
        :return:
        """
        if not self.ishead():
            alternatives = []

            if len(self.topologies) > 1:
                for top in self.topologies:
                    new_self = copy.deepcopy(self)
                    new_self.topologies = [copy.deepcopy(top),]
                    alternatives.append(new_self)
            else:
                alternatives=[self,]

            child_alternatives = []
            for child in self:
                if not child.ishead():
                    child_alternatives.append(child.split_shared_topologies())

            if not child_alternatives:
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
                        for index, altern_child in enumerate(new_self):
                            if altern_child.gorn == new_child.gorn:
                                new_self[index] = new_child
                                break
                        else:
                            raise Exception("Child not found", new_child)
                    if allowed_variation:
                        forks.append(new_self)
            return forks


def number_shared_fields(parent_edge, share_fields, base_topology):
    """
    set shared property for fields
    :param share_fields:  topology fields to share
    :param base_topology: topology with share_fields
    :return: actual number of fields to share (except fields with head edges, etc.)
    """
    number_shared_fields = 0
    for field in share_fields:
        field_gorns = base_topology[field]
        if field_gorns:
            for gorn in field_gorns:
                edge = parent_edge.find_edge(gorn)
                if edge.ishead():
                    break
            else:
                number_shared_fields += 1
    return number_shared_fields


def share_edges(parent_edge, share_fields, base_topology, parent_topologies):
    """

    :param share_fields: topology fields to share
    :param base_topology: topology with share_fields
    :param parent_topologies: where to share
    :return: None
    """
    for shared_field in share_fields:
        for field_key, field_gorns in base_topology.items():
            if field_key == shared_field:
                break
        else: continue

        if field_gorns:
            for gorn in field_gorns:
                edge = parent_edge.find_edge(gorn)
                if edge.ishead():
                    break
            # there is no head in field_gorns, we can do sharing
            else:
                # don't remove gorn from origin topology, because you can't find the field of it after sharing
                for parent_topology in parent_topologies:
                    if field_key in parent_topology.keys():
                        parent_field_gorns = parent_topology[field_key]

                        if parent_field_gorns:
                            # don't share to F fields if they are not empty
                            if field_key in (FT.F0,FT.F1):
                                continue

                            # check that we do not share to the head field
                            for gorn in parent_field_gorns:
                                edge = parent_edge.find_edge(gorn)
                                if edge.ishead():
                                    break
                            else:
                                parent_topology[field_key] = parent_field_gorns + field_gorns
                                parent_topology.field_map[field_key].shared_from = base_topology.field_map[field_key]
                                base_topology.field_map[field_key].shared_to = parent_topology.field_map[field_key]
                        else:
                                parent_topology[field_key] = parent_field_gorns + field_gorns
                                parent_topology.field_map[field_key].shared_from = base_topology.field_map[field_key]
                                base_topology.field_map[field_key].shared_to = parent_topology.field_map[field_key]


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
    else:
        if feature in featStructNonTerm:
            result.add(featStructNonTerm[feature])
    return tuple(result)

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
