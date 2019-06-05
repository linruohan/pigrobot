#!/usr/bin/env python
# -*- coding: utf-8 -*-
########################################################################
#
# Copyright (c) 2016 Baidu.com, Inc. All Rights Reserved
#
########################################################################

"""
Desc: 将mangodb中的车系实体名称生成到term词槽
Author: yanjingang@baidu.com
Cmd: python /home/work/search/dps/robot/data/car-series/car_series_terms.py
"""

basepath = '/home/work/search/dps/'
taskpath = '/home/work/search/dps/robot/data/car-series/'

import sys
import os

sys.path.append(basepath)
sys.path.append(basepath + 'baselib/')
from baselib.dps.taskbase import TaskBase


class CarSeriesTerms(TaskBase):
    """车系库导出数据"""

    def __init__(self, env):
        """加载配置"""
        # 初始化配置
        conf = {"schema": taskpath + "conf/car_series_terms.conf"}
        TaskBase.__init__(self, conf)

        # clear file
        if os.path.exists(self.conf['target']['path'] + self.conf['target']['brand_dict']):
            os.remove(self.conf['target']['path'] + self.conf['target']['brand_dict'])
        if os.path.exists(self.conf['target']['path'] + self.conf['target']['series_dict']):
            os.remove(self.conf['target']['path'] + self.conf['target']['series_dict'])
        if os.path.exists(
                self.conf['target']['path'] + self.conf['target']['brand_name_idx_diff']):
            os.remove(self.conf['target']['path'] + self.conf['target']['brand_name_idx_diff'])
        if os.path.exists(
                self.conf['target']['path'] + self.conf['target']['series_name_idx_diff']):
            os.remove(
                self.conf['target']['path'] + self.conf['target']['series_name_idx_diff'])
        if os.path.exists(self.conf['target']['path'] + self.conf['target']['debug_file']):
            os.remove(self.conf['target']['path'] + self.conf['target']['debug_file'])

    def execute(self):
        """执行"""
        errno = TaskBase.execute(self)
        return errno

    def add_alias(self, data):
        """
        挖掘车品牌、系名别名
        :param data:车系实体
        :return:车系实体
        """
        brand_skip = [u'汽车', u'新能源', u'商务车', u'专用车', u'电动汽车', u'商用车', u'乘用车', u'旅居车', u'客车',
                      u'自动车', u'亚太', u'轻汽', u'进口', u'(进口)', u'（进口）', u'四川', u'厦门', u'北京',
                      u'江西', u'绵阳', u'福建', u'天津', u'吉林', u'南京', u'郑州']
        series_skip = [u'皮卡', u'系列', u'客车系列', 'm', 'r', 'f', '100', '200', u'王x5', u'之光v',
                       u'法拉利la']
        skip_alias = brand_skip + series_skip
        # 0.id
        series_id = data['@sid']

        # 1.brand & manufacturer
        brand_id = ''
        brand_name = ''
        manufacturer_name = ''
        brand_alias = []
        manufacturer_alias = []
        if 'brand' in data:
            if 'name_zh' in data['brand'] and data['brand']['name_zh'].strip() != '':
                brand_alias.append(data['brand']['name_zh'].lower())
                if brand_name == '':
                    brand_name = data['brand']['name_zh'].lower()
            if 'name' in data['brand'] and data['brand']['name'].strip() != '':
                brand_alias.append(data['brand']['name'].lower())
                if brand_name == '':
                    brand_name = data['brand']['name'].lower()
            if 'name_en' in data['brand'] and data['brand']['name_en'].strip() != '':
                brand_alias.append(data['brand']['name_en'].lower())
                if brand_name == '':
                    brand_name = data['brand']['name_en'].lower()
        if 'brand_name_idx' in data and data['brand_name_idx'].strip() != '':
            tmp_arr = data['brand_name_idx'].split(';')
            for tmp in tmp_arr:
                if tmp.strip() != '':
                    brand_alias.append(tmp.strip().lower())
        if 'brand_alias_idx' in data and data['brand_alias_idx'].strip() != '':
            tmp_arr = data['brand_alias_idx'].split(';')
            for tmp in tmp_arr:
                if tmp.strip() != '':
                    brand_alias.append(tmp.strip().lower())
        if 'manufacturer' in data:
            if 'name' in data['manufacturer'] and data['manufacturer']['name'].strip() != '':
                manufacturer_name = data['manufacturer']['name'].lower()
                brand_alias.append(manufacturer_name)
                manufacturer_alias.append(manufacturer_name)
                # 广汽吉奥 => 广汽
                for bn in brand_skip + [brand_name]:
                    tmp = manufacturer_name.replace(bn, '').strip()
                    if tmp[-1:] == '-':
                        tmp = tmp[:-1]
                    if tmp[-2:] == '()':
                        tmp = tmp[:-2]
                    if tmp != '' and tmp != manufacturer_name and tmp not in skip_alias:
                        brand_alias.append(tmp)
                        manufacturer_alias.append(tmp)
                        add_msg = "BEAND ALIAS:[" + tmp + "]\t" + series_id + "\t" + manufacturer_name
                        self.debug(add_msg)
        if 'merged_brand_sid' in data:
            brand_id = data['merged_brand_sid'].strip()
        for alias in brand_alias:  # clear
            if alias.count('-') > 0 or alias.count(' ') > 0 or alias.count(
                    '(') > 0 or alias.count(')') > 0 or alias.count(u'（') > 0 or alias.count(
                u'）') > 0 or alias.count(u'新能源') > 0 or alias.count(
                u'汽车') > 0 or alias.count(u'制造') > 0:
                brand_alias.append(
                    alias.replace('-', '').replace(' ', '').replace('(', '').replace(')',
                                                                                     '').replace(
                        u'（', '').replace(u'）', '').replace(u'新能源', '').replace(u'汽车',
                                                                                '').replace(
                        u'制造', ''))
        brand_alias = set(brand_alias)
        for name in brand_alias:
            self.write_file(name, self.conf['target']['brand_dict'],
                            self.conf['target']['path'])

        # 2.series
        series_name = ''
        series_alias = []
        if 'series' in data:
            if 'name_zh' in data['series'] and data['series']['name_zh'].strip() != '':
                series_alias.append(data['series']['name_zh'].lower())
                if series_name == '':
                    series_name = data['series']['name_zh'].lower()
            if 'name' in data['series'] and data['series']['name'].strip() != '':
                series_alias.append(data['series']['name'].lower())
                if series_name == '':
                    series_name = data['series']['name'].lower()
            if 'name_en' in data['series'] and data['series']['name_en'].strip() != '':
                series_alias.append(data['series']['name_en'].lower())
                if series_name == '':
                    series_name = data['series']['name_en'].lower()
            if 'series_alias' in data['series'] and type(
                    data['series']['series_alias']) is list:
                # series_alias += data['series']['series_alias']
                for tmp in data['series']['series_alias']:
                    if tmp.strip() != '':
                        series_alias.append(tmp.lower())
            if 'series_name_arr' in data['series'] and type(
                    data['series']['series_name_arr']) is list:
                # series_alias += data['series']['series_name_arr']
                for tmp in data['series']['series_name_arr']:
                    if tmp.strip() != '':
                        series_alias.append(tmp.lower())
            if 'manufacturer_series_arr' in data['series'] and type(
                    data['series']['manufacturer_series_arr']) is list:
                # series_alias += data['series']['manufacturer_series_arr']
                for tmp in data['series']['manufacturer_series_arr']:
                    if tmp.strip() != '':
                        series_alias.append(tmp.lower())
            if 'brand_series_alias_arr' in data['series'] and type(
                    data['series']['brand_series_alias_arr']) is list:
                # series_alias += data['series']['brand_series_alias_arr']
                for tmp in data['series']['brand_series_alias_arr']:
                    if tmp.strip() != '':
                        series_alias.append(tmp.lower())
        if 'series_name_idx' in data and data['series_name_idx'].strip() != '':
            tmp_arr = data['series_name_idx'].split(';')
            for tmp in tmp_arr:
                if tmp.strip() != '':
                    series_alias.append(tmp.lower())
        if 'series_alias_idx' in data and data['series_alias_idx'].strip() != '':
            tmp_arr = data['series_alias_idx'].split(';')
            for tmp in tmp_arr:
                if tmp.strip() != '':
                    series_alias.append(tmp.lower())
        if 'series_name_zh_idx' in data and data['series_name_zh_idx'].strip() != '':
            tmp_arr = data['series_name_zh_idx'].split(';')
            for tmp in tmp_arr:
                if tmp.strip() != '':
                    series_alias.append(tmp.lower())
        if 'series_name_en_idx' in data and data['series_name_en_idx'].strip() != '':
            tmp_arr = data['series_name_en_idx'].split(';')
            for tmp in tmp_arr:
                if tmp.strip() != '':
                    series_alias.append(tmp.lower())
        # clear
        for alias in series_alias:
            if alias.count('-') > 0 or alias.count(' ') > 0 or alias.count(
                    '(') > 0 or alias.count(')') > 0 or alias.count(u'（') > 0 or alias.count(
                u'）') or alias.count(u'级') > 0 or alias.count(u'系列') > 0 or alias.count(
                u'汽车') > 0 or alias.count(u'制造') > 0:
                series_alias.append(
                    alias.replace('-', '').replace(' ', '').replace('(', '').replace(')',
                                                                                     '').replace(
                        u'（', '').replace(u'）', '').replace(u'级', '').replace(u'系列',
                                                                              '').replace(
                        u'汽车', '').replace(u'制造', ''))
        # add sort alias
        skip_alias2 = [u'之星']
        for brand in brand_alias:
            tmp = series_name
            if brand != u'进口':
                tmp = series_name.replace(brand, '').strip()
            if tmp.count(u'汽车') > 0:
                tmp = tmp.replace(u'汽车', '')
            if tmp[:1] == '-':
                tmp = tmp[1:]
            if tmp in skip_alias or tmp[:2] in skip_alias2 or (
                    brand == u'马自达' and tmp[:1].isdigit()) or (
                    brand == u'rs' and tmp[-2:-1] == ' ') or (len(tmp) <= 2 and tmp.isdigit()):
                continue
            if series_alias.count(tmp) == 0 and len(tmp) > 1:  # 宝马8系=>8系
                series_alias.append(tmp)
                add_msg = "SERIES ALIAS:[" + tmp + "]\t" + series_id + "\t" + series_name + "\t" + brand + "\t" + ','.join(
                    series_alias)  # +"\t"+','.join(brand_alias)
                self.debug(add_msg)

            tmp = tmp.replace('-', '').replace(' ', '').replace('(', '').replace(')',
                                                                                 '').replace(
                u'级', '')
            if series_alias.count(tmp) == 0 and len(tmp) > 1:  # gla级=>gla
                series_alias.append(tmp)
                add_msg = "SERIES ALIAS:[" + tmp + "]\t" + series_id + "\t" + series_name + "\t" + brand + "\t" + ','.join(
                    series_alias)  # +"\t"+','.join(brand_alias)
                self.debug(add_msg)

            tmp = tmp.replace(u'进口', '').replace('(', '').replace(')', '').replace(u'（',
                                                                                   '').replace(
                u'）', '')
            if series_alias.count(tmp) == 0 and len(tmp) > 1:  # spyder进口
                series_alias.append(tmp)
                add_msg = "SERIES ALIAS:[" + tmp + "]\t" + series_id + "\t" + series_name + "\t" + brand + "\t" + ','.join(
                    series_alias)  # +"\t"+','.join(brand_alias)
                self.debug(add_msg)

        series_alias = set(series_alias)
        for name in series_alias:
            self.write_file(name, self.conf['target']['series_dict'],
                            self.conf['target']['path'])

        # debug
        #line = "%s\t%s => %s\t%s => %s" % (
        #    series_id, series_name, ','.join(series_alias), brand_name, ','.join(brand_alias))
        #self.write_file(line, self.conf['target']['debug_file'], self.conf['target']['path'])

        # 3.add new alias index
        # diff idx
        old_brand_idx = []
        old_series_idx = []
        for old in data['brand_name_idx'].split(';') + data['brand_alias_idx'].split(';'):
            if old.strip() != '':
                old_brand_idx.append(old.lower())
        for old in data['series_name_idx'].split(';') + data['series_alias_idx'].split(';'):
            if old.strip() != '':
                old_series_idx.append(old.lower())
        old_brand_idx = set(old_brand_idx)
        old_series_idx = set(old_series_idx)
        if brand_alias != old_brand_idx:
            data['brand_name_idx_bak'] = data['brand_name_idx']
            data['brand_name_idx'] = ';'.join(brand_alias)
            self.write_file(series_id + "\t" + series_name + "\t" + ';'.join(
                old_brand_idx) + "\t" + ';'.join(brand_alias),
                            self.conf['target']['brand_name_idx_diff'],
                            self.conf['target']['path'])
        if series_alias != old_series_idx:
            data['series_name_idx_bak'] = data['series_name_idx']
            data['series_name_idx'] = ';'.join(series_alias)
            self.write_file(series_id + "\t" + series_name + "\t" + ';'.join(
                old_series_idx) + "\t" + ';'.join(series_alias),
                            self.conf['target']['series_name_idx_diff'],
                            self.conf['target']['path'])

        return data


if __name__ == '__main__':
    # execute
    series = CarSeriesTerms({})
    series.execute()
