# encoding: utf-8
import io
import json
import os
import sys
import threading

from client import Pica
from util import *

# 将标准输出的编码设置为utf8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')


def download_comic(comic):
    """
    下载单个漫画
    :param comic: 漫画信息
    """
    cid = comic["_id"]
    title = comic["title"]
    author = comic["author"]
    categories = comic["categories"]
    print('%s | %s | %s | %s: 正在下载...' % (cid, title, author, categories))
    res = []
    episodes = p.episodes_all(cid)
    for eid in episodes:
        page = 1
        while True:
            try:
                # 获取漫画的图片信息
                docs = json.loads(p.picture(cid, eid["order"], page).content)["data"]["pages"]["docs"]
                page += 1
                if docs:
                    res.extend(docs)
                else:
                    break
            except Exception as e:
                print('获取漫画图片信息失败:', e)
                continue
    pics = list(map(lambda i: i['media']['fileServer'] + '/static/' + i['media']['path'], res))

    # 如果没有获取到图片，则直接返回
    if not pics:
        return

    # 创建漫画保存的目录
    path = './comics/' + convert_file_name(title) + '/'
    if not os.path.exists(path):
        os.makedirs(path)

    # 将图片列表分成多个部分，每个部分使用一个线程下载
    pics_part = list_partition(pics, int(get_cfg('crawl', 'concurrency')))
    for part in pics_part:
        threads = []
        for pic in part:
            t = threading.Thread(target=download, args=(p, title, pics.index(pic), pic))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        last = pics.index(part[-1]) + 1
        print("已下载:%d,总共:%d,进度:%s%%" % (last, len(pics), int(last / len(pics) * 100)))

    # 记录已下载过的漫画id
    try:
        with open('./downl.txt', 'a', encoding='utf-8') as f:
            f.write(str(cid) + '\n')
    except Exception as e:
        print('记录已下载漫画id失败:', e)


# 创建Pica客户端对象并登录
p = Pica()
p.login()
p.punch_in()

# 获取需要下载的漫画列表
comics = filter_comics(p.leaderboard()) + p.my_favourite()
keywords = os.environ["SUBSCRIBE_KEYWORD"].split(',')
for keyword in keywords:
    subscribe_comics = filter_comics(p.search_all(keyword))
    print('关键词%s : 订阅了%d本漫画' % (keyword, len(subscribe_comics)))
    comics += subscribe_comics

# 下载漫画并收藏
print('id | 本子 | 画师 | 分区')
for index, comic in enumerate(comics):
    try:
        download_comic(comic)
        info = p.comic_info(comic['_id'])
        if info["data"]['comic']['isFavourite']:
            p.favourite(comic["_id"])
    except Exception as e:
        print('下载漫画失败:', e)
        continue

# 压缩漫画文件夹
if not os.path.exists("./comics"):
    os.mkdir('./comics')
if not os.path.exists("./zips"):
    os.mkdir('./zips')
zip_file("./comics", "./zip", sys.maxsize)
