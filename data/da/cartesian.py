#!/usr/bin/env python
# -*- coding: utf-8 -*-


# python 实现N个数组的排列组合(笛卡尔积算法)
class Cartesian():
    # 初始化
    def __init__(self, datagroup):
        self.datagroup = datagroup
        # 二维数组从后往前下标值
        self.counterIndex = len(datagroup)-1
        # 每次输出数组数值的下标值数组(初始化为0)
        self.counter = [0 for i in range(0, len(self.datagroup))]

    # 计算数组长度
    def countlength(self):
        i = 0
        length = 1
        while(i < len(self.datagroup)):
            length *= len(self.datagroup[i])
            i += 1
        return length

    # 递归处理输出下标
    def handle(self):
        # 定位输出下标数组开始从最后一位递增
        self.counter[self.counterIndex]+=1
        # 判断定位数组最后一位是否超过长度，超过长度，第一次最后一位已遍历结束
        if self.counter[self.counterIndex] >= len(self.datagroup[self.counterIndex]):

            # 重置末位下标
            self.counter[self.counterIndex] = 0
            # 标记counter中前一位
            self.counterIndex -= 1
            # 当标记位大于等于0，递归调用
            if self.counterIndex >= 0:
                self.handle()
            # 重置标记
            self.counterIndex = len(self.datagroup)-1

    # 排列组合输出
    def assemble(self):
        length = self.countlength()
        i = 0
        result = []
        while(i < length):
            attrlist = []
            j = 0
            while(j<len(self.datagroup)):
                attrlist.append(self.datagroup[j][self.counter[j]])
                j += 1
            result.append(attrlist)
            self.handle()
            i += 1
        return result