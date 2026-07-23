# 文字转语音 (TTS)

基于 Microsoft Edge TTS 引擎，将文字合成为自然语音 MP3。

## 运行

1. 安装依赖：`pip install -r requirements.txt`
2. 修改 `base_tts.py` 中的参数：
   - `TEXT`：要合成的文字
   - `VOICE`：语音角色（支持多种中文语音）
   - `OUTPUT_FILE_PATH`：输出目录
3. 运行：`python base_tts.py`
