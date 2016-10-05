import copy



from nltk.featstruct import CelexFeatStructReader, unify, TYPE, EXPRESSION, _unify_feature_values
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar
from nltk.topology.FeatTree import minimize_nonterm, open_disjunction, simplify_expression, GF, STATUS
from nltk.topology.compassFeat import GRAM_FUNC_FEATURE, LEMMA_FEATURE, PRODUCTION_ID_FEATURE, BRANCH_FEATURE, \
    INHERITED_FEATURE, SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE, STATUS_FEATURE

__author__ = 'Denis Krusko: kruskod@gmail.com'

import mysql.connector
from mysql.connector import errorcode


def connect():
    try:
        # cnx = mysql.connector.connect(host="localhost", port=3306, user='root', password='total', database='pgc', use_unicode = True, charset='utf8', collation='utf8_bin')
        cnx = mysql.connector.connect(unix_socket="/var/run/mysqld/mysqld.sock", database='pgc', password='total', user='root', use_unicode = True, charset='utf8', collation='utf8_bin')
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

        query = (
        ' select pos, i.feature as formFeature, c.feature as categoryFeature, l.lemma, f.lexFrameKey, w.word from WordForm w' +
        ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey' +
        ' inner join Lemma l on l.lemmaId = w.lemmaId' +
        ' inner join WordFrame f on f.lemmaId = w.lemmaId' +
        ' inner join WordCategory c on c.lexFrameKey = f.lexFrameKey' +
        ' where w.word=%s;')

        for token in tokens:
            cursor.execute(query, (token,))
            productions.extend(productions_extractor(cnx, cursor, fstruct_reader))

        productions.append(Production(FeatStructNonterminal("S[]"), (
            FeatStructNonterminal("S[]"), FeatStructNonterminal("XP[]"), FeatStructNonterminal("S[]"),)))

        if dump:
            with open('../../fsa/query.fcfg', "w") as f:
                for rule in productions:
                    f.write(repr(rule) + '\n\n')
        cursor.close()
        cnx.close()
    return FeatureGrammar(FeatStructNonterminal("S[status='Fin']"),  productions)


def productions_extractor(cnx, cursor, fstruct_reader):
    productions = set()

    frameCursor = cnx.cursor(buffered=True)
    unificationCursor = cnx.cursor(buffered=True)

    frameQuery = ('select w.position, pos1,pos2,pos3,feature, w.facultative from WordCategorySegment w' +
                  ' inner join Segment s on s.position = w.position' +
                  ' left join PartOfSpeech p on p.pos = s.pos3' +
                  ' where w.lexFrameKey = %s  and pos2 !="mod" ' +
                  ' order by w.facultative, w.position;')

    unificationQuery = ('select cond, feature from UnificationFeatures u where u.position = %s;')

    for (pos, formFeature, categoryFeature, lemma, lexFrameKey, word) in cursor:
        word = word.decode('utf8')
        nt = formNT = catNT = None
        if formFeature:
            formNT = fstruct_reader.fromstring(formFeature)
            formNT = formNT.filter_feature(SLOT_FEATURE, )  # , PERSONAL_FEATURE
            formNT[TYPE] = pos
            nt = formNT

        if categoryFeature:
            catNT = fstruct_reader.fromstring(categoryFeature)
            catNT = catNT.filter_feature(SLOT_FEATURE, )  # PERSONAL_FEATURE
            catNT[TYPE] = pos
            nt = catNT

        if formNT and catNT:
            nt = unify(formNT, catNT)

        if nt:
            nt.add_feature({LEMMA_FEATURE: lemma})
            nt[TYPE] = pos
        else:
            nt = fstruct_reader.fromstring(pos)

        # nt = minimize_nonterm(nt)
        frameCursor.execute(frameQuery, (lexFrameKey,))
        gf = set()
        rhs = []
        # hd = (None, None)
        # personal = nt.get_feature(PERSONAL_FEATURE)
        # if personal:
        #     if not isinstance(personal, bool):
        #         personal = personal[0]
        #
        #     if personal:    # weak status rule, discuss with the expert
        #         status = nt.get_feature(STATUS_FEATURE)
        #         if isinstance(status, str):
        #             status = (status,)
        #         if STATUS.Infin.name in status:
        #             personal = False

        for (position, pos1, pos2, pos3, feature, facultative) in frameCursor:
            pos2NT = FeatStructNonterminal(pos2)

            pos2NT.add_feature({PRODUCTION_ID_FEATURE: lexFrameKey})
            # pos2NT[TYPE] = pos2
            pos3NT = FeatStructNonterminal(pos3)

            # After this point inherited features will be added
            unificationCursor.execute(unificationQuery, (position,))
            for (cond, un_feature) in unificationCursor:
                if cond:
                    condNT = fstruct_reader.fromstring('[' + cond + ']')
                    if not unify(nt, condNT):
                        continue
                unNT = fstruct_reader.fromstring(un_feature)
                # It is actually not unification, but features merging
                un_pos3NT = unify(pos3NT, unNT)
                pos3NT = un_pos3NT  # .filter_feature(SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE)

                pos2NT = unify(pos2NT, unNT)
                pos2NT = pos2NT  # .filter_feature(SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE)

            if facultative:
                if pos2NT.has_feature({BRANCH_FEATURE: 'obligatory'}):
                    pos2NT = pos2NT.filter_feature(BRANCH_FEATURE)
                else:
                    if pos2 == 'subj':
                        status = nt.get_feature(STATUS_FEATURE)
                        if status:
                            if isinstance(status, str):
                                status = (status,)
                            if STATUS.Infin.name not in status:
                                facultative = False

                    if facultative:
                        pos2NT.add_feature({BRANCH_FEATURE: 'facultative',})

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
                    keys = tuple(keys)
                    pos2NT.add_feature({INHERITED_FEATURE: keys})
                    pos3NT.add_feature({PRODUCTION_ID_FEATURE: lexFrameKey, INHERITED_FEATURE: keys})

                rhs.append(pos2NT)
            # simplify disjunction to separate rules
            # map(process_inherited_features,openDisjunction(Production(pos2NT, pos3NT)))
            productions.update(map(lambda production: production.process_inherited_features(),
                                          open_disjunction(Production(pos2NT, (pos3NT,)))))
        # simplify lhs here
        lhs = copy.deepcopy(nt)  # .filter_feature(SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE)
        lhs[TYPE] = pos1
        nt.add_feature({PRODUCTION_ID_FEATURE: lexFrameKey})
        productions.update(open_disjunction(Production(nt, (word,))))
        # productions.append(Production(nt, (word,)))
        productions.update(
            map(lambda production: production.process_inherited_features(), open_disjunction(Production(lhs, rhs))))

    unificationCursor.close()
    frameCursor.close()
    return productions

def wordforms_extractor(cnx, cursor, fstruct_reader):
    productions = set()

    for (pos, formFeature, categoryFeature, lemma, lexFrameKey, word) in cursor:
        word = word.decode('utf8')
        nt = None
        if formFeature:
            formNT = fstruct_reader.fromstring(formFeature)
            formNT = formNT.filter_feature(SLOT_FEATURE, )  # , PERSONAL_FEATURE
            nt = formNT

        if not nt:
            nt = fstruct_reader.fromstring(pos)

        lhs = nt  # .filter_feature(SLOT_FEATURE, PERSONAL_FEATURE, INFLECTED_FEATURE)
        lhs[TYPE] = pos
        nt.add_feature({PRODUCTION_ID_FEATURE: lexFrameKey,LEMMA_FEATURE: lemma})
        productions.update(open_disjunction(Production(nt, (word,))))

    return productions

def build_wordform_productions(lemma, lexFrameKey, fstruct_reader):
    cnx = connect()
    productions = []
    if cnx:
        cursor = cnx.cursor(buffered = True)

        query = (
            ' select pos, i.feature as formFeature, c.feature as categoryFeature, l.lemma, f.lexFrameKey, w.word ' +
            ' from Lemma l inner join WordForm w on w.lemmaId =l.lemmaId ' +
            ' inner join WordFrame f on f.lemmaId = w.lemmaId ' +
            ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey' +
            ' inner join WordCategory c on c.lexFrameKey = f.lexFrameKey ' +
            ' where l.lemma=%s and f.lexFrameKey=%s;')

        cursor.execute(query, (lemma, lexFrameKey))
        query_results = cursor.fetchall()
        productions = wordforms_extractor(cnx, query_results, fstruct_reader)
        word_forms = set()
        for (pos, formFeature, categoryFeature, lemma, lexFrameKey, word) in query_results:
            word_forms.add(word.decode("utf-8"))
        cnx.close()

    return word_forms, productions


def build_productions(lemma, lexFrameKey, fstruct_reader):
    cnx = connect()
    productions = []
    if cnx:
        cursor = cnx.cursor(buffered = True)

        query = (
            ' select pos, i.feature as formFeature, c.feature as categoryFeature, l.lemma, f.lexFrameKey, w.word ' +
            ' from Lemma l inner join WordForm w on w.lemmaId =l.lemmaId ' +
            ' inner join WordFrame f on f.lemmaId = w.lemmaId ' +
            ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey' +
            ' inner join WordCategory c on c.lexFrameKey = f.lexFrameKey ' +
            ' where l.lemma=%s and f.lexFrameKey=%s;')

        cursor.execute(query, (lemma, lexFrameKey))
        query_results = cursor.fetchall()
        productions = productions_extractor(cnx, query_results, fstruct_reader)
        word_forms = set()
        for (pos, formFeature, categoryFeature, lemma, lexFrameKey, word) in query_results:
            word_forms.add(word.decode("utf-8"))
        cnx.close()

    return word_forms, productions

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

def get_word_inf(word):
    cnx = connect()
    if cnx:
        cursor = cnx.cursor()

        query = (
        'SELECT '
        ' l.lemmaId as Lemma_Id, '
        ' f.lexFrameKey as WordFrame_lexFrameKey, '
        ' l.lemma as Lemma_lemma, '
        ' w.word as WordForm_word, w.pronuncation as WordForm_pronuncation, '
        ' c.pos as WordCategory_pos, c.feature as WordCategory_feature,	c.description as WordCategory_description, c.example as WordCategory_example,	'
        ' i.feature as InflectionalForm_feature, i.description as InflectionalForm_description, '
        ' p.feature as PartOfSpeech_feature,    p.description as PartOfSpeech_description,	p.example as PartOfSpeech_example'
        ' FROM    WordForm w'
        '   inner join    WordFrame f ON w.lemmaId = f.lemmaId'
        '   inner join    WordCategory c ON c.lexFrameKey = f.lexFrameKey'
        '   inner join    InflectionalForm i ON i.inflFormKey = w.inflFormKey'
        '   inner join    PartOfSpeech p ON p.pos = c.pos'
        '   inner join    Lemma l ON l.lemmaId = w.lemmaId'
        ' where w.word =%s order by LENGTH(f.lexFrameKey), f.lexFrameKey;')

        cursor.execute(query, (word,))
        cnx.close()
        return form_frames(cursor)

def get_frame_segments(lexFrameKey):
    cnx = connect()
    if cnx:
        cursor = cnx.cursor()
        query = (
            'select '
            ' w.lexFrameKey as WordCategorySegment_lexFrameKey,'
            ' w.position as WordCategorySegment_position,'
            ' w.facultative as WordCategorySegment_facultative,'
            ' s.pos1 as Segment_pos1,'
            ' s.pos2 as Segment_pos2,'
            ' s.pos3 as Segment_pos2,'
            ' s.example as Segment_example,'
            ' u.cond as UnificationFeatures_condition,'
            ' u.feature as UnificationFeatures_feature,'
            ' u.example as UnificationFeatures_example'
        ' from WordCategorySegment w'
        ' inner join Segment s on s.position = w.position'
        ' left join UnificationFeatures u on u.position = w.position'
        ' where w.lexFrameKey=%s'
        ' order by w.facultative, w.position;')

        cursor.execute(query, (lexFrameKey,))
        cnx.close()
        return form_frames(cursor)

def get_frame_features(lexFrameKey):
    cnx = connect()
    if cnx:
        cursor = cnx.cursor()

        query = (
            ' select'
            ' c.lexFrameKey as WordCategory_lexFrameKey,'
            ' c.lexFrame as WordCategory_lexFrame,'
            ' c.pos as WordCategory_pos,'
            ' c.description as WordCategory_description,'
            ' c.feature as WordCategory_feature,'
            ' c.example as WordCategory_example,'
            ' p.description as PartOfSpeech_description,'
            ' p.feature as PartOfSpeech_feature,'
            ' p.example as PartOfSpeech_example'
        ' from WordCategory c'
        ' inner join PartOfSpeech p ON p.pos = c.pos where c.lexFrameKey=%s')

        cursor.execute(query, (lexFrameKey,))
        cnx.close()
        return form_frames(cursor)

def get_frame_examples(lexFrameKey):
    cnx = connect()
    if cnx:
        cursor = cnx.cursor()

        query = (
             ' select f.lemmaId as WordFrame_lemmaId,'
             ' f.lexFrameKey as WordFrame_lexFrameKey,'
             ' f.inflParadigmKey as WordFrame_inflParadigmKey,'
             ' l.lemma as Lemma_lemma,'
             ' w.word as WordForm_word,'
             ' w.pronuncation as WordForm_pronuncation,'
             ' w.inflFormKey as WordForm_inflFormKey,'
             ' i.description as InflectionalForm_description,'
             ' i.feature as InflectionalForm_feature'
             ' from WordFrame f'
             ' inner join Lemma l on l.lemmaId = f.lemmaId'
             ' inner join WordForm w on f.lemmaId = w.lemmaId'
             ' inner join InflectionalForm i on i.inflFormKey = w.inflFormKey'
             ' where f.lexFrameKey =%s order by l.lemma, w.word limit 1000;')

        cursor.execute(query, (lexFrameKey,))
        cnx.close()
        return form_frames(cursor)

def form_frames(cursor):
    frames = []
    if cursor:
        frames.append(('',) + cursor.column_names)
        for rule in cursor:
            frames.append(tuple(
                item if isinstance(item, (str, int)) else '' if not item else item.decode("utf-8") for item in
                rule))
        cursor.close()
    return frames


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
    # fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    # print(build_rules('Kurier'.split(), fstruct_reader))
    frames = get_word_inf('werden')
    print(frames)
