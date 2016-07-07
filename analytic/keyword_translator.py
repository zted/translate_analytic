#!/usr/bin/env python

from concrete import Communication, AnnotationMetadata, Tokenization, TokenList, Token, TokenizationKind
from concrete.services import Annotator
from concrete.util.concrete_uuid import AnalyticUUIDGeneratorFactory

from thrift.transport import TSocket, TTransport
from thrift.protocol import TCompactProtocol
from thrift.server import TNonblockingServer

import logging
import time
import nltk


class Word:
    def __init__(self, s):
        self.name = s
        self.translations = []

    def getName(self):
        return self.name

    def getTranslations(self):
        return self.translations

    def addTranslation(self, target, score):
        self.translations.append((target, score))
        return

    def sortTranslations(self):
        # sort by score
        self.translations = sorted(self.translations, key=lambda t: t[1], reverse=True)


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


def translate(srcWord, wordDict):
    translatedWord = "N/A"
    try:
        srcWordObj = wordDict[srcWord]
        translatedWord = srcWordObj.getTranslations()[0][0]
        # grabs the best translation available
    except KeyError:
        pass
    return translatedWord


class CommunicationHandler:
    def __init__(self):
        self.wordDict = {}

    def parseTranslations(self, filename):
        self.wordDict = initialize_translations(filename)

    def annotate(self, communication):
        for section in communication.sectionList:
            for sentence in section.sentenceList:
                for (n, token) in enumerate(sentence.tokenization.tokenList.tokenList):
                    src = token.text
                    target = translate(src, self.wordDict)
                    token.text = target
        return communication


if __name__ == "__main__":
    import argparse
    import sys

    reload(sys)
    sys.setdefaultencoding('utf8')

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, default=9095)
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
