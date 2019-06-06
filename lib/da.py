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

    def __init__(self, name, deep=0, count=1, isleaf=False, childs=None, param=""):
        self.name = str(name)     # 名称
        self.id = utils.md5(self.name)    # id
        self.deep = deep      # 节点深度类型（0root，1意图分类，2解析模版分类，3+模版树或词库树节点）
        self.count = count  # 节点计数
        self.isleaf = isleaf  # 是否可作为叶子节点
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
            node.deep = self.deep + 1
            # node.print()
            self.childs[node.id] = node
            # self.print()
        return self.childs[node.id]

    def get_child(self, name):
        """获取子节点"""
        id = utils.md5(name)
        if id in self.childs:
            return self.childs[id]
        return None

    def get_child_names(self):
        """获取所有一级子节点的name列表"""
        names = []
        for id in self.childs:
            names.append(self.childs[id].name)
        return names

    def add_trie_child(self, _node, trieid=None):
        """增加单字字典树trietree"""
        node = self
        for i in range(len(_node.name)):
            isleaf = (i == len(_node.name) - 1)  # 是否是叶子
            #print(_node.name[i:i+1], isleaf)
            node = node.add_child(Node(name=_node.name[i:i+1], param=_node.param, isleaf=isleaf))
        return node

    def find_trietree(self, words):
        """从trietree中查找完全匹配字符串的叶子节点位置"""
        res = []  # 是否在query中匹配到这个dname
        node = self
        for i in range(len(words)):
            word = words[i:i+1]
            #print("{},{}".format(i, word))
            node = node.get_child(word)
            if node is None:  # 没找到
                break
            if node.isleaf:
                res.append({'node': self.name, 'pos': (0, i+1), 'substr': words[0:i+1]})
        return res

    def get_trie_child_names(self):
        """获取trietree递归子节点的name列表"""
        names = [self.name]
        for id in self.childs:
            names += self.childs[id].get_trie_child_names()
        return names

    def print(self, prefix=''):
        """打印树"""
        print(prefix + str(self.deep) + ' ' + self.name + ' ('+str(self.count) + ')\t'+str(len(self.childs)) + '\t'+str(self.isleaf) + '\t'+str(self.param))
        prefix += '-'
        for id in self.childs:
            if len(self.childs[id].childs) > 0:
                self.childs[id].print(prefix)
            else:
                print(prefix + str(self.childs[id].deep) + ' '+self.childs[id].name + ' ('+str(self.childs[id].count) + ')\t' +
                      str(len(self.childs[id].childs)) + '\t'+str(self.childs[id].isleaf) + '\t'+str(self.childs[id].param))


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
        query = utils.full2half(query).strip().lower()
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
        for _, dirs, __ in os.walk(parser_path, True):
            for category in dirs:
                if category.count('-') == 0 and category in ('term'):
                    continue
                category_node = self.parser_tree.add_child(Node(name=category))
                # pattern
                pattern_node = category_node.add_child(Node(name='pattern'))
                res = utils.load_data(parser_path + category + '/pattern.dict')
                for line in res:
                    _pattern_node = pattern_node
                    row = line[1:-1].split('][')
                    for i in range(len(row)):
                        isleaf = (i == len(row) - 1)
                        # print(line)
                        _pattern_node = _pattern_node.add_child(Node(name=row[i], isleaf=isleaf, param=line))
                        # _pattern_node.print()

                # term
                term_node = category_node.add_child(Node(name='term'))
                for _, __, files in os.walk(parser_path + category + '/term/'):
                    for tfile in files:
                        if tfile[-5:] != '.dict':
                            continue
                        term = tfile[:-5]
                        _term_node = term_node.add_child(Node(name=term))
                        # read dict
                        fo = None
                        try:
                            fo = open(parser_path + category + '/term/' + tfile, 'r')
                            if fo is None:
                                continue
                            for line in fo:
                                line = utils.full2half(line).strip().lower()
                                if len(line) > 0:
                                    line = line.split(' ', 1)
                                    _param = line[1] if len(line) > 1 else ''
                                    _term_node.add_trie_child(Node(name=line[0], param=_param))
                        finally:
                            if fo:
                                fo.close()

                # break

        # self.parser_tree.print()

    def get_parser(self, trigger, query):
        """解析某trigger下的query"""
        logging.info('__get_parser__{},{}'.format(trigger, query))
        parsers = []
        # query处理
        query = utils.full2half(query).strip().lower()
        # 意图parser配置/词典树
        parser_tree = self.parser_tree.get_child(trigger)
        # parser_tree.print()

        # 解析query
        _res = {}
        self.parser_query(parser_tree.get_child('pattern'), parser_tree.get_child('term'), query, _res)
        # print(_res)
        # res_tree.print()
        # 解析结果格式化
        for pname in _res:
            pattern_list = pname[1:-1].split('][')
            dict_count = len(pattern_list)
            if len(_res[pname]) < dict_count:  # 未完全匹配模版的跳过
                continue
            #print(pname, _res[pname])
            # 格式化res
            q = ''
            res = []
            for i in range(dict_count):
                dname = pattern_list[i]
                substr = _res[pname][i][0]['substr']
                if len(_res[pname][i]) > 1:  # 多选1时，使用后缀比较选择能匹配上的那个
                    for term in _res[pname][i]:
                        _q = term['substr'] + q
                        if _q == query[len(_q)*-1:]:
                            substr = term['substr']
                q = substr + q
                # print(q)
                res.append((dname, substr))
            res.reverse()
            parsers.append({'pattern': pname, 'parser': res})
        return parsers

    def parser_query(self, pattern_tree, term_tree, query, parent_res={}):
        """根据解析模版树和词库树解析query"""
        for id in pattern_tree.childs:
            ptree = pattern_tree.childs[id]  # 子树
            pid = ptree.param
            if pid not in parent_res:  # 按模版id分组
                parent_res[pid] = []
            res = term_tree.get_child(ptree.name).find_trietree(query)  # 用query匹配dname对应的term词典
            logging.debug("{}\t{}\t[{}] {}\t{}".format(pid, query, ptree.name, ptree.isleaf, res))
            for term in res:
                if len(ptree.childs) > 0 and len(res) > 0:  # 继续沿树往下找
                    self.parser_query(ptree, term_tree, query[term['pos'][1]:], parent_res)
            if len(res) > 0:
                parent_res[pid].append(res)


if __name__ == '__main__':
    """test"""
    utils.init_logging(log_file='da', log_path=constants.APP_PATH)

    da = Da()
    # 意图分类
    #res = da.get_trigger("宝马3系报价")
    res = da.get_trigger("哪个恐龙跑的最快？")
    print("trigger: {}".format(res))
    # 意图分类下的query解析
    #res = da.get_parser(res[0]['type'], "宝马3系报价")
    res = da.get_parser(res[0]['type'], "哪个恐龙跑的最快？")
    #res = da.get_parser(res[0]['type'], "跑的最快的恐龙")
    print("parser: {}".format(res))

    '''
    # tree test
    tree = Node(name='root')
    ctree = tree.add_child(Node('car'))
    # tree.print()
    ctree.add_trie_child(Node('一汽'))
    ctree.add_trie_child(Node('一起'))
    # ctree.print()
    ctree.add_trie_child(Node('一汽大众', param='aaa'))
    ctree.add_trie_child(Node('一汽奥迪'))
    ctree.add_trie_child(Node('上汽'))
    ctree.add_trie_child(Node('上汽通用'))
    ctree.add_trie_child(Node('上汽通用五菱'))
    ctree.print()

    # trietree查找
    res = ctree.find_trietree('一汽大众迈腾')
    print(res)
    '''
