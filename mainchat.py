import io
import json
import os
import sys
import threading

from client import Pica
from util import *

# 配置参数
DOWNLOAD_PATH = './comics/'
DOWNLOAD_FILE = './downl.txt'
ZIP_PATH = './zips/'
CONCURRENCY = int(get_cfg('crawl', 'concurrency'))
SUBSCRIBE_KEYWORD = os.environ.get('SUBSCRIBE_KEYWORD', '').split(',')

# 初始化输出流
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

# 下载漫画
def download_comic(p, comic):
    cid = comic['_id']
    title = comic['title']
    author = comic['author']
    categories = comic['categories']
    print(f'{cid} | {title} | {author} | {categories}: downloading---------------------')
    res = []
    episodes = p.episodes_all(cid)
    for eid in episodes:
        page = 1
        while True:
            docs = json.loads(p.picture(cid, eid['order'], page).content)['data']['pages']['docs']
            page += 1
            if docs:
                res.extend(docs)
            else:
                break
    pics = [i['media']['fileServer'] + '/static/' + i['media']['path'] for i in res]

    # todo pica服务器抽风了,没返回图片回来,有知道原因的大佬麻烦联系下我
    if not pics:
        return

    path = DOWNLOAD_PATH + convert_file_name(title) + '/'
    if not os.path.exists(path):
        os.makedirs(path)
    pics_part = list_partition(pics, CONCURRENCY)
    for part in pics_part:
        threads = []
        for pic in part:
            t = threading.Thread(target=download, args=(p, title, pics.index(pic), pic))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        last = pics.index(part[-1]) + 1
        print(f"downloaded:{last},total:{len(pics)},progress:{int(last / len(pics) * 100)}%")
    # 记录已下载过的id
    with open(DOWNLOAD_FILE, 'ab') as f:
        f.write(f'{cid}\n'.encode())

# 初始化pica客户端
p = Pica()
p.login()
p.punch_in()

# 获取漫画列表
comics = filter_comics(p.leaderboard()) + p.my_favourite()
for keyword in SUBSCRIBE_KEYWORD:
    subscribe_comics = filter_comics(p.search_all(keyword))
    print(f'关键词{keyword} : 订阅了{len(subscribe_comics)}本漫画')
    comics += subscribe_comics

# 下载漫画并收藏
for comic in comics:
    try:
        print('id | 本子 | 画师 | 分区')
        download_comic(p, comic)
        info = p.comic_info(comic['_id'])
        if info['data']['comic']['isFavourite']:
            p.favourite(comic['_id'])
    except KeyError:
        print(f'download failed,{comic}')
        continue

# 压缩漫画文件夹
if not os.path.exists(DOWNLOAD_PATH):
    os.mkdir(DOWNLOAD_PATH)
if not os.path.exists(ZIP_PATH):
    os.mkdir(ZIP_PATH)
zip_file(DOWNLOAD_PATH, ZIP_PATH, sys.maxsize)
