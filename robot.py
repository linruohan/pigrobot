#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: face.py
Desc: 人脸识别基类
Author:yanjingang(yanjingang@mail.com)
Date: 2019/2/21 23:34
"""

import os
import sys
import time
import yaml
import logging
import camera
from dp.pygui import PySimpleGUI as sg
from dp import utils
CUR_PATH = os.path.dirname(os.path.abspath(__file__))


class Robot:
    """机器人控制中心"""
    # 配置
    USER_PATH = os.path.expanduser('~/.robot')
    CONF_FILE = USER_PATH + "/config.yml"
    FACE_DB_PATH = USER_PATH + "/facedb/"
    FACE_ID_PATH = FACE_DB_PATH + "/faceid/"
    CONFIG_DATA = {}
    # 摄像头数据
    CAMERA_DATA = {
        'camera': {  # 界面上方摄像头区域数据
            'filename': '',
            'faceids': []
        },
        'face': {  # 界面下方捕获人脸区域数据
            'catch': {},
            'list': [],
            'list_info': {
                'lastfaceid': '',
                'lasttime': 0,
            },
        }
    }

    def __init__(self):
        """初始化"""
        # 个人配置初始化
        if os.path.exists(self.USER_PATH) is False:
            utils.mkdir(self.USER_PATH)
        if os.path.exists(self.FACE_DB_PATH) is False:
            utils.mkdir(self.FACE_DB_PATH)
        if os.path.exists(self.FACE_ID_PATH) is False:
            utils.mkdir(self.FACE_ID_PATH)
        try:
            print(self.CONF_FILE)
            if os.path.exists(self.CONF_FILE) is False:
                for name in ['config.yml', '八戒.pmdl']:
                    utils.cp(CUR_PATH+'/conf/' + name, self.USER_PATH + '/' + name)
            with open(self.CONF_FILE, "r") as f:
                self.CONFIG_DATA = yaml.safe_load(f)
        except Exception as e:
            logging.error("load conf fail! {} {}".format(self.CONF_FILE, e))
        print(self.CONFIG_DATA)

        # 启动摄像头人脸识别
        self.camera = camera.Face()
        # self.camera.get_camera_face(camera_data=self.CAMERA_DATA, callback=camera.show_camera_face_window)
        self.camera.get_camera_face(camera_data=self.CAMERA_DATA, callback=self.patrol)

    def patrol(self, camera_data):
        """巡逻"""
        while True:
            time.sleep(5)
            # 检查视野中的人
            newface = {}
            if self.CAMERA_DATA['camera']['filename'] and len(self.CAMERA_DATA['face']['list']) > 0 and time.time() - self.CAMERA_DATA['face']['list'][-1]['lasttime'] < 2.0:
                newface = self.CAMERA_DATA['face']['list'][-1]
            print(newface)
            # 主人初始化
            if self.CONFIG_DATA['master']['faceid'] == '':
                if 'faceid' in newface:
                    ret = input("看到了，主人是你吗？ [y/n]")
                    if ret == 'y':
                        name = input("你叫什么名字？ ")
                        if name != '':
                            print('正在保存主人信息...')
                            self.CONFIG_DATA['master']['name'] = name
                            self.CONFIG_DATA['master']['nick'] = '主人'
                            # 保存人脸
                            faceid = self.camera.register_faceid(newface['filename'], name, faceid_path=self.FACE_ID_PATH)
                            self.CONFIG_DATA['master']['faceid'] = faceid
                            # 保存配置
                            with open(self.CONF_FILE, "wb") as f:
                                print(yaml.dump(self.CONFIG_DATA))
                                #yaml.dump(self.CONFIG_DATA, f)
                else:
                    print('主人，请正对着我，让我看到你的脸～')

            # 巡逻并旋转摄像头
            # TODO
            # 发现可疑人员报警


if __name__ == '__main__':
    """test"""
    # log init
    log_file = 'robot-' + str(os.getpid())
    utils.init_logging(log_file=log_file, log_path=CUR_PATH)
    print("log_file: {}".format(log_file))

    robot = Robot()
