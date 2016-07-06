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
                print("Cannot find!")
                myWord = Word(src)
                someDict[src] = myWord
            myWord.addTranslation(target, score)
    for word in someDict.values():
        word.sortTranslations()
    return someDict


class CommunicationHandler:
    def __init__(self):
        self.wordDict = {}

    def parseTranslations(self, filename):
        self.wordDict = initialize_translations(filename)

    def annotate(self, communication):
        augf = AnalyticUUIDGeneratorFactory(communication)
        aug = augf.create()
        for section in communication.sectionList:
            for sentence in section.sentenceList:
                text = communication.text[sentence.textSpan.start:sentence.textSpan.ending]
                sentence.tokenization = Tokenization(uuid=aug.next(),
                                                     kind=TokenizationKind.TOKEN_LIST,
                                                     tokenList=TokenList(tokenList=[]),
                                                     tokenTaggingList=[],
                                                     metadata=AnnotationMetadata(timestamp=int(time.time()),
                                                                                 tool="nltk"))

                for i, token in enumerate(nltk.word_tokenize(text)):
                    sentence.tokenization.tokenList.tokenList.append(Token(tokenIndex=i, text=token))
        return communication


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, default=9092)
    options = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    fn = 'lex.en-zh'
    handler = CommunicationHandler()
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
