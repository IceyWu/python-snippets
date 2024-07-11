import os
import shutil
import re


def rename_file(file_name):
    regex_result = re.findall(r'_(.*?)#', file_name[19:])
    print(file_name, regex_result)
    # 获取文件后缀
    file_suffix = os.path.splitext(file_name)[1]
    if len(regex_result) > 1:
        return regex_result[0] + file_suffix
    else:
        return file_name


def move_files(src_dir, dst_dir):
    if not os.path.exists(src_dir):
        print("源目录不存在")
        return
    if not os.path.exists(dst_dir):
        print("目标目录不存在")
        return
    for file in os.listdir(src_dir):
        if os.path.isfile(os.path.join(src_dir, file)):
            if os.path.splitext(file)[1] in filterList:
                dst_file = os.path.join(dst_dir, rename_file(file))
                shutil.copy(os.path.join(src_dir, file), dst_file)
        else:
            move_files(os.path.join(src_dir, file), dst_dir)


if __name__ == "__main__":
    src_dir = "D:\\MyDev\\test\\a" # 获取的文件夹
    dst_dir = "D:\\MyDev\\test\\b" # 目标文件夹
    # 筛选列表
    filterList = [".mp3"]
    move_files(src_dir, dst_dir)
    print("过滤完成")
