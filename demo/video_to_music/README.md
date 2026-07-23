# 视频转音频

将视频文件批量转换为 MP3 音频。

## 依赖

- Python：`pip install -r requirements.txt`
- 系统：[FFmpeg](https://ffmpeg.org)（`winget install ffmpeg`）

## 运行

1. 修改 `main.py` 中的路径：
   - `filepath`：视频文件目录
   - `output_dir`：音频输出目录
2. 运行：`python main.py`
3. 会自动跳过已转换的文件，避免重复覆盖
