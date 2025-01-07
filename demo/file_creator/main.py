import os
import openpyxl

# 创建文件
def creat_files(file_dir, name_list, suffix):
    for name in name_list:
        file_name = os.path.join(file_dir, name + suffix)
        if not os.path.exists(file_name):
            wb = openpyxl.Workbook()
            wb.save(file_name)
            print("生成文件：", file_name)
        else:
            print("文件已存在")
            return

# 读取txt文件内容
def read_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]

if __name__ == "__main__":
    file_dir = "D:\\MyDev\\test\\xlsx" # 获取的文件夹
    txt_file_path = "D:\\MyDev\\test\\name_list.txt" # txt文件路径
    name_list = read_txt(txt_file_path)
    # 后缀
    suffix = ".xlsx"
   
    creat_files(file_dir, name_list, suffix)
    print("生成完成")