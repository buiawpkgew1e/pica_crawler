import os
import shutil

from pip._vendor.distlib.compat import raw_input

path = './zips/'
if not os.path.exists(path):
    os.makedirs(path)

target = raw_input("目标目录：")
if not os.path.exists(path + target):
    os.makedirs(path + target)

target_files = os.listdir(path + target)
target_files.sort(key=lambda x: str(x.split('.')[0]))
index = 1 if not target_files else int(target_files[-1].split('.')[0]) + 1

dirs = os.listdir(path)
dirs.remove(target)
for d in dirs:
    pics = os.listdir(path + d)
    pics.sort(key=lambda x: str(x.split('.')[0]))

    source = path + d + '/'
    for p in pics:
        os.rename(source + p, path + target + '/' + str(index).zfill(4) + '.jpg')
        index += 1
    shutil.rmtree(source)
    print('merge finished, ' + d + ' removed------------------------------------')
