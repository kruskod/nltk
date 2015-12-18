import copy

from nltk.featstruct import CelexFeatStructReader, unify, TYPE, EXPRESSION, _unify_feature_values
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar
from nltk.topology.FeatTree import minimize_nonterm, open_disjunction, simplify_expression
from nltk.topology.compassFeat import GRAM_FUNC_FEATURE, LEMMA_FEATURE, PRODUCTION_ID_FEATURE, BRANCH_FEATURE, \
    INHERITED_FEATURE, SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE

__author__ = 'Denis Krusko: kruskod@gmail.com'

import mysql.connector
from mysql.connector import errorcode


def connect():
    try:
        cnx = mysql.connector.connect(host="localhost", port=3306, user='root', password='total', database='pgc', use_unicode = True, charset='utf8', collation='utf8_bin')
        # cnx = mysql.connector.connect(unix_socket="", database='pgc', use_unicode = True, charset='utf8', collation='utf8_bin')
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:
        return cnx

def build_rules(tokens, fstruct_reader, dump = True):
    cnx = connect()
    productions = []
    if cnx:
        cursor = cnx.cursor(buffered = True)
        frameCursor = cnx.cursor(buffered = True)
        unificationCursor = cnx.cursor(buffered = True)
        query = (
        ' select pos, i.feature as formFeature, c.feature as categoryFeature, l.feature, l.lemma, f.lexFrameKey, w.word from WordForm w' +
        ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey' +
        ' inner join Lemma l on l.lemmaId = w.lemmaId' +
        ' inner join WordFrame f on f.lemmaId = w.lemmaId' +
        ' inner join WordCategory c on c.lexFrameKey = f.lexFrameKey' +
        ' where w.word=%s;')

        frameQuery = ( 'select w.position, pos1,pos2,pos3,feature, w.facultative from WordCategorySegment w' +
        ' inner join Segment s on s.position = w.position' +
        ' left join PartOfSpeech p on p.pos = s.pos3' +
        ' where w.lexFrameKey = %s ' + #  and pos2 !="mod"
        ' order by w.facultative, w.position;')

        unificationQuery = ('select cond, feature from UnificationFeatures u where u.position = %s;')

        # lhs = minimize_nonterm(prod.lhs())
        # select_extensions = [ext for ext in extensions if ext['lhs'] == lhs[TYPE]]
        # rhs = list(prod.rhs())
        # for i, nt in enumerate(rhs):
        #     for ext in select_extensions:
        #         if ext['rhs'] == nt[TYPE] and nt.has_feature({GRAM_FUNC_FEATURE:ext[GRAM_FUNC_FEATURE]}):
        #             if 'cond' in ext:
        #                 feat = fstruct_reader.fromstring('[' + ext['cond'] + ']')

        for token in tokens:
            cursor.execute(query, (token,))
            for (pos, formFeature, categoryFeature, lemmaFeature, lemma, lexFrameKey, word) in cursor:
                word = word.decode('utf8')
                if formFeature:
                    formNT = minimize_nonterm(fstruct_reader.fromstring(formFeature))
                    # formNT = formNT.filter_feature("personal", "inflected")
                    formNT[TYPE] = pos
                    nt = formNT
                else:
                    formNT = None
                if categoryFeature:
                    catNT = minimize_nonterm(fstruct_reader.fromstring(categoryFeature))
                    catNT = catNT.filter_feature("personal")
                    catNT[TYPE] = pos
                    nt = catNT
                else:
                    catNT = None
                if formNT and catNT:
                    nt = unify(formNT, catNT, treatBool=False)
                if lemmaFeature:
                    nt = unify(nt, minimize_nonterm(fstruct_reader.fromstring(lemmaFeature)))
                nt.add_feature({LEMMA_FEATURE:lemma})
                nt[TYPE] = pos
                nt = minimize_nonterm(nt)
                frameCursor.execute(frameQuery, (lexFrameKey,))
                gf = set()
                rhs = []
                #hd = (None, None)
                for (position, pos1, pos2, pos3, feature, facultative) in frameCursor:
                    pos2NT = FeatStructNonterminal(pos2)
                    if facultative:
                        pos2NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey, BRANCH_FEATURE:'facultative'})
                    else:
                        pos2NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey})
                    # pos2NT[TYPE] = pos2
                    pos3NT = FeatStructNonterminal(pos3)

                    #After this point inherited features will be added
                    unificationCursor.execute(unificationQuery, (position,))
                    for (cond, un_feature) in unificationCursor:
                        if cond:
                            condNT = fstruct_reader.fromstring('[' + cond + ']')
                            if not unify(nt, condNT):
                                continue
                        unNT = fstruct_reader.fromstring(un_feature)
                        # It is actually not unification, but features merging
                        un_pos3NT = unify(pos3NT, unNT, treatBool=False)
                        pos3NT = un_pos3NT.filter_feature(SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE)

                        pos2NT = unify(pos2NT, unNT, treatBool=False)
                        pos2NT = pos2NT.filter_feature(SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE)

                    if pos2 not in gf:
                        gf.add(pos2)
                        if pos2 == 'hd':
                            if feature:
                                headNT = fstruct_reader.fromstring(feature)
                                nt = unify(nt, headNT)

                            keys = set(nt.keys())
                            keys.remove(TYPE)

                            if EXPRESSION in nt:
                                keys.remove(EXPRESSION)
                                for exp in simplify_expression(nt[EXPRESSION]):
                                    keys.update(exp.keys())
                            keys=tuple(keys)
                            pos2NT.add_feature({INHERITED_FEATURE:keys})
                            pos3NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey,INHERITED_FEATURE:keys})

                        rhs.append(pos2NT)
                    # simplify disjunction to separate rules
                    #map(process_inherited_features,openDisjunction(Production(pos2NT, pos3NT)))
                    productions.extend(sorted(map(lambda production: production.process_inherited_features(), open_disjunction(Production(pos2NT, (pos3NT,))))))
                # simplify lhs here
                lhs = copy.deepcopy(nt)
                lhs[TYPE] = pos1
                nt.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey})
                productions.extend(open_disjunction(Production(nt, (word,))))
                # productions.append(Production(nt, (word,)))
                productions.extend(sorted(map(lambda production: production.process_inherited_features(), open_disjunction(Production(lhs, rhs)))))
                # Add productions simplifier
        # simplified_prodiuctions = list()
        # for production in productions:
        #     simplified_prodiuctions.extend([production.simplify()])
        # productions = simplified_prodiuctions

                # productions.append(Production(lhs, rhs).process_inherited_features())
        if dump:
            with open('../../fsa/query.fcfg', "w") as f:
                for rule in productions:
                    f.write(repr(rule) + '\n\n')
        unificationCursor.close()
        cursor.close()
        frameCursor.close()
        cnx.close()
    return FeatureGrammar(FeatStructNonterminal('S'), productions)


def get_rules(tokens, dump=True):
    cnx = connect()
    rules = ['% start S',]
    if cnx:
        cursor = cnx.cursor()
        query = (
        'select CONCAT(t.rule, " |- ", t.lexFrameKey, "\n", t.lexFrameKey, f.feature, " -> \'", w.form, "\'") from WordForms w inner join Lemma l on l.lemmaKey = w.lemmaKey ' +
        ' inner join LexFootFeatures f on f.infFormKey = w.infFormKey ' +
        ' inner join Lemma2Frame fr on fr.lemmaKey = w.lemmaKey ' +
        ' inner join LexFrameTrees t on t.lexFrameKey = fr.lexFrameKey ' +
        ' where w.form=%s;')

        for token in tokens:
            cursor.execute(query, (token,))

            for (rule,) in cursor:
                rule_str = rule.decode("utf-8")
                rules.extend(rule_str.split('\n'))

        rules = sorted(rules)
        if dump:
            with open('../../fsa/query.fcfg', "w") as f:
                f.write('\n'.join(rules))

        cursor.close()
        cnx.close()
    return rules

def get_frame_extensions(dump = True):
    cnx = connect()
    extensions = []
    if cnx:
        cursor = cnx.cursor()
        query = ('select CONCAT(position, ";", COALESCE(cond,""), ";", features, ";", example) from LexFrameExtensions;')
        cursor.execute(query)
        for (line,) in cursor:
            extensions.append(line)
        if dump:
            with open('../../fsa/extensions.csv', "w") as f:
                f.write('\n'.join(extensions))
        cursor.close()
        cnx.close()
    return extensions

def read_extensions():
    extensions = []
    with open('../../fsa/extensions.csv', "r") as file:
        for line in file:
            columns = line.split(';')
            if columns:
                ext = {}
                lhs,gf,rhs = columns[0].split('_')
                ext[GRAM_FUNC_FEATURE] = gf
                ext['lhs'] = lhs
                ext['rhs'] = rhs
                if len(columns[1].strip()):
                    ext['cond'] = columns[1]
                ext['feat'] = columns[2]
                if len(columns[3].strip()):
                    ext['example'] = columns[3]
                extensions.append(ext)
    return extensions

def compass_export():
    cnx = connect()
    productions = []
    if cnx:
        cursor = cnx.cursor(buffered = True)
        frameCursor = cnx.cursor(buffered = True)
        unificationCursor = cnx.cursor(buffered = True)

        # hier ist die Bespiel-Wortform “flog”, fuer die es zwei Baume gibt:
        # flog : (S (cmpr CP[branch=facultative]) (mod /S[branch=facultative]/NP[case=gen/dat/acc|branch=facultative]/PP[particle=false|branch=facultative]/ADVP[branch=facultative]/) (subj /NP[status=Fin|case=nom|inheritedFeature=number/person/wh|branch=facultative]/S[status=Fin|number=singular|person=3rd|inheritedFeature=wh|branch=facultative]/) (hd v[branch=obligatory|lemma=fliegen intrans.|lemmaNo=13986|perf_aux=haben/sein|personal=true|sepPrefix=none|vcat=VS|inflForm=26|inflPara=25|{[mood=indicative|number=singular|person=1st|status=Fin|tense=past] OR [mood=indicative|number=singular|person=3rd|status=Fin|tense=past]}]))
        # flog : (S (mod /ADVP[branch=facultative]/S[branch=facultative]/NP[case=gen/dat/acc|branch=facultative]/PP[particle=false|branch=facultative]/) (subj /NP[status=Fin|case=nom|inheritedFeature=number/person/wh|branch=facultative]/S[status=Fin|number=singular|person=3rd|inheritedFeature=wh|branch=facultative]/) (dobj NP[case=acc|branch=obligatory]) (cmpr CP[branch=facultative]) (hd v[branch=obligatory|lemma=fliegen oblig. trans.|lemmaNo=13988|perf_aux=haben/sein|personal=true|sepPrefix=none|vcat=VS|inflForm=26|inflPara=25|{[mood=indicative|number=singular|person=1st|status=Fin|tense=past] OR [mood=indicative|number=singular|person=3rd|status=Fin|tense=past]}]))

        query = (
        ' select pos, i.feature as formFeature, c.feature as categoryFeature, l.feature, l.lemma, f.lexFrameKey, w.word from WordForm w' +
        ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey' +
        ' inner join Lemma l on l.lemmaId = w.lemmaId' +
        ' inner join WordFrame f on f.lemmaId = w.lemmaId' +
        ' inner join WordCategory c on c.lexFrameKey = f.lexFrameKey' +
        ' where w.word=%s;')

        frameQuery = ( 'select w.position, pos1,pos2,pos3,feature, w.facultative from WordCategorySegment w' +
        ' inner join Segment s on s.position = w.position' +
        ' left join PartOfSpeech p on p.pos = s.pos3' +
        ' where w.lexFrameKey = %s ' + #  and pos2 !="mod"
        ' order by w.facultative, w.position;')

        unificationQuery = ('select cond, feature from UnificationFeatures u where u.position = %s;')

        # lhs = minimize_nonterm(prod.lhs())
        # select_extensions = [ext for ext in extensions if ext['lhs'] == lhs[TYPE]]
        # rhs = list(prod.rhs())
        # for i, nt in enumerate(rhs):
        #     for ext in select_extensions:
        #         if ext['rhs'] == nt[TYPE] and nt.has_feature({GRAM_FUNC_FEATURE:ext[GRAM_FUNC_FEATURE]}):
        #             if 'cond' in ext:
        #                 feat = fstruct_reader.fromstring('[' + ext['cond'] + ']')

        for token in tokens:
            cursor.execute(query, (token,))
            for (pos, formFeature, categoryFeature, lemmaFeature, lemma, lexFrameKey, word) in cursor:
                word = word.decode('utf8')
                if formFeature:
                    formNT = minimize_nonterm(fstruct_reader.fromstring(formFeature))
                    formNT[TYPE] = pos
                    nt = formNT
                else:
                    formNT = None
                if categoryFeature:
                    catNT = minimize_nonterm(fstruct_reader.fromstring(categoryFeature))
                    catNT[TYPE] = pos
                    nt = catNT
                else:
                    catNT = None
                if formNT and catNT:
                    nt = unify(formNT, catNT)
                if lemmaFeature:
                    nt = unify(nt, minimize_nonterm(fstruct_reader.fromstring(lemmaFeature)))
                nt.add_feature({LEMMA_FEATURE:lemma})
                nt[TYPE] = pos
                nt = minimize_nonterm(nt)
                frameCursor.execute(frameQuery, (lexFrameKey,))
                gf = set()
                rhs = []
                #hd = (None, None)
                for (position, pos1, pos2, pos3, feature, facultative) in frameCursor:
                    pos2NT = FeatStructNonterminal(pos2)
                    if facultative:
                        pos2NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey, BRANCH_FEATURE:'facultative'})
                    else:
                        pos2NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey})
                    # pos2NT[TYPE] = pos2
                    pos3NT = FeatStructNonterminal(pos3)

                    unificationCursor.execute(unificationQuery, (position,))
                    for (cond, un_feature) in unificationCursor:
                        if cond:
                            condNT = fstruct_reader.fromstring('[' + cond + ']')
                            if not unify(nt, condNT):
                                continue
                        unNT = fstruct_reader.fromstring(un_feature)
                        un_pos3NT = unify(pos3NT, unNT)
                        pos3NT = un_pos3NT
                        if pos3NT.get_feature(SLOT_FEATURE):
                            pos3NT.filter_feature(SLOT_FEATURE)
                        pos2NT = unify(pos2NT, unNT)
                        if pos2NT.get_feature(SLOT_FEATURE):
                            pos2NT.filter_feature(SLOT_FEATURE)

                    if pos2 not in gf:
                        gf.add(pos2)
                        if pos2 == 'hd':
                            if feature:
                                headNT = fstruct_reader.fromstring(feature)
                                nt = unify(nt, headNT)
                            # don't generate head features
                            #continue
                            # nt_copy = copy.deepcopy(nt)
                            # del nt_copy[TYPE]
                            # pos2NT = unify(pos2NT, nt_copy)
                            # pos3NT = unify(pos3NT, nt_copy)
                            # # number_var = Variable('?' + NUMBER_FEATURE)
                            # person_var = Variable('?' + NUMBER_FEATURE)
                            # if not pos2NT.get_feature(NUMBER_FEATURE):
                            #     pos2NT.add_feature({NUMBER_FEATURE:number_var})
                            # if not pos3NT.get_feature(NUMBER_FEATURE):
                            #     pos3NT.add_feature({NUMBER_FEATURE:number_var})
                            # if not pos2NT.get_feature(PERSON_FEATURE):
                            #     pos2NT.add_feature({PERSON_FEATURE:person_var})
                            # if not pos3NT.get_feature(PERSON_FEATURE):
                            #     pos3NT.add_feature({PERSON_FEATURE:person_var})
                            #hd = pos2NT, pos3NT
                            keys = set(nt.keys())
                            keys.remove(TYPE)

                            if EXPRESSION in nt:
                                keys.remove(EXPRESSION)
                                for exp in simplify_expression(nt[EXPRESSION]):
                                    keys.update(exp.keys())
                            keys=tuple(keys)
                            pos2NT.add_feature({INHERITED_FEATURE:keys})
                            pos3NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey,INHERITED_FEATURE:keys})
                        rhs.append(pos2NT)
                    # simplify disjunction to separate rules
                    #map(process_inherited_features,openDisjunction(Production(pos2NT, pos3NT)))
                    productions.extend(sorted(map(lambda production: production.process_inherited_features(), open_disjunction(Production(pos2NT, (pos3NT,))))))
                lhs = copy.deepcopy(nt)
                lhs[TYPE] = pos1
                nt.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey})
                productions.extend(open_disjunction(Production(nt, (word,))))
                # productions.append(Production(nt, (word,)))
                productions.extend(sorted(map(lambda production: production.process_inherited_features(), open_disjunction(Production(lhs, rhs)))))
                # productions.append(Production(lhs, rhs).process_inherited_features())
        if dump:
            with open('../../fsa/query.fcfg', "w") as f:
                for rule in productions:
                    f.write(repr(rule) + '\n\n')
        unificationCursor.close()
        cursor.close()
        frameCursor.close()
        cnx.close()
    return FeatureGrammar(FeatStructNonterminal('S'), productions)

if __name__ == "__main__":
    # get_rules('Monopole sollen geknackt werden'.split())
    # get_frame_extensions()
    # print(read_extensions())
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    build_rules('ich sehe'.split(), fstruct_reader)
