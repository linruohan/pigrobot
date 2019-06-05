#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: da.py
Desc: 需求识别测试
Author: yanjingang(yanjingang@mail.com)
Date: 2017/8/8 23:48
"""

from dp import utils
from cartesian import Cartesian
import os
import sys
import glob
import logging
import json
import time
import itertools
import jieba


CUR_PATH = os.path.dirname(os.path.abspath(__file__))


class Node():
    id = ""  # id
    word = ""  # word
    ntype = 0  # type
    count = 0  # count
    childs = {}  # child nodes


class Da():
    intention_dict = {}

    def __init__(self):
        # log
        # 加载意图词典
        self.load_intention_dict()
        # 加载pattern词典
        self.load_pattern_dict()
        # 加载database conf
        self.database = {
            'animal-dinosaur': {
                'name': 'dps_test',
                'passwd': 'ALDN_170414_yjg',
                'hostname': 'ucp-table.spider.all.serv',
                'port': '8080',
                'user': 'aladdin',
                'env': 'online',
                'type': 'mongodb'
            },
            'car-buy': {
                'name': 'dps_test',
                'passwd': 'ALDN_170414_yjg',
                'hostname': 'ucp-table.spider.all.serv',
                'port': '8080',
                'user': 'aladdin',
                'env': 'online',
                'type': 'mongodb'
            }
        }
        #ret, msg, mid = self.write_db(self.database['animal-dinosaur'], {'@id':'test','@category':'恐龙','@name':'迅猛龙','speed':78})
        # print ret,msg,mid

    def process(self, packet):
        result = {'code': 0, 'msg': '', 'data': ''}
        logging.info('__input__')
        query = utils.full2half(packet['query']).strip().lower()
        logging.info(query)

        # 0.分词
        logging.info('__get_wordrank__')
        words = []
        res = jieba.cut(query, cut_all=False)
        for word in res:
            words.append({'word': word, 'score': 0.8})
        logging.debug(words)

        # 1.意图识别
        logging.info('__get_intention__')
        categorys = {}  # 意图id
        for word in words:
            if word['word'] in self.intention_dict:  # 在意图字典中
                for category in self.intention_dict[word['word']]:  # 遍历意图id
                    if category in categorys:  # 此意图Id已从之前的word获得
                        if word['word'] in categorys[category]:
                            categorys[category][word['word']] += word['score']
                        else:
                            categorys[category][word['word']] = word['score']
                    else:
                        categorys[category] = {word['word']: word['score']}
        logging.info(categorys)

        # 2.需求匹配
        logging.info('__get_pattern__')
        pattern_info = {}
        query_md5 = utils.md5(query)
        for category in categorys:
            # 预生成方式匹配
            if category in self.pattern_query and query_md5 in self.pattern_query[category]:
                if category not in pattern_info:
                    pattern_info[category] = []
                logging.debug(self.pattern_query[category][query_md5])
                pattern_info[category].append(self.pattern_query[category][query_md5])
        logging.info(pattern_info)

        # 3.上下文
        logging.info('__get_context__')
        context = {}
        logging.info('user_id: ' + packet['user_id'] + '\tsession_id: ' + packet['session_id'])
        # todo get context
        logging.info(context)

        # 4.知识检索
        logging.info('__get_knowledge__')
        for category in pattern_info:
            categorys = []
            for pattern in pattern_info[category]:
                print(pattern['value'])
            #ret, msg, data = Function.query_db(self.database[category], {"@category" : "恐龙"}, '',False,'speed',3)
            # print ret,msg,data

        # 5.知识积累
        logging.info('__save_knowledge__')

        # 6.保存到上下文
        logging.info('__save_context__')
        context = {
            'time': time.time(),
            'user_id': packet['user_id'],
            'session_id': packet['session_id'],
            'query': query,
            'wordrank': {
                'seg_phrase': res_wordrank['query_seg_phrase'],
                'words': words
            },
            'pattern': pattern_info
        }
        context_file = packet['user_id'] + '-' + packet['session_id'] + '.context'
        open(CUR_PATH + '/context/'+context_file, "w").write(json.dumps(context))
        logging.info(CUR_PATH + '/context/' + context_file)

        # output
        logging.info('__output__')
        logging.info(result)
        return result

    def load_intention_dict(self):
        """加载意图词典"""
        self.intention_dict = {}
        for filename in glob.glob(os.path.join(CUR_PATH + '/intention/', '*.dict')):
            dir, category = os.path.split(filename)
            if filename == '' or len(category) < 6:
                continue
            else:
                category = category[:-5]
            # read file
            fo = None
            try:
                fo = open(filename, 'r')
                if fo is None:
                    continue
                for line in fo:
                    line = line.strip()
                    if len(line) > 0:
                        if line in self.intention_dict:
                            self.intention_dict[line].append(category)
                        else:
                            self.intention_dict[line] = [category]
            finally:
                if fo:
                    fo.close()
        logging.debug(self.intention_dict)
        logging.info("load_intention_dict: [" + str(len(self.intention_dict)) + "]")
        return

    def load_pattern_dict(self):
        """加载需求匹配词典"""
        self.pattern_dict = {}
        # 加载pattern和term
        pattern_path = CUR_PATH + '/pattern/'
        for root, dirs, files in os.walk(pattern_path, True):
            for category in dirs:
                if category == 'term' or category.count('-') == 0:
                    continue
                self.pattern_dict[category] = {'term': {}, 'pattern': {}}
                # term
                for root, dirs, files in os.walk(pattern_path + category + '/term/'):
                    for tfile in files:
                        if tfile[-5:] != '.dict':
                            continue
                        term = tfile[:-5]
                        self.pattern_dict[category]['term'][term] = []
                        # read dict
                        fo = None
                        try:
                            fo = open(pattern_path + category + '/term/' + tfile, 'r')
                            if fo is None:
                                continue
                            for line in fo:
                                line = utils.full2half(line).strip().lower()
                                if len(line) > 0:
                                    #self.pattern_dict[category]['term'][term].append([term, line.split('   ')])
                                    self.pattern_dict[category]['term'][term].append(line.split('   '))
                        finally:
                            if fo:
                                fo.close()
                # pattern
                fo = None
                try:
                    fo = open(pattern_path + category + '/pattern.dict', 'r')
                    if fo is None:
                        continue
                    for line in fo:
                        line = line.strip()
                        if len(line) > 0:
                            pattern = line.strip()
                            self.pattern_dict[category]['pattern'][pattern] = []
                            pattern_arr = pattern.split('][')
                            for term_name in pattern_arr:
                                term_name = term_name.strip().replace('[', '').replace(']', '')
                                self.pattern_dict[category]['pattern'][pattern].append(term_name)
                finally:
                    if fo:
                        fo.close()

        logging.debug(self.pattern_dict)
        logging.info("load_pattern_dict: [" + str(len(self.pattern_dict)) + "]")

        # print self.get_cartesian_query([])
        # 预生成可能的组合
        self.pattern_query = {}
        for category in self.pattern_dict:
            self.pattern_query[category] = {}
            for pattern in self.pattern_dict[category]['pattern']:
                logging.info("get_pattern_query: [" + category + "][" + pattern + "][" + str(self.pattern_dict[category]['pattern'][pattern]) + "]")
                # 普通组合
                datagroup = []
                termgroup = []
                for term in self.pattern_dict[category]['pattern'][pattern]:
                    if term in self.pattern_dict[category]['term']:
                        # logging.info(self.pattern_dict[category]['term'][term])
                        datagroup.append(self.pattern_dict[category]['term'][term])
                        termgroup.append(term)

                logging.info("111")
                querys = self.get_cartesian_query(datagroup, termgroup)
                logging.info("222")
                self.pattern_query[category] = dict(self.pattern_query[category], ** querys)
                logging.info("333")
                # 杂质词组合
                '''
                if 'ignore' in self.pattern_dict[category]['term']:
                    # 单位置插入
                    for index in range(0, len(datagroup) + 1):
                        #print 'INDEX: ' + str(index)
                        ignoregroup = []
                        for i in range(0, len(datagroup)):
                            #print 'I: ' + str(i)
                            if i == index:  # 起始和中间位置插入
                                ignoregroup.append(self.pattern_dict[category]['term']['ignore'])
                            ignoregroup.append(datagroup[i])
                        # 末尾后缀
                        if index == len(datagroup):
                            ignoregroup.append(self.pattern_dict[category]['term']['ignore'])

                        querys = self.get_cartesian_query(ignoregroup)
                        for query in querys:
                            self.pattern_query[category][query['query']] = query['pattern']
                    # 多位置插入
                    for index in range(0, len(datagroup) + 1):
                        ignoregroup = []
                        for i in range(0, len(datagroup)):
                            if i != index:  # 起始和中间位置插入
                                ignoregroup.append(self.pattern_dict[category]['term']['ignore'])
                            ignoregroup.append(datagroup[i])
                        # 末尾后缀
                        if index == len(datagroup):
                            ignoregroup.append(self.pattern_dict[category]['term']['ignore'])

                        querys = self.get_cartesian_query(ignoregroup)
                        for query in querys:
                            self.pattern_query[category][query['query']] = query['pattern']
                    # 多位置插入+末尾强杂质词后缀
                    for index in range(0, len(datagroup) + 1):
                        ignoregroup = []
                        for i in range(0, len(datagroup)):
                            if i != index:  # 起始和中间位置插入
                                ignoregroup.append(self.pattern_dict[category]['term']['ignore'])
                            ignoregroup.append(datagroup[i])
                        # 末尾强后缀
                        ignoregroup.append(self.pattern_dict[category]['term']['ignore'])

                        querys = self.get_cartesian_query(ignoregroup)
                        for query in querys:
                            self.pattern_query[category][query['query']] = query['pattern']
                    # 全位置插入
                    for index in range(0, len(datagroup) + 1):
                        ignoregroup = []
                        for i in range(0, len(datagroup)):
                            ignoregroup.append(self.pattern_dict[category]['term']['ignore'])
                            ignoregroup.append(datagroup[i])
                        # 末尾后缀
                        ignoregroup.append(self.pattern_dict[category]['term']['ignore'])

                        querys = self.get_cartesian_query(ignoregroup)
                        for query in querys:
                            self.pattern_query[category][query['query']] = query['pattern']
                '''
        logging.debug(self.pattern_query)
        logging.info("load_pattern_query: [" + str(len(self.pattern_query)) + "]")
        return True

    def get_cartesian_query(self, datagroup, termgroup=[]):
        """获得多个数组的笛卡尔积query"""
        result = {}

        # logging.info("111-a")
        cartesian = Cartesian(datagroup)
        # logging.info("111-b")
        res = cartesian.assemble()
        # logging.info("111-c")
        for row in res:
            query = ''
            pattern = ''
            value = {}
            # for term in row:
            # logging.info("111-c-1")
            for i in range(len(row)):
                term = row[i]
                term_key = termgroup[i]
                term_val = term[0]
                term_synonym = ''
                if len(term) > 1:
                    term_synonym = term[1].strip()
                query += term_val
                pattern += '[' + term_key + ':' + term_val + '|' + term_synonym + ']'
                value[term_key] = term_val + '|' + term_synonym
            # logging.info("111-c-2")
            logging.debug(query + '\t' + pattern)
            result[utils.md5(query)] = {'query': query, 'pattern': pattern, 'value': value}
            # logging.info("111-c-3")
        # logging.info("111-d")

        return result


if __name__ == '__main__':
    # ut test
    #query = u"哪个恐龙跑的最快？"
    query = u"宝马x1售价？"
    user_id = 'O2UXAUPSU29NAY'
    session_id = 'AFS71813BCEF'  # str(time.time())

    utils.init_logging("robot", CUR_PATH)

    da = Da()
    res = da.process({'query': query, 'user_id': user_id, 'session_id': session_id})
