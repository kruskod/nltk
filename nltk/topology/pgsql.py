import copy
from nltk.featstruct import CelexFeatStructReader, unify, TYPE
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar
from nltk.topology.FeatTree import minimize_nonterm
from nltk.topology.compassFeat import GRAM_FUNC_FEATURE, LEMMA_FEATURE, PRODUCTION_ID_FEATURE, BRANCH_FEATURE

__author__ = 'Denis Krusko: kruskod@gmail.com'

import mysql.connector
from mysql.connector import errorcode


def connect():
    try:
        cnx = mysql.connector.connect(host="localhost", port=3307, user='root', database='pgc', use_unicode = True, charset='utf8')
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
        ' select pos, i.feature as formFeature, c.feature as categoryFeature, l.lemma, f.lexFrameKey, w.word from WordForm w' +
        ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey' +
        ' inner join Lemma l on l.lemmaId = w.lemmaId' +
        ' inner join WordFrame f on f.lemmaId = w.lemmaId' +
        ' inner join WordCategory c on c.lexFrameKey = f.lexFrameKey' +
        ' where w.word=%s;')

        frameQuery = ( 'select w.position, pos1,pos2,pos3,feature, w.facultative from WordCategorySegment w' +
        ' inner join Segment s on s.position = w.position' +
        ' left join PartOfSpeech p on p.pos = s.pos3' +
        ' where w.lexFrameKey = %s and pos2 !="mod" ' +
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
            for (pos, formFeature, categoryFeature, lemma, lexFrameKey, word) in cursor:
                if formFeature:
                    formNT = minimize_nonterm(fstruct_reader.fromstring(formFeature))
                    formNT[TYPE] = pos
                    nt = formNT
                if categoryFeature:
                    catNT = minimize_nonterm(fstruct_reader.fromstring(categoryFeature))
                    catNT[TYPE] = pos
                    nt = catNT
                if formNT and catNT:
                    nt = unify(formNT, catNT)
                nt.add_feature({LEMMA_FEATURE:lemma})
                nt[TYPE] = pos
                nt = minimize_nonterm(nt)
                frameCursor.execute(frameQuery, (lexFrameKey,))
                gf = set()
                rhs = []
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
                        pos3NT = unify(pos3NT, unNT)
                        pos2NT = unify(pos2NT, unNT)

                    if pos2 not in gf:
                        gf.add(pos2)
                        if pos2 == 'hd':
                            if feature:
                                headNT = fstruct_reader.fromstring(feature)
                                nt = unify(nt, headNT)
                            nt_copy = copy.deepcopy(nt)
                            del nt_copy[TYPE]
                            #pos2NT = unify(pos2NT, nt_copy)
                            #pos3NT = unify(pos3NT, nt_copy)
                            pos3NT.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey})
                        rhs.append(pos2NT)

                    productions.append(Production(copy.deepcopy(pos2NT), (copy.deepcopy(pos3NT),))) # .process_inherited_features()
                lhs = copy.deepcopy(nt)
                lhs[TYPE] = pos1
                productions.append(Production(lhs, rhs).process_inherited_features()) #
                nt.add_feature({PRODUCTION_ID_FEATURE:lexFrameKey})
                productions.append(Production(nt, (word,)))

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

if __name__ == "__main__":
    # get_rules('Monopole sollen geknackt werden'.split())
    # get_frame_extensions()
    # print(read_extensions())
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    build_rules('Monopole sollen geknackt werden'.split(), fstruct_reader)
