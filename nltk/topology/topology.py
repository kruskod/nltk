import copy

import inspect
import pickle
from collections import OrderedDict, Iterable
from timeit import default_timer as timer

from nltk import featstruct
from nltk.draw.tree import TreeTabView
from nltk.featstruct import CelexFeatStructReader, TYPE, unify
from nltk.grammar import FeatStructNonterminal, FeatureGrammar
from nltk.parse.featurechart import FeatureTopDownChartParser, celex_preprocessing
from nltk.topology.FeatTree import FeatTree, FT, PH, TAG, GF
from nltk.topology.pgsql import build_rules

__author__ = 'Denis Krusko: kruskod@gmail.com'

class Topology(OrderedDict):

    def __init__(self, ph=None, tag=None, features=None, fields=None, parent_restriction = None):
        self.ph = ph
        self.tag = tag
        self.features = features
        # parent_restriction=((None, None)) "((some GF, some PH))" means, that topology can be only root topology
        self.parent_restriction = parent_restriction
        if fields:
            self.field_map = {field.ft: field for field in fields}
            OrderedDict.__init__(self,{field.ft:set() for field in fields})
        else:
            self.field_map = dict()
            OrderedDict.__init__(self)
        # inner variable to control alternatives generation by sharing
        self.shared_trace = ''
        self.ls = self.rs = 0

    def isvalid(self):
        """
        :return: True if all needed fields are filled.
        """
        for ft, field_gorns in self.items():
            if "!" == self.field_map[ft].mod and not field_gorns:
                return False
        return True

    def __eq__(self, other):
        if not isinstance(other, Topology):
            return NotImplemented
        elif self is other:
            return True
        else:
            if self.ph == other.ph and self.tag == other.tag:
                for field, field_gorns in self.items():
                    if (not field in other) or field_gorns != other[field]:
                        return False
                return True
        return False

    def __hash__(self, *args, **kwargs):
        field_hash = 13
        for field in self.values():
            field_hash ^= hash(field)
        result = field_hash ^ hash(self.ph) ^ hash(self.tag)
        return result

    def short_str(self):
        return "{}({})".format(self.ph, self.tag)

    def __str__(self):
        out = self.short_str()
        field_type = '{'
        for ft, field_gorns in self.items():
            if field_gorns:
                field_type += self.field_map[ft].short_str() + str(field_gorns) + '|'
        return out + field_type[:-1] + '}'

    def __repr__(self):
        return "{}:{}".format(self.__class__.__name__, str(self))

    def add_field(self, field):
        field.topology = self
        self[field.ft] = ()
        self.field_map[field.ft] = field
        for gram_func in field.grammatical_funcs:
            gram_func.field = field
        return self

    def gorns(self):
        for gorns in self.values():
            if gorns:
                yield from (gorn for gorn in gorns)


class Field:
    # M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)), Pred: NP, Pred: AP;

    def __init__(self, ft=None, mod=None, grammatical_funcs=None, dependencies=None):

        self.ft = ft
        self.mod = mod
        self.grammatical_funcs = grammatical_funcs
        self.dependencies = dependencies
        self.shared = False

    def short_str(self):
        return str(self.ft) + (self.mod if self.mod else '')

    def add_gramfunc(self, gram_func):
        if not self.grammatical_funcs:
            self.grammatical_funcs = []
        self.grammatical_funcs.append(gram_func)
        return self

    def __eq__(self, other):
        if not isinstance(other, Field):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.ft == other.ft
        return False

    def __hash__(self, *args, **kwargs):
        return hash(self.ft)

    def __str__(self):
        return " {}:{}".format(self.short_str(),
                  [str(gram_func) for gram_func in
                   self.grammatical_funcs] if self.grammatical_funcs else '')

    def __repr__(self):
        return self.__str__()

class GramFunc:
    def __init__(self, gf=None, ph=None, expression=None, field=None, tag=None):
        self.field = field
        self.gf = gf
        self.ph = ph
        self.expression = expression
        self.tag = tag

    def fit(self, edge):
        assert isinstance(edge, FeatTree)
        if self.gf == edge.gf:
            if self.expression:
                return self.expression(edge, self.field)
            elif self.ph:
                if isinstance(self.ph, Iterable):
                    return edge.ph in self.ph
                else:
                    return edge.ph == self.ph
            else:   # this idea reflects matching for "! category = none"
                return True
        return False

    def __str__(self):
        return " {:<5}: {}".format(self.gf, (inspect.getsource(self.expression).strip()
                                             if self.expression else (self.ph if self.ph else '')))

def build_topologies():

    return (
        # TOPOLOGY S[(status=Fin|status=Infin/Fin/PInfin),mood!=imperative] // Main order: SVO, OVS, VSO
        #  TAG main
        Topology(PH.S, tag=TAG.main, features={'status': ('Fin', 'Infin', 'PInfin'), 'mood':('indicative', 'subjunctive')}, parent_restriction=((None, None),))
            #  F0  : mod: PP OR ADVP OR NP IF (subj: IN F1 OR dobj: IN F1 OR iobj: IN F1 OR cmp: IN F1 TAG modf0)
            .add_field(Field(FT.F0, grammatical_funcs=(
                GramFunc(GF.mod, expression=lambda edge, field: edge.ph in (PH.PP, PH.ADVP, PH.NP) and any(gorn for gorn in field.topology[FT.F1] if edge.parent.find_edge(gorn).gf in (GF.subj, GF.obj, GF.iobj, GF.cmp))),
                ), dependencies=(FT.F1,)))
            #  F1  : subj: NP AND NOT (NP (hd rel.pro)),
            #        dobj: NP AND NOT (NP (hd rel.pro)) TAG focusdobj,
            #        iobj: NP AND NOT (NP (hd rel.pro)) TAG focusiobj,
            #        cmp: S TAG focuscmp,
            #        mod: ADVP,
            #        mod: PP,
            #        prt: PP OR ADVP
            .add_field(Field(FT.F1, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and not edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.cmp, expression=lambda edge, field: edge.ph == PH.S, tag=TAG.focuscmp),
                GramFunc(GF.mod, ph=(PH.PP, PH.ADVP, PH.NP)), )))
            #  M1 !: hd: v
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(GramFunc(GF.hd, ph=PH.v),)))
            #  M2a : subj: NP[wh=false|!wh]
            .add_field(Field(FT.M2a, grammatical_funcs=(
                GramFunc(GF.subj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})),)))
            #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),)))
            #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
            #        Pred: NP,
            #        Pred: AP
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            #  M4c*: iobj: PP, mod: ADVP[!wh|wh=false],
            #        mod: PP[!wh|wh=false]
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, expression= lambda edge, field: edge.ph in (PH.ADVP, PH.PP,PH.NP) and edge.has_feature({'wh': False})), ))) # Added or edge.ph == PH.NP to match COMPASS behavior
            #  M5  : cmp: S[status=Infin|status=PastP]
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})),)))
            #  M6a : prt: PP OR ADVP
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
            #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod, expression= lambda edge, field: (edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})) or edge.ph == PH.NP),
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})), )))
        # END TOPOLOGY S TAG main
        ,

        #  TOPOLOGY S[(status=Fin|status=Infin/Fin/PInfin),mood=imperative] // Main order: VO
        #  TAG imperative
         Topology(PH.S, tag=TAG.imperative, features={'status': ('Fin', 'Infin', 'PInfin'), 'mood': 'imperative'}, parent_restriction=((None, None),)) # Main order: VO
            #  M1 !: hd: v
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(GramFunc(GF.hd, PH.v), )))
            #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),)))
            #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
            #        Pred: NP,
            #        Pred: AP
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            #  M4c*: iobj: PP,
            #        mod: ADVP[wh=false],
            #        mod: PP[wh=false]
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, expression= lambda edge, field: edge.ph in (PH.ADVP,PH.PP,PH.NP) and edge.has_feature({'wh': False})), )))
            #  M5  : cmp: S[status=Infin|status=PastP]
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})),)))
            #  M6a : prt: PP OR ADVP
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
            #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod, expression= lambda edge, field: (edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})) or edge.ph == PH.NP),
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})), )))
        # END TOPOLOGY S TAG imperative
        ,

        # TOPOLOGY S[status=Fin|status=Infin/Fin/PInfin] // Subordinate order: SOV, OSV
        #  TAG sub
          Topology(PH.S, tag=TAG.sub, features={'status': ('Fin', 'Infin', 'PInfin')}, parent_restriction=((None, PH.S),(GF.mod, PH.S),(GF.cmp, PH.S))) # Subordinate order: SOV, OSV
            #  F1  : subj: NP[wh=true], dobj: NP[wh=true], iobj: NP[wh=true]
            .add_field(Field(FT.F1, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})), )))
            #  M1 !: cmpr: CP
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(
                GramFunc(GF.cmpr, PH.CP), )))
            #  M2a : subj: NP[wh=false|!wh]
            .add_field(Field(FT.M2a, grammatical_funcs=(
                GramFunc(GF.subj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})), )))
            #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M3  : subj: NP[wh=false|!wh] IF dobj: NP IN M2b OR iobj: NP IN M2c
            .add_field(Field(FT.M3, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})
                        and (any(gorn for gorn in field.topology[FT.M2b] if edge.parent.find_edge(gorn).gf == GF.dobj and edge.parent.find_edge(gorn).ph == PH.NP)
                             or any(gorn for gorn in field.topology[FT.M2c] if edge.parent.find_edge(gorn).gf == GF.iobj and edge.parent.find_edge(gorn).ph == PH.NP))
                         ),), dependencies=(FT.M2b,FT.M2c)))
            #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression= lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),
                )))
            #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
            #        Pred: NP,
            #        Pred: AP
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)),)))
            #  M4c*: iobj: PP, mod: ADVP, mod: PP
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, ph=(PH.ADVP, PH.PP,PH.NP)), )))
            #  M5  : cmp: S[status=Infin|status=PastP]
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})),)))
            #  M6a : prt: PP OR ADVP
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            #  M6b!: hd: v
            .add_field(Field(FT.M6b, mod='!', grammatical_funcs=(GramFunc(GF.hd, ph=PH.v), )))
            #  E1  : cmp: (S[status=Infin|status=PastP] * (cmp S) *)
            .add_field(Field(FT.E1, grammatical_funcs=(
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin','PastP')})), )))
            #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
            #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod, expression= lambda edge, field: (edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})) or edge.ph == PH.NP),
                GramFunc(GF.cmp, expression= lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})), )))
        # END TOPOLOGY S TAG sub
        ,


        # TOPOLOGY S[status=Fin|status=Infin/Fin/PInfin] // Subordinate order: SOV, OSV
        #  TAG subv2
        Topology(PH.S, tag=TAG.subv2, features={'status': ('Fin', 'Infin', 'PInfin')},parent_restriction=((None, PH.S),(GF.mod, PH.S),(GF.cmp, PH.S)))  # Subordinate order: SOV, OSV
            #  F1  : subj: NP[wh=true], dobj: NP[wh=true], iobj: NP[wh=true]
            .add_field(Field(FT.F1, grammatical_funcs=(
            GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
            GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
            GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),)))
            #  M1 !: cmpr: CP
            .add_field(Field(FT.M1, mod='!', grammatical_funcs=(
            GramFunc(GF.cmpr, PH.CP),)))
            #  M1a!: subj: NP, dobj: NP, iobj: NP, cmp: S, mod: ADVP, mod: PP
            .add_field(Field(FT.M1a, mod='!', grammatical_funcs=(
            GramFunc(GF.subj, ph=PH.NP),
            GramFunc(GF.dobj, ph=PH.NP),
            GramFunc(GF.iobj, ph=PH.NP),
            GramFunc(GF.cmp, ph=PH.S),
            GramFunc(GF.mod, ph=(PH.ADVP, PH.PP, PH.NP)),
            )))
            #  M1b!: hd: v
            .add_field(Field(FT.M1b, mod='!', grammatical_funcs=(
            GramFunc(GF.hd, PH.v),)))
            #  M2a : subj: NP[wh=false|!wh]
            .add_field(Field(FT.M2a, grammatical_funcs=(
            GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})),)))
            #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2b, grammatical_funcs=(
            GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2c, grammatical_funcs=(
            GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
            .add_field(Field(FT.M4a, grammatical_funcs=(
            GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))), )))
            #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
            #        Pred: NP,
            #        Pred: AP
            .add_field(Field(FT.M4b, grammatical_funcs=(
            GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.dem_pro, PH.rel_pro, PH.pers_pro))),
            GramFunc(GF.Pred, ph=(PH.NP, PH.AP)),)))
            #  M4c*: iobj: PP, mod: ADVP[!wh|wh=false], mod: PP[!wh|wh=false]
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
            GramFunc(GF.iobj, ph=PH.PP),
            GramFunc(GF.mod, expression=lambda edge, field: edge.ph in (PH.ADVP, PH.PP, PH.NP) and edge.has_feature({'wh': False})),)))
            #  M5  : cmp: S[status=Infin|status=PastP]
            .add_field(Field(FT.M5, grammatical_funcs=(
            GramFunc(GF.cmp, expression=lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')})),)))
            #  M6a : prt: PP OR ADVP
            .add_field(Field(FT.M6a, grammatical_funcs=(GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)),)))
            #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
            #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
            .add_field(Field(FT.E2, grammatical_funcs=(
            GramFunc(GF.mod, expression=lambda edge, field: (edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})) or edge.ph == PH.NP),
            GramFunc(GF.cmp, expression=lambda edge, field: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),)))
        # END TOPOLOGY S TAG subv2
        ,


        # TOPOLOGY S[status=Fin|status=Infin/Fin/PInfin] // Subordinate order: SOV, OSV
        #  TAG subrel
        Topology(PH.S, tag=TAG.subrel, features={'status': ('Fin', 'Infin', 'PInfin')}, parent_restriction=((GF.mod, PH.NP)))
            # F1!: subj: (NP (hd rel.pro)),
            #      dobj: (NP (hd rel.pro)) TAG dobjrel,
            #      iobj: (NP (hd rel.pro)) TAG iobjrel
            .add_field(Field(FT.F1, mod='!', grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro)),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.dobjrel),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.iobjrel), )))
            #  M2a : subj: NP[wh=false|!wh]
            .add_field(Field(FT.M2a, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})), )))
            #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro)))),)))
            #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>))
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and (edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro)))),)))
            #  M3  : subj: NP[wh=false|!wh] IF dobj: NP IN M2b OR iobj: NP IN M2c
            .add_field(Field(FT.M3, grammatical_funcs=(
                GramFunc(GF.subj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False})
                    and (any(gorn for gorn in field.topology[FT.M2b] if edge.parent.find_edge(gorn).gf == GF.dobj and edge.parent.find_edge(gorn).ph == PH.NP)
                        or any(gorn for gorn in field.topology[FT.M2c] if edge.parent.find_edge(gorn).gf == GF.iobj and edge.parent.find_edge(gorn).ph == PH.NP))),), dependencies=(FT.M2b, FT.M2c)))
            #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>))
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.dem_pro, PH.pers_pro))),)))
            #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
            #  Pred: NP, Pred: AP
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.dem_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            #  M4c*: iobj: PP,
            #        mod: ADVP,
            #        mod: PP
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, ph=(PH.ADVP, PH.PP, PH.NP)), )))
            #  M5  : cmp: S[status=Infin|status=PastP]
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')})), )))
            #  M6a : prt: PP OR ADVP
            .add_field(Field(FT.M6a, grammatical_funcs=(
                GramFunc(GF.prt, ph=(PH.PP, PH.ADVP)), )))
            #  M6b!: hd: v
            .add_field(Field(FT.M6b, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, ph = PH.v),)))
            #  E1  : cmp: (S[status=Infin|status=PastP] * (cmp S) *)
            .add_field(Field(FT.E1, grammatical_funcs=(
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')}) ),)))
            #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin], cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod,  expression=lambda edge, field=None: (edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})) or edge.ph == PH.NP),
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                )))
            # END TOPOLOGY S TAG subrel
        ,


         #  TOPOLOGY S[status=PInfin|status=PastP|status=Infin]
         #  TAG inf;
         Topology(PH.S, tag=TAG.inf, features={'status': ('PastP', 'Infin', 'PInfin')}, parent_restriction=((None, PH.S),(GF.mod, PH.S),(GF.cmp, PH.S)))
            #  F1  : dobj:NP[wh=true],
            #        dobj: NP[wh=false|!wh] AND NOT (NP (hd rel.pro)) TAG focusdobj,
            #        dobj: (NP (hd rel.pro)) TAG dobjrel,
            #        iobj:NP[wh=true],
            #        iobj: NP[wh=false|!wh] AND NOT (NP (hd rel.pro)) TAG focusiobj,
            #        iobj: (NP (hd rel.pro)) TAG iobjrel,
            #        cmp: S TAG focuscmp;
            .add_field(Field(FT.F1, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro,)), tag = TAG.focusdobj),
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.dobjrel),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': True})),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, PH.rel_pro), tag = TAG.focusiobj),
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_child(GF.hd, PH.rel_pro), tag = TAG.iobjrel),
                GramFunc(GF.cmp, ph=PH.S, tag = TAG.focuscmp),
                    )))
            #  M2b : dobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>));
            .add_field(Field(FT.M2b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M2c : iobj: (NP[wh=false|!wh] (hd <dem.pro OR pers.pro>));
            .add_field(Field(FT.M2c, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and edge.has_child(GF.hd, (PH.dem_pro, PH.pers_pro))),)))
            #  M4a : iobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>));
            .add_field(Field(FT.M4a, grammatical_funcs=(
                GramFunc(GF.iobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.dem_pro, PH.pers_pro))),)))
            #  M4b : dobj: NP[wh=false|!wh] AND NOT (NP (hd <rel.pro OR dem.pro OR pers.pro>)),
            #        Pred: NP,
            #        Pred: AP;
            .add_field(Field(FT.M4b, grammatical_funcs=(
                GramFunc(GF.dobj, expression=lambda edge, field: edge.ph == PH.NP and edge.has_feature({'wh': False}) and not edge.has_child(GF.hd, (PH.rel_pro, PH.dem_pro, PH.pers_pro))),
                GramFunc(GF.Pred, ph=(PH.NP, PH.AP)), )))
            #  M4c*: iobj: PP, mod: ADVP, mod: PP;
            .add_field(Field(FT.M4c, mod='*', grammatical_funcs=(
                GramFunc(GF.iobj, ph=PH.PP),
                GramFunc(GF.mod, ph=(PH.ADVP, PH.PP,PH.NP)),
                )))
            #  M5  : cmp: S[status=Infin|status=PastP];
            .add_field(Field(FT.M5, grammatical_funcs=(
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Infin', 'PastP')})),
                )))
            #  M6b!: hd: v;
            .add_field(Field(FT.M6b, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, ph = PH.v),)))
            #  E2  : mod: S[status=Fin|status=Infin/Fin/PInfin],
            #        cmp: S[status=Fin|status=PInfin|status=Infin/Fin/PInfin]
            .add_field(Field(FT.E2, grammatical_funcs=(
                GramFunc(GF.mod,  expression=lambda edge, field=None: (edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})) or edge.ph == PH.NP),
                GramFunc(GF.cmp,  expression=lambda edge, field=None: edge.ph == PH.S and edge.has_feature({'status': ('Fin', 'Infin', 'PInfin')})),
                )))
        # END TOPOLOGY S TAG inf
        ,


        # TOPOLOGY NP
        # TAG np
        Topology(PH.NP, tag=TAG.np)
            # NP1 : det: <DP OR NP OR QP>
            .add_field(Field(FT.NP1, grammatical_funcs=(
                GramFunc(GF.det, ph=(PH.DP, PH.NP, PH.QP)),)))
            # NP2 : mod: ADJP
            .add_field(Field(FT.NP2, grammatical_funcs=(
                GramFunc(GF.mod, ph=PH.ADJP),)))
            #  NP3!: hd: n, hd: rel.pro, hd: dem.pro, hd: pers.pro
            .add_field(Field(FT.NP3, mod='!', grammatical_funcs=(
                GramFunc(GF.hd, ph=(PH.n, PH.rel_pro, PH.dem_pro, PH.pers_pro)),)))
            #  NP4 : mod: PP, mod: S IF mod: S[topo=subrel] IN NP4
            .add_field(Field(FT.NP4, grammatical_funcs=(
                GramFunc(GF.mod, expression=lambda edge, field: edge.ph == PH.PP or (edge.ph == PH.S and edge.has_feature({'topo': 'subrel'}))),)))
        # END TOPOLOGY NP
        ,


        # TOPOLOGY PP
        #  TAG pp
        Topology(PH.PP, tag=TAG.pp)
            #  PP1 : hd: prep[location=pre]
            .add_field(Field(FT.PP1, grammatical_funcs=(
                GramFunc(GF.hd, expression=lambda edge, field: edge.ph == PH.prep and edge.has_feature({'location': 'pre'})),)))
            #  PP2 : obj: NP OR ADVP
            .add_field(Field(FT.PP2, grammatical_funcs=(
                GramFunc(GF.obj, ph=(PH.NP, PH.ADVP)), )))
            #  PP3 : hd: prep[location=post]
            .add_field(Field(FT.PP3, grammatical_funcs=(
                GramFunc(GF.hd, expression=lambda edge, field: edge.ph == PH.prep and edge.has_feature({'location': 'post'})),)))
        # END TOPOLOGY PP
        ,


        # Adjp
        # definition ~ [category = ADJP & defined = 'true'] ~ > [slot = ADJP1 & function = mod & category = ADVP]: TOP;
        # definition ~ [category = ADJP & defined = 'true']: [slot = ADJP2 & function = hd & ! category = none];
        # TOPOLOGY ADJP
        Topology(PH.ADJP, tag=TAG.adjp)
            #  ADJP1 : mod: ADVP
            .add_field(Field(FT.ADJP1, grammatical_funcs=(GramFunc(GF.mod, ph=PH.ADVP),)))
            #  ADJP2!: hd: adj
            .add_field(Field(FT.ADJP2, mod='!', grammatical_funcs=(GramFunc(GF.hd, ph=PH.adj),)))
        # END TOPOLOGY ADJP
        ,

        # Advp
        # definition ~ [category = ADVP & defined = 'true']: [slot = ADVP1 & function = hd & ! category = none];

        Topology(PH.ADVP, tag=TAG.advp)
            .add_field(Field(FT.ADVP1, grammatical_funcs=(
            GramFunc(GF.hd),))),

        # Quantifier
        # definition ~ [category = QP & defined = 'true']: [slot = QP1 & function = hd & ! category = none];

        Topology(PH.QP, tag=TAG.qp)
            .add_field(Field(FT.QP1, grammatical_funcs=(
            GramFunc(GF.hd),))),

        # Determiner
        # definition ~ [category = DP & defined = 'true']: [slot = DP1 & function = hd & ! category = none];

        Topology(PH.DP, tag=TAG.dp)
            .add_field(Field(FT.DP1, grammatical_funcs=(
            GramFunc(GF.hd),))),

        # CP
        # definition ~ [category = CP & defined = 'true']: [slot = CP1 & function = hd & ! category = none];

        Topology(PH.CP, tag=TAG.cp)
            .add_field(Field(FT.CP1, grammatical_funcs=(
            GramFunc(GF.hd), ))),
    )


def process_dominance(tree, topology_rules, parent_tree=None):
    """
    build all possible topologies in consistence to topology_rules for tree
    """
    from nltk import Tree

    node = tree.hclabel()
    for temp_topol in topology_rules:
        # chose a topology for the dominance structure item
        if tree.ph == temp_topol.ph:
            if temp_topol.parent_restriction:

                if not parent_tree or not isinstance(parent_tree, FeatTree):
                    parent_gf_ph = (None, None)
                else :
                    parent_gf_ph = (parent_tree.gf, parent_tree.ph)
                if parent_gf_ph not in temp_topol.parent_restriction:
                    continue

            # unify works correct only with structures of the same type
            # create FeatStructNonterminal from topology features
            if temp_topol.features and len(node) > 1:
                top_fstruct = FeatStructNonterminal(temp_topol.features)
                unif = featstruct.unify(node, top_fstruct)
            else:
                unif = True
            if unif:
                topology = copy.deepcopy(temp_topol)
                # fill topology fields
                dependent_fields = dict()
                child_usages = dict()
                for child in tree:
                    child_usages[child] = 0
                    if isinstance(child, Tree):
                        for field in topology.field_map.values():
                            if field.dependencies:
                                dependent_fields[field.ft] = field
                                continue
                            for func in field.grammatical_funcs:
                                if func.fit(child):
                                    child_usages[child] += 1
                                    # add edge to topology
                                    topology[field.ft] += (child.gorn,)
                                    break

                # fill fields, that should be processed afterwards because the have dependencies
                while dependent_fields:
                    for ft, field in list(dependent_fields.items()):
                        if field.dependencies in dependent_fields:
                            continue
                        del dependent_fields[ft]
                        for child in tree:
                            if isinstance(child, Tree):
                                for func in field.grammatical_funcs:
                                    if func.fit(child):
                                        child_usages[child] += 1
                                        # add edge to topology
                                        topology[ft] += (child.gorn,)
                                        break

                unused_fields = False
                children_without_topologies = False
                for child, usage_number in child_usages.items():
                    if not usage_number:
                        unused_fields = True
                        print("Warning! Node {} doesn't fit in any field of the topoology {}".format(
                            child.short_str_with_features(), topology))
                    elif not child.topologies and not child.ishead():
                        child.topologies.extend(process_dominance(child, topology_rules, parent_tree=tree))
                    if not child.ishead() and not child.topologies:
                        children_without_topologies = True
                        print("Warning! Node {} doesn't have any topoology".format(child.short_str_with_features()))

                if not unused_fields and not children_without_topologies:
                    yield topology


def demo(print_times=True, print_grammar=False,
         print_trees=True, trace=1,
         sent='ich sehe', numparses=0):
    """
     # tokens = "".split()
    er tritt in die Verwaltung ein und er wird Aktionär
    Für die Bürger schafft das die einzige Möglichkeit , zu kontrollieren und nachzuvollzuehen , was die Politik Frage will
    damit die Gesundheit der Arbeiter geschützt und diese von unzumutbaren Belästigungen verschont würden

    ich darf Kaffee trinken - works
    Kaffee darf ich jeden Tag trinken
    Bücher liest Mari und Bücher schreibt Jüri
    Monopole sollen geknackt werden und Märkte sollen getrennt werden
    die Länder legen fest daß die nördlichen Inseln zu Rußland und die südliche Inseln zu Japan gehören sollten

    sent examples:
    Peter wird das Buch finden können
    den Kaffee darf ich an dem Tag trinken
    'der Kurier sollte nachher einem Spion den Brief stecken'
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
    # with open('../../fsa/query.fcfg', "r") as f:
    #     productions = FeatureGrammar.fromstring(f.read(), logic_parser=None,
    #                                             fstruct_reader=fstruct_reader, encoding=None)

    # productions = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/query.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    # cp = FeatureTopDownChartParser(productions, use_agenda=True, trace=trace)
    cp = FeatureTopDownChartParser(build_rules(tokens, fstruct_reader), use_agenda=True, trace=trace)

    dominance_structures = []
    count_trees = 0
    # for tokens_variation in set(itertools.permutations(tokens)):

    verifier = wordPresenceVerifier(tokens)
    for tree in cp.parse(tokens):
        count_trees += 1
        if verifier(tree):
            try:
                dominance_structures.append(tree)
            except ValueError:
                pass
        # has_subj = False
        # for sub_tree in tree:
        #     if sub_tree._label[TYPE] == 'subj':
        #         has_subj = True
        #         break
        # if ver_result and has_subj and tree._label.has_feature({'status': 'Fin'}):
        #     try:
        #         dominance_structures.append(tree)
        #     except ValueError:
        #         pass
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
