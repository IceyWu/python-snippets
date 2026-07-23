# 视频截取

从视频文件中截取指定时间段，输出为新视频。

## 运行

1. 安装依赖：`pip install -r requirements.txt`
2. 修改 `main.py` 中的参数：
   - `video_path`：源视频目录
   - `result_video_path`：输出目录
   - `video`：源视频文件名（不含后缀）
   - `result_video`：输出文件名（不含后缀）
   - `start_time` / `end_time`：截取起止时间（秒）
3. 运行：`python main.py`
