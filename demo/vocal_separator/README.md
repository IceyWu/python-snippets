# 人声分离

基于 Meta demucs 模型，将音频/视频中的人声与背景音乐分离。

## 依赖

```bash
pip install -r requirements.txt
```
系统需安装 [FFmpeg](https://ffmpeg.org)：`winget install ffmpeg`

## 运行

```bash
# GUI 模式（推荐）
python main.py

# CLI 命令行模式
python main.py cli -i 歌曲.mp3
python main.py cli -i input/ -o output/ -m mdx_extra
```

## GUI 操作

1. 选择输入文件（单个或多个）或文件夹
2. 选择分离模型（默认 htdemucs）
3. 点击「开始分离」
4. 日志区实时显示进度，完成后输出到 `output/htdemucs/<文件名>/`

首次运行会自动下载模型（约 84MB）。
