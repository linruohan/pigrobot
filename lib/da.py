#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: da.py
Desc: 需求识别基类
Author:yanjingang(yanjingang@mail.com)
Date: 2019/2/21 23:34
"""

import os
import sys
import glob
import logging
import json
import time
import itertools
import jieba
from dp import utils
import constants


class Node(object):
    """解析模版/词库树"""

    def __init__(self, name, deep=0, count=1, childs=None, param=""):
        self.name = str(name)     # 名称
        self.id = utils.md5(self.name)    # id
        self.deep = deep      # 节点深度类型（0root，1意图分类，2解析模版分类，3+模版树或词库树节点）
        self.count = count   # 节点计数
        self.param = param   # 参数
        self.childs = childs if childs is not None else {}      # 子节点

    def add_count(self, count=1):
        """增加节点计数"""
        self.count += count

    def add_child(self, node):
        """增加子节点"""
        if node.id in self.childs:
            self.childs[node.id].add_count()
        else:
            node.deep = self.deep+1
            self.childs[node.id] = node
        return self.childs[node.id]

    def get_child(self, name):
        """获取子节点"""
        id = utils.md5(name)
        if id in self.childs:
            return self.childs[id]

        return None

    def add_word_child(self, _node):
        """增加单字子节点"""
        # Node(name=_term, param=_param, deep=3)
        node = self
        for w in _node.name:
            node = node.add_child(Node(name=w, param=_node.param, deep=_node.deep))
        return node

    def print(self, prefix=''):
        """打印树"""
        if self.name == 'root':
            print(prefix + str(self.deep) + ' ' + self.name + ' ('+str(self.count) + ')')
        prefix += '-'
        for id in self.childs:
            print(prefix + str(self.childs[id].deep) + ' '+self.childs[id].name + ' ('+str(self.childs[id].count) + ')\t'+str(len(self.childs[id].childs)))
            if len(self.childs[id].childs) > 0:
                self.childs[id].print(prefix)


class Da():
    """需求识别"""
    DICT_PATH = constants.APP_PATH + "/data/da/"

    def __init__(self, dict_path=None):
        """初始化词典"""
        if dict_path is not None:
            self.DICT_PATH = dict_path
        # 加载意图词典
        self.load_trigger_dict()
        # 加载pattern词典
        self.load_parser_dict()

    def load_trigger_dict(self):
        """加载意图词典"""
        logging.info('__load_trigger_dict__')
        self.trigger_dict = {}
        for filename in glob.glob(os.path.join(self.DICT_PATH + '/trigger/', '*.dict')):
            _, category = os.path.split(filename)
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
                        if line in self.trigger_dict:
                            self.trigger_dict[line].append(category)
                        else:
                            self.trigger_dict[line] = [category]
            finally:
                if fo:
                    fo.close()
        logging.debug(self.trigger_dict)
        logging.info("load_trigger_dict: [" + str(len(self.trigger_dict)) + "]")
        return

    def get_trigger(self, query):
        """意图分类识别"""
        logging.info('__get_trigger__{}'.format(query))
        categorys = {}  # 意图id
        words = []
        res = jieba.cut(query, cut_all=False)
        for word in res:
            words.append({'word': word, 'score': 1.0})
        logging.debug(words)
        for word in words:
            if word['word'] in self.trigger_dict:  # 在意图字典中
                for category in self.trigger_dict[word['word']]:  # 遍历意图id
                    if category in categorys:  # 此意图Id已从之前的word获得
                        if word['word'] in categorys[category]:
                            categorys[category][word['word']] += word['score']
                        else:
                            categorys[category][word['word']] = word['score']
                    else:
                        categorys[category] = {word['word']: word['score']}
        logging.info(categorys)

        triggers = []
        for category in categorys:
            triggers.append({'type': category, 'term': categorys[category]})
        return triggers

    def load_parser_dict(self):
        """加载需求匹配词典"""
        logging.info('__load_parser_dict__')
        self.parser_tree = Node(name='root')
        # 加载pattern和term
        parser_path = self.DICT_PATH + '/parser/'
        for root, dirs, files in os.walk(parser_path, True):
            for category in dirs:
                if category.count('-') == 0 and category in ('term'):
                    continue
                category_node = self.parser_tree.add_child(Node(name=category))
                # pattern
                pattern_node = category_node.add_child(Node(name='pattern'))
                res = utils.load_data(parser_path + category + '/pattern.dict', split='][')
                for row in res:
                    _pattern_node = pattern_node
                    for term_name in row:
                        _pattern_node = _pattern_node.add_child(Node(name=term_name.replace('[', '').replace(']', '')))

                # ignore
                ignore_node = category_node.add_child(Node(name='ignore'))
                res = utils.load_data(parser_path + category + '/ignore.dict')
                for row in res:
                    ignore_node.add_child(Node(name=row))

                # term
                term_node = category_node.add_child(Node(name='term'))
                for root, dirs, files in os.walk(parser_path + category + '/term/'):
                    for tfile in files:
                        if tfile[-5:] != '.dict':
                            continue
                        term = tfile[:-5]
                        _term_node = term_node.add_child(Node(name=term))
                        print(_term_node)
                        # read dict
                        fo = None
                        try:
                            fo = open(parser_path + category + '/term/' + tfile, 'r')
                            if fo is None:
                                continue
                            for line in fo:
                                line = utils.full2half(line).strip().lower()
                                if len(line) > 0:
                                    line = line.split('\t', 1)
                                    _param = line[1] if len(line) > 1 else ''
                                    _term_node.add_word_child(Node(name=line[0], param=_param))
                        finally:
                            if fo:
                                fo.close()

                # break

        self.parser_tree.print()

    def get_parser(self, trigger, query):
        """解析某trigger下的query"""
        logging.info('__get_parser__{},{}'.format(trigger, query))
        parsers = {}  # 解析结果

        return parsers


if __name__ == '__main__':
    """test"""
    utils.init_logging(log_file='da', log_path=constants.APP_PATH)

    da = Da()
    # 意图分类
    res = da.get_trigger("哪个恐龙跑的最快？")
    print(res)
    # 意图分类下的query解析
    res = da.get_parser(res[0]['type'], "哪个恐龙跑的最快？")
    print(res)

    '''
    # tree test
    tree = Node(name='root')
    ctree = tree.add_child(Node('car'))
    tree.print()
    ctree.add_word_child(Node('一汽'))
    ctree.add_word_child(Node('一起'))
    ctree.add_word_child(Node('一汽大众'))
    ctree.add_word_child(Node('一汽奥迪'))
    ctree.add_word_child(Node('上汽'))
    ctree.add_word_child(Node('上汽通用'))
    ctree.add_word_child(Node('上汽通用五菱'))
    ctree.print()
    '''
