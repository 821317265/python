# -#!/usr/local/bin/python
# # -*- coding: utf8 -*-
import asyncio, aiohttp
import requests
from Crypto.Cipher import AES
import re
import time
import sys
import os
from lxml import etree

"""

网站地址，属于m3u8的地址抓出啦：验证地址是否存在，不存在返回错误，
1：首先得到M3U8文件，解码出需要的.ts地址
2：异步IO请求N个.ts地址
"""
sem = asyncio.Semaphore(33)  # 请求上线设置


async def get_url(url):
    async with sem:
        async with aiohttp.ClientSession()as session:
            # print('发出请求的URL：', url)
            try:
                async with session.get(url)as response:
                    if response.status in [200, 201]:
                        data = await response.read()
                        return data
                    else:
                        return False
            except Exception as e:
                async with session.get(url)as response:
                    if response.status in [200, 201]:
                        data = await response.read()
                        return data
                print('错误原因:', e)


async def download_ts(result):
    global COUNT
    name = '0'*(6-len(result[2]))+result[2]+'.ts'
    path = 'D://AllDownload//临时存储//'+name             # 临时存储位置。后面会清空
    content = await get_url(result[0])
    if content:
        if result[1]:
            cryptors = AES.new(result[1], AES.MODE_CBC, result[1])
            content = cryptors.decrypt(content)
        with open(path, 'wb')as f:
            f.write(content)
        COUNT += 1
        print('\r'+'当前文件下载进度：{:.4%}'.format(COUNT/result[3]), end='')
    else:
        with open(temporary+'download.json', 'a+') as f:
            f.writelines(name+result[0])
            f.close()
        print('下载出错，NAME：%s   URL：%s' % (name, result[0]))


def handle_m3u8(m3u8_url):              # 处理M3U8文件，找出KEY和.TS文件地址。并返回
    ts_url_list = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 \
    (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0'}
    response = requests.get(m3u8_url, headers=headers).text
    sql = re.compile(r"URI=\"(.*?\.key)\"", re.M)
    key_key = sql.search(response)
    if key_key:                          # 如果KEY存在，再请求，否则KEY为FALSE
        key_url = m3u8_url.rsplit('/', 1)[0]+'/'+key_key.group(1)
        key = requests.get(key_url, headers=headers).content
    else:
        key = False
    sql = re.compile(r'(.*?\.ts.*?)\n', re.M)
    ts_name_list = sql.findall(response)
    # print(ts_name_list)
    if ts_name_list:                    # 如果存在.ts结尾的文件。
        if not'http' in ts_name_list:   # 不是完整的URL，需要拼接.
            for each_url in ts_name_list:
                new_url = m3u8_url.rsplit('/', 1)[0] + '/'+each_url
                ts_url_list.append(new_url)
        else:                           # 完整的URL不需要拼接
            ts_url_list = ts_name_list
    else:                               # 不存在.ts结尾的文件 。应该存在完整的http。找出来
        sql = re.compile(r"http.+", re.M)
        ts_url_list = sql.findall(response)
    result = [ts_url_list, key]
    print(result)
    return result


def run(result, name, int_max=0):
    start = time.time()
    tasks = []
    i = 0
    all_file_count = len(result[0])
    if int_max:           # 启动继续下载的时候。改变
        i = int_max
        result[0] = result[0][i:]
        print('继续下载：')
    for url in result[0]:
        task = asyncio.ensure_future(download_ts((url, result[1], str(i), all_file_count))) #使用asyncio.future(未来对象)发出去的请求是有序的。
        # task = download_ts((url, reslut[1], str(i)))
        tasks.append(task)
        i += 1
    time.sleep(1)
    print('tasks放入完成，没启动loop')
    loop = asyncio.get_event_loop()
    time.sleep(2)
    print('加载loop，没启动')
    loop.run_until_complete(asyncio.wait(tasks))
    # path = r"copy /b Z:\\Temporary\\*.ts D:\\downloads\\44.mp4"
    path = r"copy /b D:\\AllDownload\\临时存储\\*.ts D:\\AllDownload\\TsFile\\" + name     # D://AllDownload//临时存储
    os.system(path)
    del_ts = "del D:\\AllDownload\\临时存储\\*.ts"
    os.system(del_ts)
    end = time.time()
    print('总共消耗时间：', end-start)


def real_m3u8(url):             # 追溯真实的M3U8地址，并返回.
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 \
    (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0'}
    response = requests.get(url, headers=headers).text
    if 'EXT-X-TARGETDURATION' in response:  # 存在则说明。是真实的M3U8地址。返回
        print('真实的m3u8地址。返回')
        return url
    else:
        splicing = response.split('\n')[-1]
        print(splicing)
        new_url = url.rsplit('/', 1)[0]+'/'+splicing
        print('不是真实m3u8。继续寻找', new_url)
        result = real_m3u8(new_url)
        return result


def manage_http(http):   # 传入所有http地址，return all_m3u8
    new_http = []
    m3u8_list = []
    name = []
    for each in http:    # 去重
        if each not in new_http:
            new_http.append(each)
    print(new_http)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 \
    (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0'}
    for each in new_http:
        response = requests.get(url=each, headers=headers).text
        html = etree.HTML(response)
        title = html.xpath('//head/title/text()')[0]+'.ts'
        title = re.sub(r':|\?|/|\\|<|>|\*|\"|\||[\t]|[ ]', '', title)    # 将标题去掉文件名不能带的符号，用来网页标题充当文件名
        similar_m3u8 = re.findall(r'(http.*?m3u8.*?)[\"\']', response, re.M)  # 找出含m3u8的http地址
        if not similar_m3u8:         # 如果当前网页没有m3u8地址。返回空。
            print('当前网页下没有m3u8地址。出错啦！！:URL:%s' % each)
            break
        m3u8_url = re.sub(r'(\\+|/+)+', '/', similar_m3u8[0]).replace('/', '//', 1)  # 将地址进行改变变成http://qe/qwe/.m3u8
        name.append(title)
        m3u8_list.append(m3u8_url)

    result = [m3u8_list, name]
    print(result)
    return result


def plan(name_and_count, download_file_count):
    global COUNT                    # 下载完一个视频，清空完成下载文件数量
    COUNT = 0
    print('已下载文件：{}'.format(download_file_count))
    for each in range(0, download_file_count):
        print(name_and_count[1][each])
    print('当前进度：{:.2%}'.format(download_file_count/len(name_and_count[1])))


def main():
    http = [


            'https://zmee22.com/video/show/id/36047',


            ]
    # url = 'https://video.lllwo2o.com:8091/20180510/pacopacomama_101114_266/650kb/hls/index.m3u8'
    m3u8_list = init_one(http)   # 返回全部网页的m3u8地址，片名 ，续下载值。
    count = 0                       # 计数从m3u8_list 提取相应的影片名字

    for each in m3u8_list[0]:

        m3u8_url = real_m3u8(each)       # 追溯真实的M3U8地址，并返回.
        result = handle_m3u8(m3u8_url)          # 处理M3U8文件，找出KEY和所有.TS文件地址。并返回

        if not result:              # M3U8文件为空。没有地址
            print('当前%s地址无效!' % each)
            count += 1               # 片名+1
            break
        log_download(m3u8_url)
        run(result, m3u8_list[1][count], m3u8_list[2])      # 第二个参数是片名。第一个参数是.ts地址和KEY,第三个参数是继续下载值
        count += 1
        m3u8_list[2] = 0
        init_log_download()
        plan(m3u8_list, count)             # 总计划。计数当前下载了多少个文件


def init():
    global download_path
    global temporary
    if not download_path:
        download_path = 'D://'
    if temporary:
        temporary = 'D://AllDownload//临时存储//'  # 先这样勉强用着。意思意思init


def init_one(url):   # 第二个初始化。0.检查输入数据。1.去重 2.检查是m3u8地址还是http地址 3. http地址的话，读取文件名再次去重。4. 临时文件夹是否空。是否续下载。
    check_input_data(url)
    url = quchong(url)
    if jiancha_m3u8_or_http(url):  # 当输入的地址http地址时：
        result = manage_http(url)
        result = quchong_file(result)
        int_max = continue_download(result)
        return [result[0], result[1], int_max]  # 返回所有m3u8地址,片名,续下载值
    else:
        name = []
        for each in url:
            name.append(each.split('/')[-2]+'.ts')
        result = [url, name]
        int_max = continue_download(result)
        return [result[0], result[1], int_max]


def check_input_data(url):  # 检查输入数据，随便意思意思，谁吃饱没事乱输入，出错的时候他会自己检查地址。。可以考虑用正则检查，以后再说
    if '.m3u8' in url[0]:
        for each in url:
            if '.m3u8' not in each:
                print('不要输入混合地址，即m3u8跟http混合在一起。请分开下载。。')
                sys.exit(0)
    else:
        for each in url:
            if '.m3u8' in each:
                print('不要输入混合地址，即m3u8跟http混合在一起。请分开下载。。')
                sys.exit(0)
    return True


def quchong(data):
    result = []
    for each in data:
        if each not in result:
            result.append(each)
    return result


def jiancha_m3u8_or_http(url):

    for each in url:
        if '.m3u8' in each:
            return False
        else:
            return True


def quchong_file(url_and_name):
    all_file = os.listdir(download_path)
    print(all_file)
    new_all_file = []
    index = 0
    for each in all_file:
        if each != each.split('.', 1)[0]:
            new_all_file.append(each.split('.', 1)[0])
    for each_one in url_and_name[1]:
        if each_one in new_all_file:
            url_and_name[1].remove(each_one)
            url_and_name[0].pop(index)
        index += 1

    if not url_and_name[0]:
        print('所以文件貌似都下载过了。请确认地址')
        sys.exit(0)
    print('文件没有下载过')
    return url_and_name


def continue_download(url_and_name):  # 判断是否启动断点续下载
    global COUNT
    if len(os.listdir(temporary)) < 50:
        print('ts文件<50 不启动断点下载')
        return False
    else:
        int_max = int(os.listdir(temporary)[-2][:-3]) - 30
        with open(temporary+'download.json', 'r') as f:
            data = f.readline()

            f.close()
        data = data.split('.m3u8', 1)[0]
        m3u8 = real_m3u8(url_and_name[0][0])
        if data in m3u8:
            print('继续下载')
            COUNT = int_max
            return int_max
        else:
            print('虽然有临时文件，但是不同于当前要下载的文件，所以不启动续下载')
        return False


def log_download(url):    # 记录当前下载m3u8的第一个url
    with open(temporary+'download.json', 'w+') as f:
        f.write(url)
        f.close()
    print('记录下当前下文件的第一个url')

    return True


def init_log_download():
    with open(temporary+'download.json', 'w+') as f:
        f.write('')
        f.close()


if __name__ == '__main__':
    download_path = 'D:/AllDownload/TsFile/'
    temporary = 'D:/AllDownload/临时存储/'
    init()
    COUNT = 0                       # 计数，计算下载完成了多少个文件，用来显示当前下载进度在:def download_ts 中使用
    main()

