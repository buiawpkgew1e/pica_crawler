# encoding: utf-8
import io
import json
import sys
import threading
import traceback
import logging
import os
import json
import threading
import functools

from client import Pica
from util import *

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')


# only_latest: true增量下载    false全量下载
def download_comic(comic, only_latest):
    """
    下载漫画
    :param comic: 漫画信息字典
    :param only_latest: 是否只下载最新一集
    """
    cid = comic["_id"]  # 漫画id
    title = comic["title"]  # 漫画标题
    author = comic["author"]  # 漫画作者
    categories = comic["categories"]  # 漫画分类
    episodes = p.episodes_all(cid)  # 获取漫画所有话数

    if only_latest:
        episodes = filter_comics(comic, episodes)  # 筛选需要下载的话数

    if not episodes:
        return  # 无话数可下载则直接返回

    logging.info(f"{cid} | {title} | {author} | {categories} | {only_latest}: downloading---------------------")

    pics = []  # 图片列表
    for eid in episodes:  # 遍历每个话数
        page = 1
        while True:
            docs = json.loads(p.picture(cid, eid["order"], page).content)["data"]["pages"]["docs"]  # 获取当前话数的图片列表
            page += 1
            if docs:  # 若有图片
                pics.extend(list(
                    map(lambda i: os.path.join(p.convert_file_name(title), i['media']['path']), docs)))  # 将图片路径添加到列表中
            else:
                break

    if not pics:
        return

    path = os.path.join('./comics', convert_file_name(title))  # 漫画文件夹路径
    if not os.path.exists(path):
        os.makedirs(path)

    pics_part = list_partition(pics, int(get_cfg('crawl', 'concurrency')))  # 将图片列表按指定数量划分为多个部分
    for part in pics_part:
        threads = []
        for pic in part:
            pic_path = os.path.join(path, pic)
            download_partial = functools.partial(download, p, title, pics.index(pic_path), pic_path)
            t = threading.Thread(target=download_partial)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        last = pics.index(part[-1]) + 1  # 计算已下载的图片数量
        percentage = int(last / len(pics) * 100)
        logging.info(f"downloaded:{last},total:{len(pics)},progress:{percentage}%")

    with open('./downl.txt', 'ab') as f:
        f.write((str(cid) + '\n').encode())


p = Pica()
p.login()
p.punch_in()

# 排行榜/收藏夹的漫画
comics = p.leaderboard()

# # 关键词订阅的漫画
keywords = os.environ["SUBSCRIBE_KEYWORD"].split(',')
for keyword in keywords:
    subscribe_comics = p.search_all(keyword)
    print('关键词%s : 订阅了%d本漫画' % (keyword, len(subscribe_comics)))
    comics += subscribe_comics

favourites = p.my_favourite()
print('id | 本子 | 画师 | 分区')

for comic in favourites + comics:
    try:
        # 收藏夹:全量下载  其余:增量下载
        download_comic(comic, comic not in favourites)
        info = p.comic_info(comic['_id'])
        if info["data"]['comic']['isFavourite']:
            p.favourite(comic["_id"])
    except:
        print('download failed,{},{},{}', comic['_id'], comic["title"], traceback.format_exc())
        continue

# 记录上次运行时间
f = open('./run_time_history.txt', 'ab')
f.write((str(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')) + '\n').encode())
f.close()
