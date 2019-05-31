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
import copy
import logging
from dp.pygui import PySimpleGUI as sg
from dp import utils, audio
from lib import TTS, config, Player, constants, ASR, camera
from lib.snowboy import snowboydecoder
CUR_PATH = os.path.dirname(os.path.abspath(__file__))


class Robot:
    """机器人控制中心"""
    # 配置
    #USER_PATH = os.path.expanduser('~/.robot')
    USER_PATH = os.path.expanduser('~/_robot')
    CONF_FILE = USER_PATH + "/config.yml"
    FACE_ID_PATH = USER_PATH + "/facedb/faceid/"
    TEMP_PATH = USER_PATH + "/tmp/"
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
        utils.mkdir(self.USER_PATH)
        utils.mkdir(self.TEMP_PATH)
        utils.mkdir(self.FACE_ID_PATH)
        print(self.CONF_FILE)
        if os.path.exists(self.CONF_FILE) is False:
            for name in ['config.yml', '八戒.pmdl', '小白.pmdl']:
                utils.cp(CUR_PATH+'/conf/' + name, self.USER_PATH + '/' + name)
        self.CONFIG_DATA = utils.load_conf(self.CONF_FILE)
        # print(self.CONFIG_DATA)
        # 主人初始化状态(status: 1face已确认；2名字已确认)
        self.master = {'status': 0, 'time': 0, 'face': '', 'morning': 0, 'noon': 0, 'evening': 0, 'lastask': 0}
        self.guest = {'status': 0, 'time': 0, 'face': '', 'morning': 0, 'noon': 0, 'evening': 0, 'lastask': 0}
        # self.master.update(self.CONFIG_DATA['master'])
        # print(self.master)

        # 初始化语音合成
        self.saying = ''  # 是否正在播放
        self.tts = TTS.get_engine_by_slug(config.get('tts_engine', 'baidu-tts'))

        # 初始化语音识别
        self.listening = ''  # 是否正在收音
        self.asr = ASR.get_engine_by_slug(config.get('asr_engine', 'tencent-asr'))

        # 启动摄像头人脸识别
        self.camera = camera.Face(faceid_path=self.FACE_ID_PATH, temp_path=self.TEMP_PATH)
        #self.camera.get_camera_face(camera_data=self.CAMERA_DATA, callback=camera.show_camera_face_window)
        self.camera.get_camera_face(camera_data=self.CAMERA_DATA, callback=self.patrol)

    def patrol(self, camera_data):
        """巡逻"""
        while True:
            time.sleep(2)
            # 检查视野中的人
            self.newface = {}
            if self.CAMERA_DATA['camera']['filename'] and len(self.CAMERA_DATA['face']['list']) > 0 and time.time() - self.CAMERA_DATA['face']['list'][-1]['lasttime'] < 2.0:
                self.newface = self.CAMERA_DATA['face']['list'][-1]
                if self.newface['facename'] not in ('', 'unknown') and self.master['evening'] == 0:
                    self.say('{}晚上好，我是{}，有事叫我哦～'.format(self.newface['facename'], config.get('robot_name_cn', '八戒')))
                    self.master['evening'] += 1
            print(self.newface)
            # 主人初始化
            if self.CONFIG_DATA['master']['faceid'] == '':
                if 'faceid' in self.newface:
                    if self.master['status'] == 0 and self.saying == '' and self.listening == '':
                        self.say('主人是你吗？', callback=self.callback_ismaster)
                else:
                    if self.saying == '' and self.listening == '':
                        self.say('主人，请正对着我，让我看到你的脸～')
                        self.master['status'] = 0
            elif 'faceid' in self.newface and self.newface['faceid'] == 'unknown':  # 认识陌生人
                if self.guest['status'] == 0 and self.saying == '' and (self.guest['lastask'] == 0 or time.time() - self.guest['lastask'] > 30):
                    self.guest['status'] = 1
                    self.guest['face'] = self.newface
                    self.guest['lastask'] = time.time()
                    self.say('你是谁？', callback=self.callback_guestname)

            # 话筒收音
            #answer = self.listen()

            # 巡逻并旋转摄像头
            # TODO
            # 发现可疑人员报警

    def callback_ismaster(self, msg):
        """确认face是否主人的回调"""
        self.saying = ''
        answer = self.listen()   # 收音
        print(answer)
        if len(answer) > 0 and answer.count('是') > 0 and answer.count('不是') == 0:
            self.master['status'] = 1
            self.master['face'] = self.newface
            self.master['lastask'] = time.time()
            self.say('你叫什么名字？', callback=self.callback_mastername)

    def callback_mastername(self, msg):
        """确认主人名字的回调"""
        self.saying = ''
        answer = self.listen()  # 收音
        print(answer)
        if len(answer) == 0:
            self.say('你叫什么名字？', callback=self.callback_mastername)
        else:
            name = utils.clear_punctuation(answer)
            self.say('正在保存主人[{}]的信息... '.format(name))
            self.CONFIG_DATA['master']['name'] = name
            self.CONFIG_DATA['master']['nick'] = '主人'
            # 保存人脸
            faceid = self.camera.register_faceid(self.master['face']['filename'], name, faceid_path=self.FACE_ID_PATH)
            self.CONFIG_DATA['master']['faceid'] = faceid
            # 保存配置
            utils.dump_conf(self.CONFIG_DATA, self.CONF_FILE)
            self.master['status'] = 2

    def callback_guestname(self, msg):
        """确认陌生人名字的回调"""
        self.saying = ''
        answer = self.listen()  # 收音
        print(answer)
        if len(answer) == 0:
            if len(self.CAMERA_DATA['face']['list']) > 0 and self.CAMERA_DATA['face']['list'][-1]['faceid'] != 'unknown':
                self.say('原来是{}啊，不好意思刚没看清楚。'.format(self.CAMERA_DATA['face']['list'][-1]['facename']))
                self.guest['status'] == 0
                self.guest['lastask'] = 0
            elif self.guest['lastask'] != 0:
                t = time.time() - self.guest['lastask']
                if t <= 10:
                    self.say('你到底是谁？', callback=self.callback_guestname)
                elif t > 10 and t < 15:
                    self.say('不说就算了，懒得理你！', callback=self.callback_guestname)
                elif t > 15:  # 总不回答就不问了
                    self.guest['status'] == 0
        else:
            name = utils.clear_punctuation(answer)
            self.say('正在保存[{}]的信息... '.format(name))
            # 保存人脸
            faceid = self.camera.register_faceid(self.guest['face']['filename'], name, faceid_path=self.FACE_ID_PATH)
            self.guest['status'] = 2

    def say(self, msg, cache=False, callback=None):
        """说话"""
        print("saying: "+msg)
        self.saying = msg
        voice = ''
        if utils.get_cache_file(msg, constants.TEMP_PATH):
            logging.info("命中缓存，播放缓存语音")
            voice = utils.get_cache_file(msg, constants.TEMP_PATH)
        else:
            try:
                voice = self.tts.get_speech(msg)
                if cache:
                    utils.cache_file(voice, msg, constants.TEMP_PATH)
            except Exception as e:
                logging.error('保存缓存失败：{}'.format(e))

        def _callback():
            if callback is not None:
                return callback(msg)
            else:
                return self.say_callback(msg)
        audio.play(voice, delete=not cache, callback=_callback)

    def say_callback(self, msg):
        self.saying = ''

    def listen(self):
        """收音并识别为文字"""
        if self.listening == '':
            self.listening = str(int(time.time()))
        # Player.play(constants.getData('./media/beep_hi.wav'))
        audio.play(constants.getData('./media/on.wav'))
        hotword_model = constants.getHotwordModel(config.get('hotword', 'default.pmdl'))
        # print(hotword_model)
        listener = snowboydecoder.ActiveListener([hotword_model])
        voice = listener.listen(
            silent_count_threshold=config.get('silent_threshold', 15),
            recording_timeout=config.get('recording_timeout', 5) * 4
        )
        # Player.play(constants.getData('./media/beep_lo.wav'))
        Player.play(constants.getData('./media/off.wav'))
        query = self.asr.transcribe(voice)
        utils.rmdir(voice)
        logging.debug("listen: " + query)
        self.listening = ''
        return query


if __name__ == '__main__':
    """test"""
    # log init
    log_file = 'robot-' + str(os.getpid())
    utils.init_logging(log_file=log_file, log_path=CUR_PATH)
    print("log_file: {}".format(log_file))

    robot = Robot()
