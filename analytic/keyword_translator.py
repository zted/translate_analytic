#!/usr/bin/env python

from concrete import Communication, AnnotationMetadata, Tokenization, TokenList, Token, TokenizationKind, TokenLattice, Arc
from concrete.services import Annotator
from concrete.util.concrete_uuid import AnalyticUUIDGeneratorFactory

from thrift.transport import TSocket, TTransport
from thrift.protocol import TCompactProtocol
from thrift.server import TNonblockingServer

import logging
import time
import nltk


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
                myWord = Word(src)
                someDict[src] = myWord
            myWord.addTranslation(target, score)
    for word in someDict.values():
        # once the entire dictionary is loaded, sort all translations from best to worst
        word.sortTranslations()
    return someDict


def translate(srcWord, wordDict, topK):
    try:
        srcWordObj = wordDict[srcWord]
        translatedWord = srcWordObj.getTranslations()[0:topK]
        # grabs the best translation available
    except KeyError:
        translatedWord = [Translation(srcWord, 0)]
    return translatedWord


class CommunicationHandler:
    def __init__(self):
        self.wordDict = {}

    def parseTranslations(self, filename):
        self.wordDict = initialize_translations(filename)

    def annotate(self, communication):
        k = 3
        for section in communication.sectionList:
            for sentence in section.sentenceList:
                arcs = []
                for (n, token) in enumerate(sentence.tokenization.tokenList.tokenList):
                    src = token.text
                    translations = translate(src, self.wordDict, k)
                    for translation in translations:
                        tok = Token(tokenIndex=n,
                                    text=translation.getText())
                        arc = Arc(src=n,
                                  dst=n+1,
                                  token=tok,
                                  weight=translation.getScore())
                        arcs.append(arc)
                tokLat = TokenLattice(arcList=arcs)
                sentence.tokenization.lattice = tokLat
        return communication


if __name__ == "__main__":
    import argparse
    import sys

    reload(sys)
    sys.setdefaultencoding('utf8')

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, default=9090)
    options = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    fn = '/opt/scripts/lex.en-zh'
    handler = CommunicationHandler()
    handler.parseTranslations(fn)
    processor = Annotator.Processor(handler)
    transport = TSocket.TServerSocket(port=options.port)
    # tfactory = TTransport.TBufferedTransportFactory()
    # pfactory = TCompactProtocol.TCompactProtocolFactory()
    ipfactory = TCompactProtocol.TCompactProtocolFactory()
    opfactory = TCompactProtocol.TCompactProtocolFactory()

    server = TNonblockingServer.TNonblockingServer(processor, transport, ipfactory, opfactory)
    # server = TNonblockingServer.TNonblockingServer(processor, transport, tfactory, pfactory)
    logging.info('Starting the server...')
    server.serve()
