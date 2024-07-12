import os
from ffmpy3 import FFmpeg
import subprocess

def export_mp3(filepath, output_dir):
    filename = os.listdir(filepath)
    print("待处理的视频文件:")
    print(filename)
    print("\n")
    # 读取上次已导出的音频文件名（防止多次运行，出现overwrited的错误）
    exit_filename = os.listdir(output_dir)
    print("已导出的音频文件: ")
    print(exit_filename)
    for i in range(len(filename)):
        changefile = filepath + "/" + filename[i]
        change_postfix_name =filename[i].replace('mp4', 'mp3').replace('flv', 'mp3') # 另外的视频格式请自行添加
        outputfile = output_dir + "/" + change_postfix_name
        if change_postfix_name in exit_filename:
            continue
         # 利用FFmpeg进行转换
        fpg = FFmpeg(inputs={changefile: None},
            outputs={outputfile: '-vn -ar 44100 -ac 2 -ab 192 -f mp3'}
        )
        subprocess.check_call(fpg.cmd, shell=True)
        
    print("\n任务完成！！！")

if __name__ == "__main__":
    # filepath：待处理视频的文件路径
    filepath = "E:/素材/python测试/video"
    # output_dir：输出音频文件的路径
    output_dir = "E:/素材\python测试/mp3"
    export_mp3(filepath, output_dir)
