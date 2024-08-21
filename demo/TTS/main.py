#!/usr/bin/env python3
# 0 

"""
Basic example of edge_tts usage.
"""

import asyncio

import edge_tts

TEXT = "如果相遇的结果是分别的话，那相遇的意义就是，在相处的那段时间里被你改变的那一部分代替你永远陪着我"

VOICE_LIST = ["zh-CN-XiaoxiaoNeural", 'zh-CN-XiaoyiNeural', 'zh-CN-YunjianNeural', 'zh-CN-YunxiNeural',
              'zh-CN-YunxiaNeural', 'zh-CN-YunyangNeural', 'zh-CN-liaoning-XiaobeiNeural',
              'zh-CN-shaanxi-XiaoniNeural', 'zh-HK-HiuGaaiNeural', 'zh-HK-HiuMaanNeural', 'zh-HK-WanLungNeural',
              'zh-TW-HsiaoChenNeural', 'zh-TW-HsiaoYuNeural']
VOICE = VOICE_LIST[0]
OUTPUT_FILE_PATH = "./output/"


async def amain() -> None:
    """Main function"""
    communicate = edge_tts.Communicate(TEXT, VOICE, rate="-5%", pitch="-5Hz")
    await communicate.save(OUTPUT_FILE_PATH + TEXT + ".mp3")


if __name__ == "__main__":
    loop = asyncio.get_event_loop_policy().get_event_loop()
    print(loop)
    try:
        loop.run_until_complete(amain())
    finally:
        loop.close()
