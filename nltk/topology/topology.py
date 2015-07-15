from collections import OrderedDict
import copy
import inspect

from nltk import featstruct
from nltk.featstruct import CelexFeatStructReader, EXPRESSION
from nltk.grammar import FeatStructNonterminal, FeatureGrammar
from nltk.parse.featurechart import celex_preprocessing, FeatureTopDownChartParser
from nltk.topology.FeatTree import FeatTree, FT, PH, TAG, GF

__author__ = 'Denis Krusko: kruskod@gmail.com'


class Topology(OrderedDict):

    def __init__(self, ph=None, tag=None, features=None, fields=None, edge=None):
        self.ph = ph
        self.tag = tag
        self.features = features
        if fields:
            OrderedDict.__init__(self,((field.ft, field) for field in fields))
        else:
            OrderedDict.__init__(self)
        # self.fields = fields
        self.edge = edge

    def structure_str(self):
        out = "{}: {} {}\n {} {}\n".format('TOPOLOGY', self.ph, (self.features if self.features else ''),
                                           'TAG', self.tag if self.tag else '')
        fields_str = ''
        for field in self.values():
                fields_str += str(field) + '\n'
        return out + fields_str

    def __str__(self):
        out = repr(self.edge.hclabel())
        field_val = field_type = '|'
        #app = ''
        for type, field in self.items():
            field_type += "{:^8}|".format(str(type) + (str(field.mod) if field.mod else ''))
            field_val += "{:^8}|".format(str(*field.edges))
            # for e in field.edges:
            #     for t in e.topologies:
            #         app+= str(t) + '\n'

        field_type += '\n'
        field_val += '\n'
        border = '-' * (len(field_type) - 1) + '\n'
        return out + '\n' + border + field_type + border + field_val + border # + app

    def add_field(self, field):
        self[field.ft] = field
        field.topology = self
        for gram_func in field.grammatical_funcs:
            gram_func.field = field
        return self


class Field:
    # M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)), Pred: NP, Pred: AP;

    def __init__(self, ft=None, mod=None, grammatical_funcs=None, topology=None, dependencies=None):
        self.ft = ft
        self.topology = topology
        self.mod = mod
        self.grammatical_funcs = grammatical_funcs
        self.dependencies = dependencies
        self.edges = []

    def __str__(self):
        return " {:<5} {}: {}".format(self.ft, (self.mod if self.mod else ' '),
                                      [str(gram_func) for gram_func in
                                       self.grammatical_funcs] if self.grammatical_funcs else '')

    def add_gramfunc(self, gram_func):
        if not self.grammatical_funcs:
            self.grammatical_funcs = []
        self.grammatical_funcs.append(gram_func)
        return self

    def add_edge(self, edge):
        self.edges.append(edge)

    def fit(self, edge):
        if isinstance(edge, FeatTree):
            if self.gf == edge.gf:
                if self.expression:
                    return self.expression(edge)
                else:
                    return self.ph == edge.ph
        return False


class GramFunc:
    def __init__(self, gf=None, ph=None, expression=None, field=None):
        self.field = field
        self.gf = gf
        self.ph = ph
        self.expression = expression

    def fit(self, edge):
        if isinstance(edge, FeatTree):
            if self.expression:
                    return self.expression(edge, self.field)
            return self.gf == edge.gf and self.ph == edge.ph
        return False

    def __str__(self):
        return " {:<5}: {}".format(self.gf, (inspect.getsource(self.expression).strip()
                                             if self.expression else (self.ph if self.ph else '')))


def build_topologies():

    return (
        # TOPOLOGY NP
        # TAG np
        # NP1 : det: <DP OR NP OR QP>
        # NP2 : mod: ADJP
        #  NP3!: hd: n, hd: rel.pro, hd: dem.pro, hd: pers.pro
        #  NP4 : mod: PP, mod: S IF mod: S[topo=subrel] IN NP4
        # END

        (Topology(PH.NP, tag='np'))
            .add_field(Field(FT.NP1, grammatical_funcs=(
                GramFunc(GF.det, expression=lambda edge, field: edge.ph in (PH.DP, PH.NP, PH.QP)),)))

            .add_field(Field(FT.NP2, grammatical_funcs=(
                GramFunc(GF.mod, ph=PH.ADJP),)))

            .add_field(Field(FT.NP3, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, expression=lambda edge, field: edge.ph in (PH.n, PH.REL_PRO, PH.DEM_PRO, PH.pers_pro)),)))

            .add_field(Field(FT.NP4, grammatical_funcs=(
                GramFunc(GF.mod, expression=lambda edge, field: edge.ph == PH.PP or (edge.ph == PH.S and edge.has_feature({'topo': 'subrel'}))),))),

        # TOPOLOGY S[status=Fin|status=Infin/Fin/PInfin] // Subordinate order: SOV, OSV
        #  TAG subrel
        #  F1  !: subj: (NP (hd rel.pro)), dobj: (NP (hd rel.pro)) TAG dobjrel, iobj: (NP (hd rel.pro)) TAG iobjrel
        #  M2a : subj: NP[wh=false|!wh]
        #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M3  : subj: NP[wh=false|!wh] IF dobj: NP IN M2b OR iobj: NP IN M2c
        #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
        #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)), Pred: NP, Pred: AP
        #  M4c*: iobj: PP, mod: ADVP, mod: PP
        #  M5  : cmp: S[status=Infin|status=PastP]
        #  M6a : prt: PP OR ADVP
        #  M6b!: hd: v
        #  E1  : cmp: (S[status=Infin|status=PastP] * (cmp S) *)
        #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin], cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
        # END

        (Topology(PH.S, tag=TAG.subrel, features={'status': ('Fin', 'Infin', 'PInfin')}))
            .add_field(Field(FT.F1, mod='!', grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.REL_PRO)),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.tag == TAG.dobjrel and edge.has_child(GF.hd, PH.REL_PRO)),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.tag == TAG.iobjrel and edge.has_child(GF.hd, PH.REL_PRO)),
                    )))
            .add_field(Field(FT.M2a, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})), )))

            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro)))),)))

            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro)))),)))

            .add_field(Field(FT.M3, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (any(edge for edge in field.topology[FT.M2b].edges if edge.fit(GF.dobj, PH.NP)) or any(edge for edge in field.topology[FT.M2c].edges if edge.fit(GF.iobj, PH.NP)))),), dependencies = (FT.M2b, FT.M2c), ))

            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.REL_PRO, PH.DEM_PRO, PH.pers_pro))),)))

            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.REL_PRO, PH.DEM_PRO, PH.pers_pro))),
                GramFunc(GF.Pred, ph=PH.NP),
                GramFunc(GF.Pred, ph=PH.AP),
                )))

            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, ph=PH.ADVP),
                GramFunc(GF.mod, ph=PH.PP),
                )))

            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')})),
                )))

            .add_field(Field(FT.M6a, grammatical_funcs=(
                GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))

            .add_field(Field(FT.M6b, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, ph = PH.v),)))
            .add_field(Field(FT.E1, grammatical_funcs=(
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')})),
                )))

            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                )))
        ,
    )

    # TOPOLOGY PP
    #  TAG pp
    #  PP1 : hd: prep[location=pre]
    #  PP2 : obj: NP OR ADVP
    #  PP3 : hd: prep[location=post]
    # END
    #
    # TOPOLOGY ADJP
    #  ADJP1 : mod: ADVP
    #  ADJP2!: hd: adj
    # END
    # )


def simplify_expression(feat):
    # check arguments
    if isinstance(feat, tuple):
        if isinstance(feat[0], str) and len(feat) == 2:  # type of operator in expression
            operator = feat[0]
            expressions = simplify_expression(feat[1])

            if operator == 'OR':
                return expressions
            elif operator == 'AND':  # combine all features from all expressions
                result = expressions[0]
                for ex in expressions[1:]:
                    for key, val in ex.items():
                        if key in result:
                            if val != result[key]:
                                raise ValueError("Contradiction in the expresion:{} in {}".format(expressions, feat))
                        else:
                            result[key] = val
                return result
            else:
                raise ValueError("unknown operator:{} in {}".format(operator, feat))
        else:
            result = []
            for feat_d in feat:
                part_res = simplify_expression(feat_d)
                if isinstance(part_res, dict):
                    result.append(part_res)
                else:
                    result.extend(part_res)
            return result
    elif isinstance(feat, dict):
        result = []
        for key, val in feat.items():  # looking for cases like {'a':(1,2)}
            if isinstance(val, tuple):
                for sub_val in val:
                    feat_copy = feat.copy()
                    feat_copy[key] = sub_val
                    result.append(feat_copy)
        if result:
            return simplify_expression(tuple(result))
        else:
            return feat
    else:
        raise ValueError("wrong type of argument:", feat)


def process_dominance(tree, topology_rules):
    from nltk import Tree, TYPE
    # get all topolgies for tree
    node = tree.hclabel()
    tree_ph = node[TYPE]
    result = []
    for temp_topol in topology_rules:
        # chose a topology for the dominance structure item
        if tree_ph == temp_topol.ph.name:
            # unify works correct only with structures of the same type
            # create FeatStructNonterminal from topology features
            if temp_topol.features and len(node) > 1:
                top_fstruct = FeatStructNonterminal()
                top_fstruct[EXPRESSION] = temp_topol.features
                unif = featstruct.unify(node, top_fstruct)
            else:
                unif = True

            if unif:
                topology = copy.deepcopy(temp_topol)
                topology.edge = tree
                # tree.topologies.append(topology)
                # fill topology
                for child in tree:
                    if isinstance(child, Tree):
                        for field in topology.values():
                            for func in field.grammatical_funcs:
                                if func.fit(child):
                                    # add edge to topology
                                    field.add_edge(child)
                                    if not child.topologies and not child.ishead():
                                        child.topologies.extend(process_dominance(child, topology_rules))
                                    break
                result.append(topology)
    return result


def demo(print_times=True, print_grammar=False,
         print_trees=True, trace=2,
         sent='sehe ich', numparses=0):
    """
    A demonstration of the Earley parsers.
    """
    import time
    # The grammar for ChartParser and SteppingChartParser:
    from nltk.parse.earleychart import wordPresenceVerifier

    t = time.clock()
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    productions = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/lex_test.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)

    cp = FeatureTopDownChartParser(productions, trace=1)
    tokens = sent.split()
    parses = cp.parse(tokens)

    verifier = wordPresenceVerifier(tokens)
    dominance_structures = []
    count_trees = 0
    for tree in parses:
        count_trees += 1
        ver_result = verifier(tree)
        if ver_result:
            dominance_structures.append(tree)
        else:
            print(tree)
            print("Word presence verification result: {}\n".format(ver_result))

    topologies = build_topologies()
    if dominance_structures:
        print("####################################################")
        print("Dominance structures:")
        for tree in dominance_structures:
            print(tree)

        for tree in dominance_structures:
            feat_tree = FeatTree(tree)
            # featTree.draw()
            feat_tree.topologies.extend(process_dominance(feat_tree, topologies))
            print("####################################################")
            print(feat_tree)
    print("Time: {:.3f}s.\n".format (time.clock()-t))


def demo_simplifier():
    # fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    # productions = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/lex_test.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    # np0 = productions.productions()
    # np0lhs = np0.lhs();
    test = ('OR', (('OR', ({'a': (1, 2, 3, 4, 5), 'b': 2}, {'a': 2, 'c': 3})), ('AND', ({'b': 3, 'a': 5, 'c': 4}, {'c': 4}))))
    for i in simplify_expression(test):
        print(i)

if __name__ == "__main__":
    demo()
