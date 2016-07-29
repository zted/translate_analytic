#!/usr/bin/env python

import logging

from concrete import Token, TokenLattice, \
    Arc, LatticePath
from concrete.services import Annotator
from thrift.protocol import TCompactProtocol
from thrift.server import TNonblockingServer
from thrift.transport import TSocket


class Translation:
    def __init__(self, text, score):
        self.text = text
        self.score = score

    def getText(self):
        return self.text

    def getScore(self):
        return self.score


class Word:
    def __init__(self, s):
        self.name = s
        self.translations = []

    def getName(self):
        return self.name

    def getTranslations(self):
        return self.translations

    def addTranslation(self, target, score):
        self.translations.append(Translation(target, score))
        return

    def sortTranslations(self):
        # sort by score
        self.translations = sorted(self.translations, key=lambda t: t.getScore(), reverse=True)
        return


def initialize_translations(filename):
    """
    creates a dictionary for words and their possible translations. the expected
    format of the data in the file is to be "candidate_translation original_word score"
    separated by spaces
    :param filename: file containing translations
    :return: dictionary with key being string of the word and value being word object
    """
    with open(filename, 'r') as f:
        someDict = {}
        for (ln, line) in enumerate(f):
            splits = line.rstrip('\n').split(' ')
            src = splits[1]
            target = splits[0]
            score = float(splits[2])
            try:
                myWord = someDict[src]
            except KeyError:
                # we haven't seen this word before, create new entry in dict
                myWord = Word(src)
                someDict[src] = myWord
            myWord.addTranslation(target, score)
    for word in someDict.values():
        # once the entire dictionary is loaded, sort all translations from best to worst
        word.sortTranslations()
    return someDict


def translate(srcWord, wordDict, topK):
    """
    returns topK Translations for a word in a list
    :param srcWord: string that you want to translate
    :param wordDict: dictionary that stores the Word objects
    :param topK: maximum number of translations you want
    :return: Translations in a list
    """
    try:
        srcWordObj = wordDict[srcWord]
        translatedWord = srcWordObj.getTranslations()[0:topK]
        # grabs the best translation available
    except KeyError:
        # no translation available, use original word
        translatedWord = [Translation(srcWord, 1)]
    return translatedWord


class CommunicationHandler:
    def __init__(self):
        self.wordDict = {}

    def parseTranslations(self, filename):
        self.wordDict = initialize_translations(filename)

    def annotate(self, communication):
        """
        WARNING: if there is already a TokenLattice, this method will overwrite it!

        takes in a communication in the source language that is tokenized,
        returns the same communication with an additional tokenization
        :param communication:
        :return: the same communication with addition of tokenlattice
        """
        k = 3
        for section in communication.sectionList:
            for sentence in section.sentenceList:
                assert sentence.tokenization is not None
                arcs = []
                latpath = LatticePath(weight=None, tokenList=[])
                # we want to cache best path to make unpacking easier downstream

                for (n, token) in enumerate(sentence.tokenization.tokenList.tokenList):
                    src = token.text.lower()
                    translations = translate(src, self.wordDict, k)
                    for m, translation in enumerate(translations):
                        tok = Token(tokenIndex=n,
                                    text=translation.getText())
                        arc = Arc(src=n,
                                  dst=n + 1,
                                  token=tok,
                                  weight=translation.getScore())
                        arcs.append(arc)
                        if m == 0:
                            # "naive" best translation is the first token we
                            # iterate through given a list of k translations
                            latpath.tokenList.append(tok)
                tokLat = TokenLattice(arcList=arcs)
                tokLat.cachedBestPath = latpath
                sentence.tokenization.lattice = tokLat
        return communication


if __name__ == "__main__":
    import argparse
    import sys

    reload(sys)
    sys.setdefaultencoding('utf8')

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, default=9090)
    parser.add_argument("-dictionary", dest="dictPath", type=str)
    options = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    handler = CommunicationHandler()
    logging.info('Loading the dictionary, please be patient.')
    handler.parseTranslations(options.dictPath)
    processor = Annotator.Processor(handler)
    transport = TSocket.TServerSocket(port=options.port)
    ipfactory = TCompactProtocol.TCompactProtocolFactory()
    opfactory = TCompactProtocol.TCompactProtocolFactory()

    server = TNonblockingServer.TNonblockingServer(processor, transport, ipfactory, opfactory)
    logging.info('Starting the server...')
    server.serve()
