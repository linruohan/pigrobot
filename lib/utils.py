# -*- coding: utf-8-*-

import os
import tempfile
import wave
import shutil
import re
import time
import hashlib
from . import constants, config
from pydub import AudioSegment
from pytz import timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from robot import logging
from dp import utils as util

logger = logging.getLogger(__name__)

do_not_bother = False


def emailUser(SUBJECT="", BODY="", ATTACH_LIST=[]):
    """
    给用户发送邮件

    :param SUBJECT: subject line of the email
    :param BODY: body text of the email
    :returns: True: 发送成功; False: 发送失败
    """
    # add footer
    if BODY:
        BODY = u"%s，<br><br>这是您要的内容：<br>%s<br>" % (config['first_name'], BODY)

    recipient = config.get('/email/address', '')
    robot_name = config.get('robot_name_cn', 'wukong-robot')
    recipient = robot_name + " <%s>" % recipient
    user = config.get('/email/address', '')
    password = config.get('/email/password', '')
    server = config.get('/email/smtp_server', '')
    port = config.get('/email/smtp_port', '')

    if not recipient or not user or not password or not server or not port:
        return False
    try:
        util.send_mail(SUBJECT, BODY, ATTACH_LIST, user, user,
                       recipient, password, server, port)
        return True
    except Exception as e:
        logger.error(e)
        return False


def clean():
    """ 清理垃圾数据 """
    temp = constants.TEMP_PATH
    temp_files = os.listdir(temp)
    for f in temp_files:
        if os.path.isfile(os.path.join(temp, f)) and re.match(r'output[\d]*\.wav', os.path.basename(f)):
            os.remove(os.path.join(temp, f))


def is_proper_time():
    """ 是否合适时间 """
    if do_not_bother == True:
        return False
    if not config.has('do_not_bother'):
        return True
    bother_profile = config.get('do_not_bother')
    if not bother_profile['enable']:
        return True
    if 'since' not in bother_profile or 'till' not in bother_profile:
        return True
    since = bother_profile['since']
    till = bother_profile['till']
    current = time.localtime(time.time()).tm_hour
    if till > since:
        return current not in range(since, till)
    else:
        return not (current in range(since, 25) or
                    current in range(-1, till))


def get_do_not_bother_on_hotword():
    """ 打开勿扰模式唤醒词 """
    return config.get('/do_not_bother/on_hotword', '悟空别吵.pmdl')


def get_do_not_bother_off_hotword():
    """ 关闭勿扰模式唤醒词 """
    return config.get('/do_not_bother/off_hotword', '悟空醒醒.pmdl')


def getTimezone():
    """ 获取时区 """
    return timezone(config.get('timezone', 'HKT'))
