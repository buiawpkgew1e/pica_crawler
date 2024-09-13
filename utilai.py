import os
import random
import zipfile
from configparser import ConfigParser
from datetime import datetime


def convert_file_name(name: str) -> str:
    # Windows的文件夹不能带特殊字符,需要处理下文件夹名
    replacements = {
        '/': '／', '\\': '＼', '?': '？', '|': '︱', '"': '＂', '*': '＊', '<': '＜', '>': '＞', ':': '-'
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    return name.replace(" ", "")


def get_cfg(section: str, key: str):
    parser = ConfigParser()
    parser.read('./config.ini', encoding='utf-8')
    return parser.get(section, key)


def get_latest_run_time():
    try:
        with open('./run_time_history.txt', 'r') as f:
            run_times = [line for line in f.read().splitlines() if line]
        return datetime.strptime(run_times[-1], '%Y-%m-%d %H:%M:%S')
    except (FileNotFoundError, IndexError, ValueError) as e:
        raise RuntimeError("Failed to get latest run time") from e


# 获取待下载的章节
def filter_comics(comic, episodes) -> list:
    try:
        with open('./downl.txt', 'r') as f:
            ids = set(f.read().split())
    except FileNotFoundError:
        ids = set()

    if comic["_id"] in ids:
        latest_run_time = get_latest_run_time()
        episodes = [i for i in episodes if (datetime.strptime(i['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ') - latest_run_time).total_seconds() > 0]

    categories_rule = os.getenv("CATEGORIES_RULE", "INCLUDE")
    categories = set(os.getenv("CATEGORIES", "").split(','))

    if categories:
        intersection = set(comic['categories']).intersection(categories)
        if (categories_rule == 'EXCLUDE' and not intersection) or (categories_rule == 'INCLUDE' and intersection):
            return episodes
        return []
    return episodes


def list_partition(ls, size):
    return [ls[i:i + size] for i in range(0, len(ls), size)]


def download(self, name: str, i: int, url: str):
    path = f'./comics/{convert_file_name(name)}/{str(i + 1).zfill(4)}.jpg'
    if os.path.exists(path):
        return

    try:
        with open(path, 'wb') as f:
            f.write(self.http_do("GET", url=url).content)
    except Exception as e:
        print(f"Failed to download file: {e}")


def generate_random_str(str_length=16):
    base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(base_str) for _ in range(str_length))


def zip_file(source_dir, target_dir, block_size=None):
    if not block_size:
        block_size = int(os.getenv("EMAIL_ATTACH_SIZE", 10)) - 1
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    size_Mbit = block_size * 1024 * 1024
    count = 1
    zip_files = {}

    try:
        file_size_temp = 0
        for dir_path, _, file_names in os.walk(source_dir):
            file_path = dir_path.replace(source_dir, "")
            file_path = file_path and file_path + os.sep or ''
            for file_name in file_names:
                file_size = os.path.getsize(os.path.join(dir_path, file_name))
                if file_size_temp + file_size > size_Mbit:
                    count += 1
                    file_size_temp = file_size
                else:
                    file_size_temp += file_size

                var_index = str(count).zfill(2)
                if var_index not in zip_files:
                    zip_files[var_index] = zipfile.ZipFile(os.path.join(target_dir, var_index + ".zip"), 'w', zipfile.ZIP_DEFLATED)
                zip_files[var_index].write(os.path.join(dir_path, file_name), file_path + file_name)
    finally:
        for zipf in zip_files.values():
            zipf.close()


def zip_subfolders(source_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for folder_name in os.listdir(source_dir):
        folder_path = os.path.join(source_dir, folder_name)
        if os.path.isdir(folder_path):
            zip_path = os.path.join(target_dir, folder_name + '.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, source_dir))
