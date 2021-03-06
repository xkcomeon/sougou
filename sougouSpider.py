# -*- coding:utf-8 -*-
"""
File Name : 'sougouSpider'.py 
Description:
Author: 'wanglongzhen' 
Date: '2016/12/26' '10:00'
"""

import time
import logging
import datetime
import sys
from bs4 import BeautifulSoup as bs
import traceback
import distinct
import pymssql
import random
import AES_Encrypt
import get_params
import json
import requests
import phonemarkDao
import proxy
import ConfigParser
import comm_log
import os
import random

reload(sys)
sys.setdefaultencoding('utf8')


class sougouSpider(object):
    def __init__(self, conf_path = 'db.conf'):
        """
        初始化
        """

        conf = ConfigParser.ConfigParser()
        conf.read(conf_path)
        self.redis_name = conf.get('redis', 'redis_name')

        #日志
        # logging.basicConfig(filename="output/sougou_spider.log",
        #                     level=logging.INFO,
        #                     filemode='a',
        #                     format='%(asctime)s - %(levelname)s: %(message)s')
        # self.log = logging.getLogger("requests")
        # self.log.setLevel(logging.WARNING)
        log_name = 'spider' + str(os.getpid())
        self.log = comm_log.comm_log(log_name)


        #redis
        self.pool, self.redis = distinct.redis_init()

        # SQL

        self.dbhost = conf.get('tagphonedb', 'host')
        self.dbname = conf.get('tagphonedb', 'database')
        self.dbusername = conf.get('tagphonedb', 'user')
        self.dbpasswd = conf.get('tagphonedb', 'passwd')

        # self.dbhost = "99.48.58.245"
        # self.dbname = "tagphone"
        # self.dbusername = "sa"
        # self.dbpasswd = "mime@123"

        try:
            self.conn = pymssql.connect(host=self.dbhost,
                                        database=self.dbname,
                                        user=self.dbusername,
                                        password=self.dbpasswd,
                                        charset="utf8")
        except Exception as e:
            self.conn = None
            self.log.info(u"连接数据库发生错误：" + str(e))
        else:
            self.log.info(u"成功连接到数据库!")


        self.header = {
            "Host": "data.haoma.sogou.com",
            "User-Agent": "Apache-HttpClient/UNAVAILABLE (java 1.4)",
            "Proxy-Switch-Ip" : "yes"
        }

        self.url = "http://data.haoma.sogou.com/query/super_search.php?v=1.2&parames={parames}"  # 需要计算parames
        self.hidlist = get_params.get_hidlist()

        self.aesfunc = AES_Encrypt.AES_Encrypt('Sogou$Haoma$Tong')

        # self.ses = requests.session()

        # self.proxy = proxy.Proxy()
        # self.proxy.initProxy()

    def being(self, body):
        self.log.info(u'开始处理数据, {0}'.format(body))
        try:
            # result = distinct.check_repeate(self.redis, body['phone'], self.redis_name)
            # # result = 1
            # if result == 1:
            #     pass
            # else:
            #     return True

            ret = self.get_info_from_sogou(body)
            #0成功，1失败，2代理返回429错误
            if ret == 0:
                return True
            elif ret == 2:
                self.log.info(u'请求过多，代理返回429错误, {0}'.format(body))
                return True
            elif ret == 1:
                return False
            else:
                return True
        except Exception, e:
            self.log.info(u'处理数据异常, 号码：{0}'.format(body))
            self.log.info(traceback.format_exc())
            return False

        self.log.info(u'处理数据完成, {0}'.format(body))
        return True

    def get_info_from_sogou(self, body):
        """
        任务爬取主要部分
        :param phone:
        :return:
        """
        try:

            n = random.randint(0, 300 - 1)
            m = random.choice([2 * n - 1, 2 * n])
            paramstr = self.hidlist[m]
            if paramstr is None:
                paramstr = random.choice(self.hidlist)

            data_enc = paramstr.format(phone=body['phone'])
            parames = self.aesfunc.encrypt(data_enc)
            url = self.url.format(parames=parames)
            ret = self.requesetGet(url)

            try:
                soup = bs(ret.text.encode(ret.encoding), 'html.parser')
            except Exception, e:
                # ip = self.proxy.getCurIp()
                self.log.error(u'转换页面数据失败，数据：{0}'.format(body))
                self.log.error(traceback.format_exc())

            ret_json = json.loads(self.aesfunc.decrypt(soup.text))

            result_json = ret_json.get("num_info")
            if result_json is None:
                # self.un_phones.append(body['phone'])
                self.log.info(u"此号码返回None：" + str(body['phone']))
                return 1
            location, cardtype, tagcontent, tagcount = result_json.get('place'), result_json.get(
                'tel_co'), result_json.get('tag'), result_json.get('amount')

            if tagcontent == '':
                source = ''
            else:
                source = 'sogou'

            try:
                if body['table'] == 'PHONEMARK_ALL_2016_10_31':
                    phonemark = phonemarkDao.PHONEMARK_TEST_2016_10_31(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())
                elif body['table'] == 'PHONEMARK_ALL_2016_08_23':
                    phonemark = phonemarkDao.PHONEMARK_TEST_2016_08_23(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())
                elif body['table'] == 'PHONEMARK_ALL_2016_08_15':
                    phonemark = phonemarkDao.PHONEMARK_TEST_2016_08_15(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())
                elif body['table'] == 'PHONEMARK_ALL_2016_06_12':
                    phonemark = phonemarkDao.PHONEMARK_TEST_2016_06_12(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())
                elif body['table'] == 'PHONEMARK_ALL_2016_05_30':
                    phonemark = phonemarkDao.PHONEMARK_TEST_2016_05_30(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())
                elif body['table'] == 'PHONEMARK_ALL_2016_05_18':
                    phonemark = phonemarkDao.PHONEMARK_TEST_2016_05_18(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())
                else:
                    phonemark = phonemarkDao.phonemark(phone=body['phone'], location=location, cardtype=cardtype,
                                                       tagcontent=tagcontent, tagcount=tagcount, source=source,
                                                       ctime=time.time())

                if hasattr(self, 'dao') == False:
                    self.dao = phonemarkDao.Dao()
                self.dao.add(phonemark)
            except Exception, e:
                self.log.error(u'抓取数据异常,{0}'.format(body))


        except Exception, e:
            self.log.error(traceback.format_exc())
            self.log.error(u'抓取数据异常,{0}'.format(body))
            return 1
        return 0

    def requesetGet(self, url):
        """
        统一管理request的get请求
        :param url:
        :return:
        """

        if hasattr(self, 'ses') == False:
            self.ses = requests.session()

        ret = None

        try:
            if hasattr(self, 'proxy') == False:
                self.proxy = proxy.proxy()

            retry_count = 1
            while True:
                ret = self.ses.get(url, proxies = self.proxy.getProxy())
                
                if ret.status_code == 429:
                    wait = random.randint(1, 3)
                    time.sleep(wait)
                    self.log.info(u'requesetGet, 请求代理超过5个，返回429{0}，随机等待{1}秒'.format(url, wait))
                    continue
                elif ret.status_code != 200 and retry_count < 3:
                    wait = random.randint(1, 3)
                    time.sleep(wait)
                    self.log.info(u'requesetGet, 请求失败，返回code:{2}, url:{0}，随机等待{1}秒'.format(url, wait, ret.status_code))
                    retry_count += 1
                    continue
                else:
                    break
        except:
            # ip = self.proxy.getCurIp()
            # self.log.error(u'代理请求数据异常, url:{0}, ip:{1}'.format(url, ip))
            self.log.error(u'代理请求数据异常, url:{0}'.format(url))
            self.log.error(traceback.format_exc())
        self.log.info(u'代理请求数据完成，url：{0}'.format(url))

        return ret

    def getProxy(self):
        # 要访问的目标页面
        # targetUrl = "http://test.abuyun.com/proxy.php"
        # targetUrl = "http://proxy.abuyun.com/switch-ip"
        targetUrl = "http://proxy.abuyun.com/current-ip"

        # 代理服务器
        proxyHost = "proxy.abuyun.com"
        proxyPort = "9010"

        # 代理隧道验证信息
        proxyUser = "H7SN5J89R653UHDP"
        proxyPass = "222E4A29D99B0499"

        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": proxyHost,
            "port": proxyPort,
            "user": proxyUser,
            "pass": proxyPass,
        }

        proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }

        # return proxies
        # resp = requests.get(targetUrl, proxies=proxies)
        #
        # print resp.status_code
        # print resp.text
        # print 'u'
        #
        # return proxies