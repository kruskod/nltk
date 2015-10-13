from nltk.topology.compassFeat import GRAM_FUNC_FEATURE

__author__ = 'Denis Krusko: kruskod@gmail.com'

import mysql.connector
from mysql.connector import errorcode


def connect():
    try:
        cnx = mysql.connector.connect(host="localhost", port=3307, user='root', database='pg')
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:
        return cnx


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
    get_rules('Monopole sollen geknackt werden'.split())
    get_frame_extensions()
    print(read_extensions())
