import io
import json
import os
import sys
import traceback
import logging
import configparser
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from util import *
from client import Pica

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
DOWNLOAD_PATH = config.get('Paths', 'download_path')
ZIP_PATH = config.get('Paths', 'zip_path')
CONCURRENCY = int(config.get('Crawler', 'concurrency'))
SUBSCRIBE_KEYWORDS = config.get('Subscribe', 'keywords').split(',')

def initialize_pica():
    p = Pica()
    p.login()
    p.punch_in()
    return p

def filter_comics(comic, episodes):
    # 根据需求实现增量更新逻辑
    pass

def download_picture(p, comic, pics, index, pic_url):
    try:
        # ... 实现具体的图片下载逻辑 ...
        logging.info(f"Downloaded: {pic_url}")
    except Exception as e:
        logging.error(f"Download failed for {pic_url}: {e}")

    last = len(pics) if isinstance(index, Exception) else index + 1
    progress = f"{last}/{len(pics)} ({int(last / len(pics) * 100)}%)"
    logging.info(f"Download Progress: {progress}")

def download_comic(p, comic, only_latest=False):
    cid = comic['_id']
    title = comic['title']
    author = comic['author']
    categories = comic['categories']

    logging.info(f"{cid} | {title} | {author} | {categories}| {only_latest}: downloading---------------------")

    episodes = p.episodes_all(cid)
    if only_latest:
        episodes = filter_comics(comic, episodes)

    pics = []
    for eid in episodes:
        page = 1
        while True:
            docs = json.loads(p.picture(cid, eid['order'], page).content)['data']['pages']['docs']
            page += 1
            if docs:
                pics.extend(list(map(lambda i: i['media']['fileServer'] + '/static/' + i['media']['path'], docs)))
            else:
                break

    if not pics:
        logging.warning("No pictures found for comic: %s", title)
        return

    path = os.path.join(DOWNLOAD_PATH, convert_file_name(title))
    os.makedirs(path, exist_ok=True)

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        future_to_index = {executor.submit(download_picture, p, comic, pics, idx): idx for idx, pic in enumerate(pics)}
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            future.result()  # 如果有异常，这里会再次抛出

    with open('downl.txt', 'a') as f:
        f.write(f'{cid}\n'.encode())

def main():
    p = initialize_pica()

    comics = p.leaderboard()
    for keyword in SUBSCRIBE_KEYWORDS:
        subscribe_comics = p.search_all(keyword)
        logging.info(f'关键词{keyword} : 订阅了{len(subscribe_comics)}本漫画')
        comics.extend(subscribe_comics)

    favourites = p.my_favourite()

    for comic in favourites + comics:
        try:
            logging.info('id | 本子 | 画师 | 分区')
            download_comic(p, comic, comic not in favourites)
            info = p.comic_info(comic['_id'])

            if info['data']['comic']['isFavourite']:
                p.favourite(comic["_id"])
        except KeyError as e:
            logging.error('download failed,%s,%s,%s', comic['_id'], comic["title"], traceback.format_exc())
            continue

if __name__ == "__main__":
    main()
