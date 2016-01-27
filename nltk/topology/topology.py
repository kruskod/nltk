import copy
import hashlib
import inspect
import pickle
from collections import OrderedDict
from timeit import default_timer as timer

from nltk import featstruct
from nltk.draw.tree import TreeTabView
from nltk.featstruct import CelexFeatStructReader, TYPE, unify
from nltk.grammar import FeatStructNonterminal
from nltk.parse.featurechart import FeatureTopDownChartParser
from nltk.topology.FeatTree import FeatTree, FT, PH, TAG, GF
from nltk.topology.pgsql import build_rules

__author__ = 'Denis Krusko: kruskod@gmail.com'

class Topology(OrderedDict):

    def __eq__(self, other):
        if not isinstance(other, Topology):
            return NotImplemented
        elif self is other:
            return True
        else:
            if self.ph == other.ph and self.tag == other.tag and self.edge == other.edge:
                for field in self.values():
                    if (not field.ft in other) or repr(field) != repr(other[field.ft]):
                        return False
                return True
        return False

    def __hash__(self, *args, **kwargs):
        field_hash = 13
        for field in self.values():
            field_hash ^= hash(repr(field))
        result = field_hash ^ hash(self.ph) ^ hash(self.tag)
        return result

    def __init__(self, ph=None, tag=None, features=None, fields=None, edge=None, parent = None):
        self.ph = ph
        self.tag = tag
        self.features = features
        self.parent = parent
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
            # field_val += "{:^8}|".format(*field.edges)
            if field.edges:
                for edge in field.edges:
                    field_val += "{:^8}|".format(str(edge))

                # field_val += "{:^8}|".format(field.edges)
            # for e in field.edges:
            #     for t in e.topologies:
            #         app+= str(t) + '\n'

        field_type += '\n'
        field_val += '\n'
        border = '-' * (len(field_type) - 1) + '\n'
        return out + '\n' + border + field_type + border + field_val + border # + app

    def __repr__(self):
        class_name = self.__class__.__name__
        out = "{}:{}[".format(class_name,self.tag)
        return out + ",".join([repr(field) for field in self.values()]) + ']'
        # for type, field in self.items():
        #     if field.edges:
        #         out += "{}[".format(type)
        #         for edge in field.edges:
        #             out += "{} {}({})".format(edge.gf, edge.ph, edge.gorn)
        #         out += '],'
        # if out[-1] == ',':
        #     return out[:-1] + ']'
        # else:
        #     return out + ']'


    def add_field(self, field):
        self[field.ft] = field
        field.topology = self
        for gram_func in field.grammatical_funcs:
            gram_func.field = field
        return self

    def read_out(self, tokens, count_in_root = 0):
        leaves = []
        if tokens:
            for field in self.values():
                for id, edge in enumerate(field.edges):
                    if edge.topologies:
                        for top in edge.topologies:
                            if leaves and not isinstance(leaves[0], str):
                                for l in leaves:
                                    count = len(set(l))
                                    if count > 0:
                                        sub_fields = top.read_out(tokens[count - 1:], count)
                                    else:
                                        sub_fields = top.read_out(tokens, count)
                                    leaves.extend(sub_fields)
                                    if sub_fields:
                                        if isinstance(str, sub_fields[0]):
                                            l.extend(sub_fields)
                                        else:
                                            new_leaves = []
                                            for sub_field in sub_fields:
                                                new_leaves.append(leaves + sub_field)
                                            l = new_leaves
                            else:
                                count = len(set(leaves))
                                if count > 0:
                                    sub_fields = top.read_out(tokens[count - 1:], count)
                                else:
                                    sub_fields = top.read_out(tokens, count)
                                leaves.extend(sub_fields)
                    else:
                        edge_content = None
                        for ast in edge:
                                edge_content = ast.leaves()
                                for leaf in edge_content:
                                    if leaves and not isinstance(leaves[0], str):
                                        for l in leaves:
                                            count = len(set(leaves))
                                            if (len(tokens) > count and tokens[count] == leaf):
                                                l.append(leaf)
                                            elif (count_in_root > 0 and len(tokens) > count + 1 and tokens[count + 1] == leaf):
                                                l.append(leaf)
                                            else:
                                                #remove everything
                                                pass
                                    else:
                                        count = len(set(leaves))
                                        if (len(tokens) > count and tokens[count] == leaf):
                                            leaves.append(leaf)
                                        elif (count_in_root > 0 and len(tokens) > count + 1 and tokens[count + 1] == leaf):
                                            leaves.append(leaf)
                                        else:
                                            #remove everything
                                            pass
        return leaves

    def gorns(self):
        for field in self.values():
            if field.edges:
                yield from (e.gorn for e in field.edges)

    # def read_out(self):
    #     #check obligatory fields
    #     fields_map = {}
    #     obligatory_field_indexes = []
    #     for i, field in enumerate(self):
    #         if field.mod == '!':
    #             if not field.edges:
    #                 return None
    #             obligatory_field_indexes.append(i)
    #         if field.edges:
    #             fields_map[i] = field.edges
    #     #check heads order
    #     #check tree order


class Field:
    # M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)), Pred: NP, Pred: AP;

    # def __eq__(self, other):
    #     if not isinstance(other, Field):
    #         return NotImplemented
    #     elif self is other:
    #         return True
    #     else:
    #         if self.ft == other.ft and self.topology == other.topology and self.mod == other.mod and self.edges == other.edges:
    #             return True
    #     return False

    # def __hash__(self, *args, **kwargs):
    #     # edge_hash = 7
    #     # for edge in self.edges:
    #     #     edge_hash ^= hash(edge)
    #     # result = edge_hash ^ hash(self.ft) ^ hash(self.mod)
    #     # return result
    #     # return hash(repr(self))
    #     return hash(super(self,))

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

    def __repr__(self):
        count_edges = len(self.edges)
        if count_edges:
            out = '['
            for index, edge in enumerate(self.edges):
                out += "{} {}({})".format(edge.gf, edge.ph, edge.gorn)
                if index < count_edges -1 :
                    out += ' '
            return '{}{}]'.format(self.ft, out)
        return str(self.ft)

class GramFunc:
    def __init__(self, gf=None, ph=None, expression=None, field=None, tag=None):
        self.field = field
        self.gf = gf
        self.ph = ph
        self.expression = expression
        self.tag = tag

    def fit(self, edge):
        if isinstance(edge, FeatTree):
            if self.gf == edge.gf:
                if self.expression:
                    return self.expression(edge, self.field)
                else:
                    return self.ph == edge.ph
        return False

    def __str__(self):
        return " {:<5}: {}".format(self.gf, (inspect.getsource(self.expression).strip()
                                             if self.expression else (self.ph if self.ph else '')))

def build_topologies():

    return (

        # TOPOLOGY S[(status=Fin|status=Infin/Fin/PInfin),mood!=imperative] // Main order: SVO, OVS, VSO
        #  TAG main
        #  F0  : mod: PP OR ADVP IF (subj: IN F1 OR dobj: IN F1 OR iobj: IN F1 OR cmp: IN F1 TAG modf0)
        #  F1  : subj: NP AND NOT (NP (hd rel.pro)),
        #        dobj: NP AND NOT (NP (hd rel.pro)) TAG focusdobj,
        #        iobj: NP AND NOT (NP (hd rel.pro)) TAG focusiobj,
        #        cmp: S TAG focuscmp,
        #        mod: ADVP,
        #        mod: PP,
        #        prt: PP OR ADVP
        #  M1 !: hd: v
        #  M2a : subj: NP[wh=false|!wh]
        #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
        #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
        #        Pred: NP,
        #        Pred: AP
        #  M4c*: iobj: PP, mod: ADVP[!wh|wh=false],
        #        mod: PP[!wh|wh=false]
        #  M5  : cmp: S[status=Infin|status=PastP]
        #  M6a : prt: PP OR ADVP
        #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
        #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
        # END

        # parentField=((None, None)) means, that topology can be only root topology

        Topology(PH.S, tag=TAG.main, features={'status': ('Fin', 'Infin', 'PInfin')}, parent=((None, None),))
            .add_field(Field(FT.F0, grammatical_funcs=(
                GramFunc(GF.mod, expression=lambda edge, field: edge.ph == PH.PP or (edge.ph == PH.ADVP and any(edge for edge in field.topology[FT.F1].edges if edge.gf in (GF.subj, GF.obj, GF.iobj, GF.cmp)))), )))
            .add_field(Field(FT.F1, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.cmp, expression=lambda edge, field: edge.ph == PH.S, tag=TAG.focuscmp),
                GramFunc(GF.mod, ph=(PH.PP, PH.ADVP)), )))
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(GramFunc(GF.hd, ph=PH.v), )))
            .add_field(Field(FT.M2a, grammatical_funcs=(
                GramFunc(GF.subj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})),)))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro))),)))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro))),)))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.DEM_PRO, PH.rel_pro, PH.pers_pro))),)))
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.DEM_PRO, PH.rel_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, expression= lambda edge, field: (edge.ph == PH.ADVP or edge.ph == PH.PP) and edge.has_feature({'wh': False})), )))
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})),)))
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})), )))
        ,

        #  TOPOLOGY S[(status=Fin|status=Infin/Fin/PInfin),mood=imperative] // Main order: VO
        #  TAG imperative
        #  M1 !: hd: v
        #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
        #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
        #        Pred: NP,
        #        Pred: AP
        #  M4c*: iobj: PP,
        #        mod: ADVP[wh=false],
        #        mod: PP[wh=false]
        #  M5  : cmp: S[status=Infin|status=PastP]
        #  M6a : prt: PP OR ADVP
        #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
        #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
        # END

         Topology(PH.S, tag=TAG.imperative, features={'status': ('Fin', 'Infin', 'PInfin'), 'mood': 'imperative'}, parent=((None, None),)) # Main order: VO
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, PH.v), )))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro))),)))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro))),)))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.DEM_PRO, PH.rel_pro, PH.pers_pro))),)))
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.DEM_PRO, PH.rel_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, expression= lambda edge, field: (edge.ph == PH.ADVP or edge.ph == PH.PP) and edge.has_feature({'wh': False})), )))
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})),)))
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})), )))
        ,

        # TOPOLOGY S[status=Fin|status=Infin/Fin/PInfin] // Subordinate order: SOV, OSV
        #  TAG sub
        #  F1  : subj: NP[wh=true], dobj: NP[wh=true], iobj: NP[wh=true]
        #  M1 !: cmpr: CP
        #  M2a : subj: NP[wh=false|!wh]

        #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M3  : subj: NP[wh=false|!wh] IF dobj: NP IN M2b OR iobj: NP IN M2c
        #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
        #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
        #        Pred: NP,
        #        Pred: AP
        #  M4c*: iobj: PP, mod: ADVP, mod: PP
        #  M5  : cmp: S[status=Infin|status=PastP]
        #  M6a : prt: PP OR ADVP
        #  M6b!: hd: v
        #  E1  : cmp: (S[status=Infin|status=PastP] * (cmp S) *)
        #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin], cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
        # END

        Topology(PH.S, tag=TAG.sub, features={'status': ('Fin', 'Infin', 'PInfin'), 'mood': 'imperative'}) # Main order: VO
             .add_field(Field(FT.F1, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})), )))
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(
                GramFunc(GF.cmpr, PH.CP), )))
            .add_field(Field(FT.M2a, grammatical_funcs=(
                GramFunc(GF.subj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})), )))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro))),)))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro))),)))
            .add_field(Field(FT.M3, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (any(edge for edge in field.topology[FT.M2b].edges if edge.gf == GF.dobj and edge.ph == PH.NP))
                    or (any(edge for edge in field.topology[FT.M2c].edges if edge.gf == GF.iobj and edge.ph == PH.NP))), )))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.DEM_PRO, PH.rel_pro, PH.pers_pro))),
                  GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, ph=(PH.ADVP, PH.PP)), )))
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})),)))
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            .add_field(Field(FT.M6b, mod='!', grammatical_funcs=(GramFunc(GF.hd, ph=PH.v), )))
            .add_field(Field(FT.E1, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})), )))
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})), )))
        ,

        # TOPOLOGY S[status=Fin|status=Infin/Fin/PInfin] // Subordinate order: SOV, OSV
        #  TAG subv2
        #  F1  : subj: NP[wh=true], dobj: NP[wh=true], iobj: NP[wh=true]
        #  M1 !: cmpr: CP
        #  M1a!: subj: NP, dobj: NP, iobj: NP, cmp: S, mod: ADVP, mod: PP
        #  M1b!: hd: v
        #  M2a : subj: NP[wh=false|!wh]
        #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
        #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
        #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)), Pred: NP, Pred: AP
        #  M4c*: iobj: PP, mod: ADVP[!wh|wh=false], mod: PP[!wh|wh=false]
        #  M5  : cmp: S[status=Infin|status=PastP]
        #  M6a : prt: PP OR ADVP
        #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin], cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
        # END


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

        (Topology(PH.S, tag=TAG.subrel, features={'status': ('Fin', 'Infin', 'PInfin')}, parent=((GF.mod, PH.NP),)))
            .add_field(Field(FT.F1, mod='!', grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.dobjrel),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.iobjrel),
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
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.DEM_PRO, PH.pers_pro))),)))

            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.DEM_PRO, PH.pers_pro))),
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
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')}) ),)))

            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                )))
        ,

        #  TOPOLOGY S[status=PInfin|status=PastP|status=Infin]
        #  TAG inf;
        #  F1  : dobj:NP[wh=true], dobj: NP[wh=false|!wh] AND NOT (NP (hd rel.pro)) TAG focusdobj, dobj: (NP (hd rel.pro)) TAG dobjrel, iobj:NP[wh=true], iobj: NP[wh=false|!wh] AND NOT (NP (hd rel.pro)) TAG focusiobj, iobj: (NP (hd rel.pro)) TAG iobjrel, cmp: S TAG focuscmp;
        #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>));
        #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>));
        #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>));
        #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)), Pred: NP, Pred: AP;
        #  M4c*: iobj: PP, mod: ADVP, mod: PP;
        #  M5  : cmp: S[status=Infin|status=PastP];
        #  M6b!: hd: v;
        #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin], cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
        # END

         (Topology(PH.S, tag=TAG.inf, features={'status': ('PastP', 'Infin', 'PInfin')}))
            .add_field(Field(FT.F1, mod='!', grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not (edge.has_child(GF.hd, (PH.rel_pro,))), tag = TAG.focusdobj),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.dobjrel),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro), tag = TAG.focusiobj),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.iobjrel),
                GramFunc(GF.cmp, ph=PH.S, tag = TAG.focuscmp),
                    )))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro)))),)))

            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (edge.has_child(GF.hd, (PH.DEM_PRO, PH.pers_pro)))),)))

            .add_field(Field(FT.M3, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (any(edge for edge in field.topology[FT.M2b].edges if edge.fit(GF.dobj, PH.NP)) or any(edge for edge in field.topology[FT.M2c].edges if edge.fit(GF.iobj, PH.NP)))),), dependencies = (FT.M2b, FT.M2c), ))

            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.DEM_PRO, PH.pers_pro))),)))

            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.DEM_PRO, PH.pers_pro))),
                GramFunc(GF.Pred, ph=PH.NP),
                GramFunc(GF.Pred, ph=PH.AP),
                )))

            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, ph=(PH.ADVP, PH.PP)),
                )))

            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')})),
                )))
            .add_field(Field(FT.M6b, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, ph = PH.v),)))

            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                )))
        ,


        # TOPOLOGY NP
        # TAG np
        # NP1 : det: <DP OR NP OR QP>
        # NP2 : mod: ADJP
        #  NP3!: hd: n, hd: rel.pro, hd: dem.pro, hd: pers.pro
        #  NP4 : mod: PP, mod: S IF mod: S[topo=subrel] IN NP4
        # END

        Topology(PH.NP, tag='np')
            .add_field(Field(FT.NP1, grammatical_funcs=(
                GramFunc(GF.det, expression=lambda edge, field: edge.ph in (PH.DP, PH.NP, PH.QP)),)))

            .add_field(Field(FT.NP2, grammatical_funcs=(
                GramFunc(GF.mod, ph=PH.ADJP),)))

            .add_field(Field(FT.NP3, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, expression=lambda edge, field: edge.ph in (PH.n, PH.rel_pro, PH.DEM_PRO, PH.pers_pro)),)))

            .add_field(Field(FT.NP4, grammatical_funcs=(
                GramFunc(GF.mod, expression=lambda edge, field: edge.ph == PH.PP or (edge.ph == PH.S and edge.has_feature({'topo': 'subrel'}))),))) ,


        # TOPOLOGY PP
        #  TAG pp
        #  PP1 : hd: prep[location=pre]
        #  PP2 : obj: NP OR ADVP
        #  PP3 : hd: prep[location=post]
        # END

        Topology(PH.PP, tag='pp')
            .add_field(Field(FT.PP1, grammatical_funcs=(
                GramFunc(GF.hd, expression=lambda edge, field: edge.ph == PH.prep and edge.has_feature({'location': 'pre'})),)))

            .add_field(Field(FT.PP2, grammatical_funcs=(
                GramFunc(GF.obj, expression=lambda edge, field: edge.ph == PH.NP or edge.ph == PH.ADVP),)))

            .add_field(Field(FT.PP3, grammatical_funcs=(
                GramFunc(GF.hd, expression=lambda edge, field: edge.ph == PH.prep and edge.has_feature({'location': 'post'})),))) ,

        # TOPOLOGY ADJP
        #  ADJP1 : mod: ADVP
        #  ADJP2!: hd: adj
        # END
        # )

        Topology(PH.ADJP, tag='pp')
            .add_field(Field(FT.ADJP1, grammatical_funcs=(
                GramFunc(GF.mod, ph=PH.ADJP),)))

            .add_field(Field(FT.ADJP2, mod='!', grammatical_funcs=(
                GramFunc(GF.mod, ph=PH.adj),))) ,
    )


def process_dominance(tree, topology_rules):
    from nltk import Tree, TYPE
    # get all topolgies for tree
    node = tree.hclabel()
    result = []
    for temp_topol in topology_rules:
        # chose a topology for the dominance structure item
        if tree.ph == temp_topol.ph:
            if temp_topol.parent:
                parent_node = tree.parent
                if not parent_node or not isinstance(parent_node, FeatTree):
                    parent_gf_ph = (None, None)
                else :
                    parent_gf_ph = (parent_node.gf, parent_node.ph)
                if parent_gf_ph not in temp_topol.parent:
                    continue

            # unify works correct only with structures of the same type
            # create FeatStructNonterminal from topology features
            if temp_topol.features and len(node) > 1:
                top_fstruct = FeatStructNonterminal(temp_topol.features)
                #top_fstruct[EXPRESSION] = temp_topol.features
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
         sent='Monopole sollen geknackt werden', numparses=0):
    """
    Monopole sollen geknackt werden

    sent examples:
        wen habe ich gesehen
        Monopole sollen geknackt werden und Märkte sollen getrennt werden.
        Monopole sollen geknackt und Märkte getrennt werden.
        Monopole sollen geknackt werden und Märkte getrennt.

        Katzen werden geschlagen - läuft 20.11.15

        sehe ich den Mann

    A demonstration of the Earley parsers.
    """
    # The grammar for ChartParser and SteppingChartParser:
    from nltk.parse.earleychart import wordPresenceVerifier

    t = timer()
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    # productions = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/minlex_test.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    # str_prod = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/monopole.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    tokens = sent.split()
    #get_rules(tokens)
    # str_prod = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/query.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    # filter features and minify expressions in productions
    # minimized_productions = []
    # extensions = read_extensions()
    # for prod in str_prod.productions():
    #     lhs = minimize_nonterm(prod.lhs())
    #     select_extensions = [ext for ext in extensions if ext['lhs'] == lhs[TYPE]]
    #     rhs = list(prod.rhs())
    #     for i, nt in enumerate(rhs):
    #         for ext in select_extensions:
    #             if ext['rhs'] == nt[TYPE] and nt.has_feature({GRAM_FUNC_FEATURE:ext[GRAM_FUNC_FEATURE]}):
    #                 if 'cond' in ext:
    #                     feat = fstruct_reader.fromstring('[' + ext['cond'] + ']')
    #                     if not nt.has_feature(feat):
    #                         continue
    #                     # else:
    #                     #     print("Condition match!!!!!!!")
    #                 nt = unify(nt, fstruct_reader.fromstring(ext['feat']))
    #                 break
    #         if nt:
    #             rhs[i] = minimize_nonterm(nt)
    #         else:
    #             rhs = None
    #             break
    #     if rhs:
    #         minimized_productions.append(Production(lhs, rhs).process_inherited_features())
    #
    # productions = FeatureGrammar(str_prod.start(), minimized_productions)
    # print(productions.productions()[0].rhs()[0])
    cp = FeatureTopDownChartParser(build_rules(tokens, fstruct_reader), use_agenda=True, trace=1)

    dominance_structures = []
    count_trees = 0
    # for tokens_variation in set(itertools.permutations(tokens)):
    parses = list(cp.parse(tokens))
    verifier = wordPresenceVerifier(tokens)
    for tree in parses:
        count_trees += 1
        ver_result = verifier(tree)
        has_subj = False
        for sub_tree in tree:
            if sub_tree._label[TYPE] == 'subj':
                has_subj = True
                break
        if ver_result and has_subj and tree._label.has_feature({'status': 'Fin'}):
            try:
                dominance_structures.append(tree)
            except ValueError:
                pass
        #print(tree)
        #print("Word presence verification result: {}".format(ver_result))
    # topologies = build_topologies()
    end_time = timer()
    if dominance_structures:
        print("####################################################")
        print("Dominance structures:")
        dominance_structures = sorted(dominance_structures, key=lambda tree: ' '.join(tree.leaves()).lower())

        for tree in dominance_structures:
            print(tree)
            # feat_tree = FeatTree(tree)
            # feat_tree.topologies.extend(process_dominance(feat_tree, topologies))
            # print(feat_tree)
            # for top in feat_tree.topologies:
            #     print(top.read_out(tokens))
        end_time = timer()
        with open('../../fsa/dominance_structures.dump', 'wb') as f:
            pickle.dump(dominance_structures, f, pickle.HIGHEST_PROTOCOL)
    print("####################################################")
    print("Nr trees:", count_trees)
    print("Nr Dominance structures:", len(dominance_structures))
    print('Count of productions:', len(cp._grammar._productions))
    print("Time: {:.3f}s.\n".format (end_time - t))

    if dominance_structures:
        TreeTabView(*dominance_structures[:20])
# TODO
# split features like case=(dat/nom/acc) to separate rules
# add feature to lemma
# check Der Mann will ich sehen
# add voice=passive for lemma Lexikon

def unify_demo():
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    fs1 = fstruct_reader.fromstring('N[status=Infin]')
    fs2 = fstruct_reader.fromstring('N[wh=true]')
    result = unify(fs1, fs2)
    print(result)

if __name__ == "__main__":
    #demo_simplifier()
    #unify_demo()
    demo()
