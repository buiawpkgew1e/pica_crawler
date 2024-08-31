# encoding: utf-8
import io
import json
import sys
import threading
import time
import traceback
import shutil
import requests

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
    # 增量更新
    if only_latest:
        episodes = filter_comics(comic, episodes)  # 筛选需要下载的话数
    if episodes:
        print('%s | %s | %s | %s | %s:downloading---------------------' % (cid, title, author, categories,only_latest), flush=True)  # 打印下载信息
    else:
        return  # 无话数可下载则直接返回

    pics = []  # 图片列表
    for eid in episodes:  # 遍历每个话数
        page = 1
        while True:
            docs = json.loads(p.picture(cid, eid["order"], page).content)["data"]["pages"]["docs"]  # 获取当前话数的图片列表
            page += 1
            if docs:  # 若有图片
                pics.extend(list(map(lambda i: i['media']['fileServer'] + '/static/' + i['media']['path'], docs)))  # 将图片路径添加到列表中
            else:
                break

    # todo pica服务器抽风了,没返回图片回来,有知道原因的大佬麻烦联系下我
    if not pics:  # 若无图片则直接返回
        return

    path = './comics/' + convert_file_name(title) + '/'  # 漫画文件夹路径
    if not os.path.exists(path):  # 若文件夹不存在则创建
        os.makedirs(path)
    pics_part = list_partition(pics, int(get_cfg('crawl', 'concurrency')))  # 将图片列表按指定数量划分为多个部分
    for part in pics_part:  # 遍历每个图片部分
        threads = []  # 线程列表
        for pic in part:  # 遍历每个图片
            t = threading.Thread(target=download, args=(p, title, pics.index(pic), pic))  # 创建下载线程
            threads.append(t)
            t.start()
        for t in threads:  # 等待所有线程下载完成
            t.join()
        last = pics.index(part[-1]) + 1  # 计算已下载的图片数量
        print("downloaded:%d,total:%d,progress:%s%%" % (last, len(pics), int(last / len(pics) * 100)), flush=True)  # 打印下载进度
    # 记录已下载过的id
    f = open('./downl.txt', 'ab')
    f.write((str(cid) + '\n').encode())
    f.close()
    # 下载每本漫画的间隔时间
    if os.environ.get("INTERVAL_TIME"):
        time.sleep(int(os.environ.get("INTERVAL_TIME")))

# 登录并打卡
p = Pica()
p.login()
p.punch_in()

# 排行榜的漫画
comics = p.leaderboard()

# 关键词订阅的漫画
keywords = os.environ.get("SUBSCRIBE_KEYWORD", "").split(',')
for keyword in keywords:
    subscribe_comics = p.search_all(keyword)
    print('关键词%s : 订阅了%d本漫画' % (keyword, len(subscribe_comics)), flush=True)
    comics += subscribe_comics

# 收藏夹的漫画
favourites = p.my_favourite_all()
print('收藏夹共计%d本漫画' % (len(favourites)), flush=True)
print('id | 本子 | 画师 | 分区', flush=True)

for comic in favourites + comics:
    try:
        # 收藏夹:全量下载  其余:增量下载
        download_comic(comic, comic not in favourites)
        info = p.comic_info(comic['_id'])
        # 收藏夹中的漫画被下载后,自动取消收藏,避免下次运行时重复下载
        if info["data"]['comic']['isFavourite']:
            p.favourite(comic["_id"])
    except:
        print('download failed,{},{},{}', comic['_id'], comic["title"], traceback.format_exc(), flush=True)
        continue

# 记录上次运行时间
f = open('./run_time_history.txt', 'ab')
f.write((str(datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')) + '\n').encode())
f.close()

# 打包成zip文件, 并删除旧数据 , 删除comics文件夹会导致docker挂载报错
if os.environ.get("PACKAGE_TYPE", "False") == "True":
    zip_subfolders('./comics', './output')
    for filename in os.listdir('./comics'):
        file_path = os.path.join('./comics', filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

# 发送消息通知
if os.environ.get("BARK_URL"):
    requests.get(os.environ.get("BARK_URL"))