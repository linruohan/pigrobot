#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: da.py
Desc: 需求识别基类
Author:yanjingang(yanjingang@mail.com)
Date: 2019/2/21 23:34
"""

import logging
from dp import utils
from dp.da import Da
import constants


if __name__ == '__main__':
    """test"""
    utils.init_logging(log_file='da', log_path=constants.APP_PATH)

    da = Da(dict_path=constants.APP_PATH + "/data/da/")
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
