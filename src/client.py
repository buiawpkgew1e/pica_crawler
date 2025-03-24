import hashlib
import hmac
import json
import os
from configparser import ConfigParser
from datetime import datetime
from time import time
from urllib.parse import urlencode
import logging

import requests
import urllib3
from util import get_cfg

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base = "https://picaapi.picacomic.com/"


class Pica:
    Order_Default = "ua"  # 默认
    Order_Latest  = "dd"  # 新到旧
    Order_Oldest  = "da"  # 旧到新
    Order_Loved   = "ld"  # 最多爱心
    Order_Point   = "vd"  # 最多指名

    def __init__(self) -> None:
        self.__s = requests.session()
        self.__s.verify = False
        parser = ConfigParser()
        parser.read('./config/config.ini', encoding='utf-8')
        self.headers = dict(parser.items('header'))
        self.timeout = int(get_cfg("crawl", "request_time_out", 10))

    def http_do(self, method, url, max_retries=3, **kwargs):
        """执行HTTP请求，包含重试机制和错误处理

        Args:
            method (str): HTTP方法(GET/POST等)
            url (str): 请求URL
            max_retries (int, optional): 最大重试次数. Defaults to 3.
            **kwargs: 其他请求参数

        Returns:
            Response: requests响应对象

        Raises:
            Exception: 请求失败且重试次数用尽时抛出异常
        """
        kwargs.setdefault("allow_redirects", True)
        header = self.headers.copy()
        ts = str(int(time()))
        raw = url.replace(base, "") + str(ts) + header["nonce"] + method + header["api-key"]
        hc = hmac.new(get_cfg("param", "pica_secret_key").encode(), digestmod=hashlib.sha256)
        hc.update(raw.lower().encode())
        header["signature"] = hc.hexdigest()
        header["time"] = ts
        kwargs.setdefault("headers", header)
        proxy = get_cfg("param", "request_proxy")
        if proxy:
            proxies = {'http': proxy, 'https': proxy}
        else:
            proxies = None

        for retry in range(max_retries):
            try:
                response = self.__s.request(
                    method=method, url=url, verify=False,
                    proxies=proxies, timeout=self.timeout, **kwargs
                )
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                logging.warning(f"Request timeout for {url}, attempt {retry + 1} of {max_retries}")
                if retry == max_retries - 1:
                    raise
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed for {url}: {str(e)}, attempt {retry + 1} of {max_retries}")
                if retry == max_retries - 1:
                    raise
            time.sleep(1 * (retry + 1))  # 指数退避重试

    def login(self):
        url = base + "auth/sign-in"
        send = {
            "email": get_cfg('param', 'pica_account'), 
            "password": get_cfg('param', 'pica_password')
        }
        response = self.http_do("POST", url=url, json=send).text
        print("login response:{}".format(response), flush=True)
        if json.loads(response)["code"] != 200:
            raise Exception('PICA_ACCOUNT/PICA_PASSWORD ERROR')
        if 'token' not in response:
            raise Exception('PICA_SECRET_KEY ERROR')
        self.headers["authorization"] = json.loads(response)["data"]["token"]

    def comics(self, block="", tag="", order="", page=1):
        args = []
        if len(block) > 0:
            args.append(("c", block))
        if len(tag) > 0:
            args.append(("t", tag))
        if len(order) > 0:
            args.append(("s", order))
        if page > 0:
            args.append(("page", str(page)))
        params = urlencode(args)
        url = f"{base}comics?{params}"
        return self.http_do("GET", url).json()

    # 排行榜
    def leaderboard(self) -> list:
        # tt的可选值: H24, D7, D30   分别代表每天/周/月
        args = [("tt", 'H24'), ("ct", 'VC')]
        params = urlencode(args)
        url = f"{base}comics/leaderboard?{params}"
        res = self.http_do("GET", url)
        return json.loads(res.content.decode("utf-8"))["data"]["comics"]

    # 获取本子详细信息
    def comic_info(self, book_id):
        url = f"{base}comics/{book_id}"
        res = self.http_do("GET", url=url)
        return json.loads(res.content.decode())

    # 获取本子的章节 一页最大40条
    def episodes(self, book_id, current_page):
        url = f"{base}comics/{book_id}/eps?page={current_page}"
        return self.http_do("GET", url=url)

    def episodes_all(self, book_id: str, title: str) -> list:
        """获取漫画的所有章节信息

        Args:
            book_id (str): 漫画ID
            title (str): 漫画标题

        Returns:
            list: 章节信息列表，每个元素包含章节的详细信息
                 如果获取失败则返回空列表
        """
        episode_list = []
        try:
            # 获取第一页数据以及总页数信息
            first_page_data = self.episodes(book_id, current_page=1).json()
            if not first_page_data.get('data'):
                logging.warning(f'漫画章节信息缺失，可能已被删除: {title}(ID:{book_id})')
                return []

            eps_data = first_page_data['data']['eps']
            total_pages = eps_data['pages']      # 总页数
            total_episodes = eps_data['total']   # 总章节数
            episode_list = list(eps_data['docs'])

            # 获取剩余页面的章节数据
            for page in range(total_pages, 1, -1):
                try:
                    page_data = self.episodes(book_id, page).json()
                    additional_episodes = page_data['data']['eps']['docs']
                    episode_list.extend(list(additional_episodes))
                except (KeyError, requests.exceptions.RequestException) as e:
                    logging.error(f'获取漫画{title}第{page}页章节失败: {str(e)}')
                    continue

            # 按章节顺序排序
            episode_list = sorted(episode_list, key=lambda x: x['order'])

            # 验证章节完整性
            if len(episode_list) != total_episodes:
                logging.warning(
                    f'漫画{title}章节数量不匹配: 期望{total_episodes}章, 实际获取{len(episode_list)}章'
                )

        except KeyError as e:
            logging.error(f'漫画{title}数据结构异常: {str(e)}')
        except requests.exceptions.RequestException as e:
            logging.error(f'获取漫画{title}章节信息失败: {str(e)}')
        except Exception as e:
            logging.error(f'获取漫画{title}章节时发生未知错误: {str(e)}')

        return episode_list

    # 根据章节获取图片
    def picture(self, book_id, ep_id, page=1):
        url = f"{base}comics/{book_id}/order/{ep_id}/pages?page={page}"
        return self.http_do("GET", url=url)

    def search(self, keyword, page=1, sort=Order_Latest):
        url = f"{base}comics/advanced-search?page={page}"
        res = self.http_do("POST", url=url, json={"keyword": keyword, "sort": sort})
        return json.loads(res.content.decode("utf-8"))["data"]["comics"]

    def search_all(self, keyword: str) -> list:
        """搜索所有匹配关键词的漫画

        Args:
            keyword (str): 搜索关键词

        Returns:
            list: 匹配的漫画列表
        """
        comics = []
        if not keyword:
            logging.warning('搜索关键词为空，返回空列表')
            return comics

        try:
            # 获取总页数
            first_page_result = self.search(keyword)
            total_pages = first_page_result['pages']
            comics.extend(first_page_result['docs'])

            # 获取剩余页面的数据
            for page in range(2, total_pages + 1):
                try:
                    page_docs = self.search(keyword, page)['docs']
                    comics.extend(page_docs)
                except (KeyError, requests.exceptions.RequestException) as e:
                    logging.error(f'获取第{page}页搜索结果失败: {str(e)}')
                    continue

        except (KeyError, requests.exceptions.RequestException) as e:
            logging.error(f'搜索漫画失败，关键词: {keyword}, 错误: {str(e)}')
        except Exception as e:
            logging.error(f'搜索漫画时发生未知错误，关键词: {keyword}, 错误: {str(e)}')

        return comics
                recent_comics = [comic for comic in page_docs if
                    (
                        (
                            datetime.now() - 
                            datetime.strptime(comic["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        ).days
                    ) <= int(get_cfg('filter', 'subscribe_days'))]
                subscribed_comics += recent_comics

                # Check if any comics in the current page exceed the subscribe time limit.
                # If there are any comics that do not meet the time criteria, it is assumed
                # that subsequent pages will also contain outdated comics, so the search
                # is stopped early to save unnecessary requests.
                if len(page_docs) != len(recent_comics):
                    break

        return subscribed_comics

    def categories(self):
        url = f"{base}categories"
        return self.http_do("GET", url=url)

    # 收藏/取消收藏本子
    def favourite(self, book_id):
        url = f"{base}comics/{book_id}/favourite"
        return self.http_do("POST", url=url)

    # 获取收藏夹-分页
    def my_favourite(self, page=1):
        url = f"{base}users/favourite?page={page}"
        res = self.http_do("GET", url=url)
        return json.loads(res.content.decode())["data"]["comics"]

    # 获取收藏夹-全部
    def my_favourite_all(self):
        comics = []
        pages = self.my_favourite()["pages"]
        for page in range(1, pages + 1):
            comics += self.my_favourite(page)["docs"]
        return comics

    # 打卡
    def punch_in(self):
        url = f"{base}/users/punch-in"
        res = self.http_do("POST", url=url)
        return json.loads(res.content.decode())
