#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: camera.py
Desc: 摄像头人脸识别基类
Author:yanjingang(yanjingang@mail.com)
Date: 2019/2/21 23:34
Cmd: 捕获摄像头中的人脸：      python face.py camera_face yan
     从目录图片中提取人脸：    python face.py path_face ~/Desktop/FACE/
     从指定图片中提取人脸：    python face.py image_face data/facedb/test/2.png
     从face目录生成训练数据：  python face.py train_data

     查询facedb id数量：       python face.py get_facedb
     使用facenet方式识别人脸： python face.py face_embedding

     # face_recognition
     识别人脸                   python face.py face_recognition
     捕获摄像头中的人脸          python face.py face_recognition_camera
                                    tail -f log/face_recognition_camera-* |grep catch
     分拣人脸图片到不同目录       python face.py face_sorting
                                    tail -f log/face_sorting-* |grep auto_sorting
"""

from dp.pygui import PySimpleGUI as sg
from dp import utils
import os
import sys
import time
import copy
import random
import logging
import cv2
import numpy as np
import face_recognition
from threading import Thread

# PATH
CUR_PATH = os.path.dirname(os.path.abspath(__file__))

# 最多保存人脸数量
MAX_FACE = 11


def show_camera_face_window(camera_data, warning_faceids=['mjs', 'zhu', 'yjy', 'zn']):
    """创建视频人脸监控windows窗口"""
    # create window
    face_imgs, face_labels = [], []
    for i in range(MAX_FACE):
        face_imgs.append(sg.Image(filename=CUR_PATH + '/data/image/kuang.png', size=(80, 80), key='face' + str(i)))
        face_labels.append(sg.Text('', size=(14, 1), key='label' + str(i)))
    layout = [
        [sg.Image(filename=CUR_PATH + '/data/image/pic.png', size=(600, 400), key='camera')],
        face_imgs,
        face_labels,
        [sg.Text('filename', size=(100, 1), key='filename')]
    ]
    window = sg.Window('视频人脸监控', return_keyboard_events=True, default_element_size=(30, 2), location=(0, 0), use_default_focus=False).Layout(layout).Finalize()
    # window.FindElement('filename').Update(str(time.time()))

    # show camera_data
    while True:
        event, values = window.Read(timeout=5)  # wait 5ms for a GUI event
        if event is None or event == 'Exit':  # exit
            break
        while True:  # 刷新页面数据
            logging.debug('___show_camera_face_window__')
            if camera_data['camera']['filename']:
                # print(camera_data['camera']['filename'])
                window.FindElement('camera').Update(filename=camera_data['camera']['filename'])
                window.FindElement('filename').Update(camera_data['camera']['filename'])
                try:
                    # show face
                    for i in range(len(camera_data['face']['list'])):
                        face = camera_data['face']['list'][i]
                        window.FindElement('face' + str(i)).Update(face['filename'])
                        window.FindElement('label' + str(i)).Update(face['faceid'] + ' ' + str(round(face['weight'] / face['cnt'], 3)))
                except:  # will get exception when Queue is empty
                    logging.warning('refresh window fail! {}'.format(utils.get_trace()))
                    break
                window.Refresh()
                # 重要人物刚出现时报警
                if len(camera_data['face']['list']) > 0 and time.time() - camera_data['face']['list'][-1]['lasttime'] < 2.0 and camera_data['face']['list'][-1]['faceid'] in warning_faceids:
                    # utils.play_sound('warning0.wav')
                    Thread(target=utils.play_sound, daemon=True).start()
            logging.debug('___show_camera_face_window__ done')

    # close window
    window.Close()


class Face():
    """人脸测试"""
    #DATA_PATH = CUR_PATH + "/data/"
    TEMP_PATH = CUR_PATH + "/data/tmp/"
    FACE_ID_PATH = CUR_PATH + "/data/facedb/faceid/"

    def __init__(self, faceid_path=None, temp_path=None):
        """初始化facedb"""
        if faceid_path is not None:
            self.FACE_ID_PATH = faceid_path
        if temp_path is not None:
            self.TEMP_PATH = temp_path
        self.facedb, self.facenames = [], []
        self.create_face_db(faceid_path=faceid_path)
        # 摄像头数据
        self.camera_data = {
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

    def create_face_db(self, faceid_path=None):
        """创建FaceDB字典"""
        if faceid_path is None:
            faceid_path = self.FACE_ID_PATH

        #self.facedb, self.facenames = [], []
        if os.path.exists(faceid_path) is False:
            return
        for img_file in os.listdir(faceid_path):
            if img_file in utils.TMPNAMES:
                continue
            image = face_recognition.load_image_file(faceid_path + img_file)
            emb = face_recognition.face_encodings(image)[0]
            tmp = img_file.split('.')
            faceid = tmp[0]
            facename = tmp[1] if len(tmp) > 2 else faceid
            self.facedb.append(emb)
            self.facenames.append({'id': faceid, 'name': facename})
            #print(faceid, emb)

    def register_faceid(self, face_img_file, name, faceid_path=None):
        """注册新的faceid"""
        faceid = utils.get_pinyin(name)
        if faceid_path is None:
            faceid_path = self.FACE_ID_PATH
        faceid_file = '{}/{}.{}.jpg'.format(faceid_path, faceid, name)
        if os.path.exists(faceid_file):
            utils.cp(faceid_file, faceid_file + '.bak')
        utils.cp(face_img_file, faceid_file)
        # reload
        self.create_face_db(faceid_path=faceid_path)
        return faceid

    def get_faceids(self, img_file=None, image=None, zoom=0.5):
        """计算指定图片中的人脸与facedb中各faceid的距离（距离越小越像, <0.6可以确信是同一个人, >1不可信）"""
        logging.info("__get_faceids__")
        faceids = []
        if image is None and img_file is None:
            logging.error("img_file and image params is empty!")
            return faceids

        if image is None:
            image = face_recognition.load_image_file(img_file)
        else:
            # (window_width, window_height, color_number) = image.shape
            # print("{},{},{}".format(window_width, window_height, color_number))
            if zoom < 1.0:
                small_frame = cv2.resize(image, (0, 0), fx=zoom, fy=zoom)
            else:
                small_frame = image
            # (window_width, window_height, color_number) = small_frame.shape
            # print("{},{},{}".format(window_width, window_height, color_number))
            image = small_frame[:, :, ::-1]
        logging.debug('___face_locations__')
        face_locations = face_recognition.face_locations(image)  # 此函数性能：zoom=1.0,1280*720=500ms; zoom=0.5, 640*360=120ms
        logging.debug('___face_encodings__')
        face_encodings = face_recognition.face_encodings(image, face_locations)

        for i in range(len(face_encodings)):
            face_encoding = face_encodings[i]
            faceid = "Unknown"
            facename = ""
            logging.debug('___face_distance__ {}'.format(i))
            distances = face_recognition.face_distance(self.facedb, face_encoding)
            weight = 0.0
            #print(self.facedb, distances)
            if distances is not None and len(distances) > 0:
                distances = list(distances)
                sort_distances = copy.deepcopy(distances)
                # print(sort_distances)
                sort_distances.sort()
                # print(sort_distances)
                weight = sort_distances[0]
                idx = distances.index(sort_distances[0])
                # print(idx)
                faceid = self.facenames[idx]['id']
                facename = self.facenames[idx]['name']
                # print(name)
            # rect
            top, right, bottom, left = face_locations[i]
            faceids.append({'faceid': faceid, 'facename': facename, 'weight': float(weight), 'rect': (left, top, right, bottom), 'distance': distances})

        logging.info("get faceids: {}".format(faceids))
        return faceids

    def get_camera_face(self, camera_id=0, camera_data=None, callback=show_camera_face_window):
        """捕获摄像头中的人脸 - 使用自定义window展示"""
        if camera_data is None:
            camera_data = self.camera_data
        # open camera
        self.video_capture = cv2.VideoCapture(camera_id)

        # clear tmp file
        utils.rmdir(self.TEMP_PATH)
        utils.mkdir(self.TEMP_PATH)

        # 后台异步线程-更新摄像头当前数据
        Thread(target=self._get_camera_face_image, args=(camera_data, 20), daemon=True).start()
        # 后台异步线程-清理摄像头临时数据
        Thread(target=self._clear_tmp_path, args=(camera_data, 2000), daemon=True).start()

        # 创建视频人脸监控windows窗口，展示摄像头当前数据
        if callback is not None:
            callback(camera_data)

        # close camera
        if callback is not None:
            self.video_capture.release()

    def _get_camera_face_image(self, camera_data, run_freq=100, zoom=0.5):
        """更新摄像头当前数据"""
        i = -1
        while True:
            logging.debug('___get_camera_face_image__')
            i += 1
            time.sleep(run_freq / 1000)
            # get cap
            ret, image = self.video_capture.read()
            # logging.debug('___get_camera_face_image__ 0')
            # print(ret)
            if ret is False:
                logging.warning("video_capture.read: {} {}".format(ret, image))
                return
            # get faceid
            camera_data['camera']['faceids'] = self.get_faceids(image=image)
            # logging.debug('___get_camera_face_image__ 1')
            # show
            for face in camera_data['camera']['faceids']:
                faceid = face['faceid'] if face['weight'] < 0.5 else 'unknown'  # 只保留距离<0.5的可信face
                facename = face['facename'] if face['weight'] < 0.5 else 'unknown'  # 只保留距离<0.5的可信face
                left, top, right, bottom = face['rect']
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top = int(top * 1 / zoom)
                right = int(right * 1 / zoom)
                bottom = int(bottom * 1 / zoom)
                left = int(left * 1 / zoom)
                size = bottom - top
                # 人脸计数
                catch_data = camera_data['face']['catch']
                sec_max_cnt = round((1.1 - zoom) * 10, 2)  # 每秒的最多捕获face次数（与face_locations性能有关）
                check_cnt = sec_max_cnt if sec_max_cnt > 1 else sec_max_cnt + 1  # 最少2次才能入队列
                if faceid not in catch_data or time.time() - catch_data[faceid]['lasttime'] > zoom * 3 or catch_data[faceid]['cnt'] >= check_cnt * 1.5:  # 如果此face上次出现距离本次已查超过n s则重置
                    catch_data[faceid] = {'faceid': faceid, 'facename': facename, 'weight': face['weight'], 'size': size, 'cnt': 1, 'lasttime': time.time(), 'filename': ''}
                else:
                    catch_data[faceid]['cnt'] += 1
                    catch_data[faceid]['weight'] += face['weight']
                    catch_data[faceid]['size'] += size
                    catch_data[faceid]['lasttime'] = time.time()
                # 放入队列
                avg_weight = round(catch_data[faceid]['weight'] / catch_data[faceid]['cnt'], 4)
                avg_size = round(catch_data[faceid]['size'] / catch_data[faceid]['cnt'], 2)
                logging.info("catch: {} {} {} {} {} {}".format(faceid, catch_data[faceid]['cnt'], check_cnt, size, avg_size, avg_weight))
                if (catch_data[faceid]['cnt'] >= check_cnt * 2 and faceid == 'unknown') or \
                        (catch_data[faceid]['cnt'] >= check_cnt and avg_weight < 0.35) or \
                        (catch_data[faceid]['cnt'] >= check_cnt and avg_size >= 200 and avg_weight < 0.4) or \
                        (catch_data[faceid]['cnt'] >= check_cnt and 200 > avg_size >= 150 and avg_weight < 0.43) or \
                        (catch_data[faceid]['cnt'] >= check_cnt and 150 > avg_size >= 100 and avg_weight < 0.47) or \
                        (catch_data[faceid]['cnt'] >= check_cnt * 1.5 and avg_size < 100 and avg_weight < 0.49):  # 连续cnt次被识别，避免偶发错误识别（注意cnt和weight设置与zoom参数有关，zoom=1.0每秒最多2张，zoom=0.5每秒最多6张）
                    logging.info('face catched!  {} {} {}'.format(faceid, avg_size, avg_weight))
                    # logging.debug('___get_camera_face_image__ 1.1')
                    # TODO:检查眨眼
                    # 保存人脸照片
                    if catch_data[faceid]['filename'] == '' or i % 10 == 0:
                        face_file = '{}/face-{}-{}-{}.png'.format(self.TEMP_PATH, faceid, round(avg_weight, 2), int(time.time() * 1000))
                        face_image = image[top:bottom, left:right]
                        face_image = cv2.resize(face_image, (80, 80), interpolation=cv2.INTER_CUBIC)
                        cv2.imwrite(face_file, face_image)
                        catch_data[faceid]['filename'] = face_file
                    if len(camera_data['face']['list']) > 0 and camera_data['face']['list'][-1]['faceid'] == faceid:  # 如果尾部跟当前是一个人脸，重置此人图像
                        camera_data['face']['list'][-1] = catch_data[faceid]
                        logging.info('reset last self !!! ')
                    else:
                        # clear old data
                        for j in range(len(camera_data['face']['list']) - 1, -1, -1):
                            if camera_data['face']['list'][j]['faceid'] == faceid:
                                logging.info('clear old data !!! ')
                                camera_data['face']['list'].pop(j)
                        # append
                        camera_data['face']['list'].append(catch_data[faceid])
                        if len(camera_data['face']['list']) > MAX_FACE:  # 定长
                            logging.info('max face pop !!! {}'.format(len(camera_data['face']['list'])))
                            camera_data['face']['list'].pop(0)

                # 画边框
                # logging.debug('___get_camera_face_image__ 1.2')
                cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
                # 加face标注
                # if catch_data[faceid]['cnt'] > check_cnt * 0.5:
                # logging.debug('___get_camera_face_image__ 1.3')
                cv2.putText(image, '{} {}'.format(faceid, round(face['weight'], 2)), (left + 6, top + 12), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 0), 1)

            # 保存摄像头照片
            # logging.debug('___get_camera_face_image__ 2')
            img_file = '{}/camera-{}.png'.format(self.TEMP_PATH, int(time.time() * 1000))
            image = cv2.resize(image, (0, 0), fx=0.798, fy=0.798)
            # logging.debug('___get_camera_face_image__ 3')
            cv2.imwrite(img_file, image)
            # update
            camera_data['camera']['filename'] = img_file
            # print(camera_data)
            logging.debug('___get_camera_face_image__ done')

    def _clear_tmp_path(self, camera_data, sleep=1000):
        """清理摄像头临时数据"""
        while True:
            logging.debug('___clear_tmp_path__')
            time.sleep(sleep / 1000)
            # get used filelist
            skips = []
            for face in camera_data['face']['list']:
                skips.append(face['filename'])
            # clear
            for file in os.listdir(self.TEMP_PATH):
                # print(float(file.split('-')[-1].split('.')[0]) / 1000)
                timeout = 60.0 * 60 * 24 if file.count('face') > 0 else 30.0  # camera 30s,face 24h
                if self.TEMP_PATH + '/' + file not in skips and time.time() - float(file.split('-')[-1].split('.')[0]) / 1000 > timeout:  # 30s前的无用临时照片清理
                    os.unlink(self.TEMP_PATH + '/' + file)
                    logging.debug('clear tmp file: {}'.format(file))
            logging.debug('___clear_tmp_path__ done')

    def face_sorting(self, extract_path, output_path):
        """按faceid自动分拣face到不同目录（建议调用此函数前，先进行照片extract face提取）
            Params:
                extract_path:要分拣的face文件目录
                output_path: 分拣结果输出位置
            Demo:
                faceid_path = Face.FACE_DB_PATH + 'faceid_test/'  # 每个人物取一个face图片放到此目录用于分类
                face_reco = Face(faceid_path)
                face_reco.face_sorting(extract_path, output_path)
        """
        i = 0
        for file in os.listdir(extract_path):
            i += 1
            source_file = extract_path + file
            if file in utils.TMPNAMES or os.path.exists(source_file) is False:
                continue
            faceids = self.get_faceids(source_file)
            if len(faceids) == 0:
                logging.info("auto_sorting faceid not found: {}".format(source_file))
                continue
            faceid = faceids[0]['faceid']
            target_file = output_path + faceid + '/' + file
            utils.mkdir(output_path + faceid)
            ret = utils.move_file(source_file, target_file)
            logging.info("auto_sorting face file {}: {} {}  {} -> {}".format(i, faceid, round(faceids[0]['weight'], 2), source_file, target_file))
            # break


if __name__ == '__main__':
    """test"""
    # log init
    log_file = 'face-' + str(os.getpid())
    utils.init_logging(log_file=log_file, log_path=CUR_PATH)
    print("log_file: {}".format(log_file))

    face_reco = Face()
    face_reco.get_camera_face()
