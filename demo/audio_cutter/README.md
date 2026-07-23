# 音频切割工具

可视化波形切割工具，在波形图上点击即可设置切割点，拖动调整位置，一键导出分段音频。

## 依赖

- Python：`pip install -r requirements.txt`
- 系统：[FFmpeg](https://ffmpeg.org)（`winget install ffmpeg`）

## 运行

```bash
# GUI 模式（推荐）
python main.py

# CLI 命令行模式
python main.py cli -i 音频.mp3 -s 1:30,3:00
```

## 操作

| 操作 | 方式 |
|------|------|
| 📂 打开文件 | 点击「打开文件」按钮 |
| ✂️ 添加切割点 | 左键点击波形 |
| ↕️ 调整位置 | 拖动三角手柄 |
| ❌ 删除切割点 | 右键点击手柄 |
| ▶️ 预览片段 | 播放按钮 |
| 💾 导出 | 点击「导出分段」→ `output/` |
