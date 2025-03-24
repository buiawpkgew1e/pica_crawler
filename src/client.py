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
        """初始化Pica客户端，设置会话和请求头"""
        self.__s = requests.session()
        self.__s.verify = False
        parser = ConfigParser()
        parser.read('./config/config.ini', encoding='utf-8')
        self.headers = dict(parser.items('header'))
        self.timeout = int(get_cfg("crawl", "request_time_out", 10))
        self.__s.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
        self.__s.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    def http_do(self, method: str, url: str, **kwargs) -> requests.Response:
        """执行HTTP请求，添加必要的认证信息
        
        Args:
            method: HTTP请求方法
            url: 请求URL
            **kwargs: 请求的其他参数
            
        Returns:
            requests.Response: HTTP响应对象
            
        Raises:
            requests.exceptions.RequestException: 当请求失败时抛出
        """
        try:
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
            proxies = {'http': proxy, 'https': proxy} if proxy else None
            
            response = self.__s.request(
                method=method,
                url=url,
                verify=False,
                proxies=proxies,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP请求失败: {url}, 错误: {str(e)}")
            raise

    def login(self) -> None:
        """登录并获取认证token
        
        Raises:
            Exception: 当登录失败或认证失败时抛出
        """
        try:
            url = base + "auth/sign-in"
            send = {
                "email": get_cfg('param', 'pica_account'),
                "password": get_cfg('param', 'pica_password')
            }
            response = self.http_do("POST", url=url, json=send)
            response_data = response.json()
            
            if response_data["code"] != 200:
                raise Exception('PICA_ACCOUNT/PICA_PASSWORD ERROR')
            if 'token' not in response.text:
                raise Exception('PICA_SECRET_KEY ERROR')
                
            self.headers["authorization"] = response_data["data"]["token"]
            logging.info("登录成功")
        except Exception as e:
            logging.error(f"登录失败: {str(e)}")
            raise

    def comics(self, block: str = "", tag: str = "", order: str = "", page: int = 1) -> dict:
        """获取漫画列表
        
        Args:
            block: 分区
            tag: 标签
            order: 排序方式
            page: 页码
            
        Returns:
            dict: 漫画列表数据
        """
        try:
            args = []
            if block:
                args.append(("c", block))
            if tag:
                args.append(("t", tag))
            if order:
                args.append(("s", order))
            if page > 0:
                args.append(("page", str(page)))
                
            params = urlencode(args)
            url = f"{base}comics?{params}"
            response = self.http_do("GET", url)
            return response.json()
        except Exception as e:
            logging.error(f"获取漫画列表失败: {str(e)}")
            return {"data": {"comics": []}}

    # 排行榜
    def leaderboard(self) -> list:
        """获取排行榜数据
        
        Returns:
            list: 排行榜漫画列表
        """
        try:
            # tt的可选值: H24, D7, D30   分别代表每天/周/月
            args = [("tt", 'H24'), ("ct", 'VC')]
            params = urlencode(args)
            url = f"{base}comics/leaderboard?{params}"
            
            response = self.http_do("GET", url)
            return response.json()["data"]["comics"]
        except Exception as e:
            logging.error(f"获取排行榜数据失败: {str(e)}")
            return []

    def comic_info(self, book_id: str) -> dict:
        """获取漫画详细信息
        
        Args:
            book_id: 漫画ID
            
        Returns:
            dict: 漫画详细信息
            
        Raises:
            Exception: 当获取信息失败时抛出
        """
        try:
            url = f"{base}comics/{book_id}"
            response = self.http_do("GET", url=url)
            return response.json()
        except Exception as e:
            logging.error(f"获取漫画信息失败: {book_id}, 错误: {str(e)}")
            return {"data": {"comic": {}}}

    def episodes(self, book_id: str, current_page: int) -> requests.Response:
        """获取漫画章节信息，每页最多40条
        
        Args:
            book_id: 漫画ID
            current_page: 当前页码
            
        Returns:
            requests.Response: HTTP响应对象
            
        Raises:
            requests.exceptions.RequestException: 当请求失败时抛出
        """
        try:
            url = f"{base}comics/{book_id}/eps?page={current_page}"
            return self.http_do("GET", url=url)
        except Exception as e:
            logging.error(f"获取章节信息失败: {book_id}, 页码: {current_page}, 错误: {str(e)}")
            raise

    def episodes_all(self, book_id: str, title: str) -> list:
        """获取漫画的所有章节信息
        
        Args:
            book_id: 漫画ID
            title: 漫画标题
            
        Returns:
            list: 所有章节信息列表
        """
        episode_list = []
        try:
            first_page_data = self.episodes(book_id, current_page=1).json()
            if 'data' not in first_page_data:
                logging.info(f'漫画章节信息缺失，可能已被删除: {title}, {book_id}')
                return []

            total_pages = first_page_data["data"]["eps"]["pages"]
            total_episodes = first_page_data["data"]["eps"]["total"]
            episode_list = list(first_page_data["data"]["eps"]["docs"])
            
            # 获取剩余页面的章节信息
            for page in range(2, total_pages + 1):
                try:
                    page_data = self.episodes(book_id, page).json()
                    additional_episodes = page_data["data"]["eps"]["docs"]
                    episode_list.extend(list(additional_episodes))
                except Exception as e:
                    logging.error(f"获取第{page}页章节信息失败: {title}, 错误: {str(e)}")
                    continue
            
            # 按章节顺序排序
            episode_list = sorted(episode_list, key=lambda x: x['order'])
            
            # 验证章节数量
            if len(episode_list) != total_episodes:
                logging.warning(
                    f"章节数量不匹配: {title}, 预期: {total_episodes}, 实际: {len(episode_list)}"
                )
        except KeyError as e:
            logging.error(f"漫画数据缺失: {title}, KeyError: {e}")
        except Exception as e:
            logging.error(f"获取全部章节失败: {title}, 错误: {str(e)}")
            
        return episode_list

    def picture(self, book_id: str, ep_id: str, page: int = 1) -> requests.Response:
        """获取章节的图片信息
        
        Args:
            book_id: 漫画ID
            ep_id: 章节ID
            page: 页码
            
        Returns:
            requests.Response: HTTP响应对象
            
        Raises:
            requests.exceptions.RequestException: 当请求失败时抛出
        """
        try:
            url = f"{base}comics/{book_id}/order/{ep_id}/pages?page={page}"
            return self.http_do("GET", url=url)
        except Exception as e:
            logging.error(f"获取图片信息失败: 漫画ID {book_id}, 章节ID {ep_id}, 页码 {page}, 错误: {str(e)}")
            raise

    def search(self, keyword: str, page: int = 1, sort: str = Order_Latest) -> dict:
        """搜索漫画
        
        Args:
            keyword: 搜索关键词
            page: 页码
            sort: 排序方式
            
        Returns:
            dict: 搜索结果
        """
        url = f"{base}comics/advanced-search?page={page}"
        try:
            res = self.http_do("POST", url=url, json={"keyword": keyword, "sort": sort})
            return json.loads(res.content.decode("utf-8"))["data"]["comics"]
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"搜索解析失败: {keyword}, 错误: {str(e)}")
            return {"docs": [], "pages": 0}

    def search_all(self, keyword: str) -> list:
        """搜索所有符合条件的漫画
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            list: 符合条件的漫画列表
        """
        subscribed_comics = []
        if not keyword:
            return subscribed_comics
            
        try:
            total_pages_num = self.search(keyword)["pages"]
            subscribe_days = int(get_cfg('filter', 'subscribe_days'))
            
            for current_page in range(1, total_pages_num + 1):
                page_docs = self.search(keyword, current_page)["docs"]
                if not page_docs:
                    break
                    
                # 使用生成器表达式优化内存使用
                recent_comics = [
                    comic for comic in page_docs
                    if (datetime.now() - datetime.strptime(
                        comic["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                    )).days <= subscribe_days
                ]
                
                subscribed_comics.extend(recent_comics)
                
                # 如果当前页面有不符合时间条件的漫画，提前结束搜索
                if len(page_docs) != len(recent_comics):
                    break
                    
        except Exception as e:
            logging.error(f"搜索全部漫画失败: {keyword}, 错误: {str(e)}")
            
        return subscribed_comics

    def categories(self):
        url = f"{base}categories"
        return self.http_do("GET", url=url)

    def favourite(self, book_id: str) -> requests.Response:
        """收藏或取消收藏漫画
        
        Args:
            book_id: 漫画ID
            
        Returns:
            requests.Response: HTTP响应对象
            
        Raises:
            requests.exceptions.RequestException: 当请求失败时抛出
        """
        try:
            url = f"{base}comics/{book_id}/favourite"
            response = self.http_do("POST", url=url)
            response.raise_for_status()
            return response
        except Exception as e:
            logging.error(f"收藏操作失败: 漫画ID {book_id}, 错误: {str(e)}")
            raise

    def my_favourite(self, page: int = 1) -> dict:
        """获取收藏夹中的漫画（分页）
        
        Args:
            page: 页码
            
        Returns:
            dict: 收藏的漫画列表数据
        """
        try:
            url = f"{base}users/favourite?page={page}"
            response = self.http_do("GET", url=url)
            return response.json()["data"]["comics"]
        except Exception as e:
            logging.error(f"获取收藏夹分页数据失败: 页码 {page}, 错误: {str(e)}")
            return {"docs": [], "pages": 0}

    def my_favourite_all(self) -> list:
        """获取收藏夹中的所有漫画
        
        Returns:
            list: 所有收藏的漫画列表
        """
        comics = []
        try:
            first_page = self.my_favourite()
            pages = first_page['pages']
            comics.extend(first_page["docs"])
            
            for page in range(2, pages + 1):
                try:
                    page_comics = self.my_favourite(page)
                    comics.extend(page_comics["docs"])
                except Exception as e:
                    logging.error(f"获取收藏夹第{page}页数据失败: {str(e)}")
                    continue
        except Exception as e:
            logging.error(f"获取全部收藏夹数据失败: {str(e)}")
            
        return comics

    def punch_in(self) -> dict:
        """用户打卡
        
        Returns:
            dict: 打卡结果
            
        Raises:
            requests.exceptions.RequestException: 当请求失败时抛出
        """
        try:
            url = f"{base}/users/punch-in"
            response = self.http_do("POST", url=url)
            result = response.json()
            logging.info("打卡成功")
            return result
        except Exception as e:
            logging.error(f"打卡失败: {str(e)}")
            raise

