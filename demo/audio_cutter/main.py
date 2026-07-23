"""
音频切割工具 —— 可视化界面版

在波形图上点击即可设置切割点，拖动调整位置，一键导出分段音频。

依赖：
  pip install customtkinter
  （系统需安装 FFmpeg）

用法：
  python main.py          → 打开 GUI 界面
  python main.py cli ...  → 命令行模式（向下兼容）
"""

import os
import sys
import subprocess
import struct
import threading
import customtkinter as ctk

# 确保 FFmpeg 在 PATH 中（Windows 下 GUI 进程可能不继承终端 PATH）
if sys.platform == "win32":
    for scope in ["Machine", "User"]:
        try:
            env_path = subprocess.run(
                ["powershell", "-Command",
                 f"[Environment]::GetEnvironmentVariable('Path','{scope}')"],
                capture_output=True, text=True
            ).stdout.strip()
            if env_path:
                for p in env_path.split(";"):
                    if p and p not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = p + ";" + os.environ.get("PATH", "")
        except Exception:
            pass


# ── FFmpeg 工具函数 ───────────────────────────────────────

def get_duration(filepath: str) -> float:
    """获取音频时长（秒）。"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", filepath
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return float(r.stdout.strip()) if r.returncode == 0 else 0


def get_waveform_data(filepath: str, num_bars: int = 800) -> list:
    """提取音频波形数据（归一化到 0~1）。"""
    cmd = [
        "ffmpeg", "-i", filepath, "-f", "s16le", "-ac", "1",
        "-ar", "8000", "-", "-y"
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 2:
        return [0.5] * num_bars

    samples = struct.unpack(f"<{len(r.stdout) // 2}h", r.stdout)
    if len(samples) < num_bars:
        return [0.5] * num_bars

    chunk = len(samples) // num_bars
    peaks = []
    for i in range(num_bars):
        seg = samples[i * chunk:(i + 1) * chunk]
        peak = max(abs(min(seg)), abs(max(seg))) / 32768
        peaks.append(peak)
    return peaks


def cut_segment(input_path: str, output_path: str, start_sec: float, duration_sec: float):
    cmd = [
        "ffmpeg", "-ss", str(start_sec), "-i", input_path,
        "-t", str(duration_sec), "-c", "copy", "-y", output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def fmt_time(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


# ── GUI 主体 ──────────────────────────────────────────────

SEGMENT_COLORS = ["#c084fc", "#4fc3f7", "#ffb74d", "#81c784", "#f472b6", "#4dd0e1"]
HANDLE_SIZE = 10  # 切割手柄三角形大小
RULER_H = 24      # 时间标尺高度
BOTTOM_PAD = 28   # 底部留白给段标签


class AudioCutterApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.win = ctk.CTk()
        self.win.title("音频切割工具")
        self.win.geometry("1000x640")
        self.win.minsize(750, 480)

        self.audio_path: str = ""
        self.duration: float = 0
        self.waveform: list = []
        self.split_points: list[float] = []
        self.playing = False
        self.play_proc = None
        self.current_time: float = 0
        self.play_timer_id = None
        self.drag_idx: int = -1
        self.dragging_playhead: bool = False
        self.hover_time: float = -1

        # ── 顶部栏 ──
        top = ctk.CTkFrame(self.win, fg_color="#1e1e2e", corner_radius=0, height=48)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="🎵 音频切割", font=ctk.CTkFont(size=16, weight="bold"),
                      text_color="#e94560").pack(side="left", padx=16, pady=10)

        self.file_label = ctk.CTkLabel(top, text="拖拽音频文件到窗口或点击打开",
                                        text_color="#666", font=ctk.CTkFont(size=12))
        self.file_label.pack(side="left", padx=8)

        ctk.CTkButton(top, text="📂 打开文件", width=100, height=30,
                       fg_color="#2b2b3d", hover_color="#3d3d55",
                       command=self.open_file).pack(side="right", padx=(0, 8), pady=9)

        ctk.CTkButton(top, text="↩ 撤销上一个", width=100, height=30,
                       fg_color="#3d2020", hover_color="#552828",
                       command=self.undo_last_point).pack(side="right", padx=(0, 4), pady=9)

        ctk.CTkButton(top, text="🗑 全部清除", width=90, height=30,
                       fg_color="#2b2b3d", hover_color="#3d3d55",
                       command=self.clear_points).pack(side="right", padx=(0, 4), pady=9)

        # ── 波形区域 ──
        self.canvas = ctk.CTkCanvas(self.win, bg="#12121a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=(12, 12), pady=(8, 0))

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_hover)
        self.canvas.bind("<Configure>", self.redraw)
        self.win.bind("<Control-z>", lambda e: self.undo_last_point())

        # ── 底部控制栏 ──
        bottom = ctk.CTkFrame(self.win, fg_color="#1e1e2e", corner_radius=0, height=56)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        self.btn_play = ctk.CTkButton(bottom, text="▶ 播放", width=80, height=32,
                                       fg_color="#2b2b3d", hover_color="#3d3d55",
                                       command=self.toggle_play)
        self.btn_play.pack(side="left", padx=(16, 4), pady=12)

        # 快退快进
        ctk.CTkButton(bottom, text="⏪ -5s", width=50, height=28,
                       fg_color="#2b2b3d", hover_color="#3d3d55",
                       command=lambda: self.seek_to(max(0, self.current_time - 5))
                       ).pack(side="left", padx=2, pady=12)
        ctk.CTkButton(bottom, text="⏩ +5s", width=50, height=28,
                       fg_color="#2b2b3d", hover_color="#3d3d55",
                       command=lambda: self.seek_to(min(self.duration, self.current_time + 5))
                       ).pack(side="left", padx=(2, 8), pady=12)

        self.time_label = ctk.CTkLabel(bottom, text="0:00 / 0:00",
                                        font=ctk.CTkFont(size=14), text_color="#aaa")
        self.time_label.pack(side="left", padx=(0, 16))

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(bottom, width=200, height=8,
                                                fg_color="#2b2b3d", progress_color="#e94560")
        self.progress_bar.pack(side="left", padx=(0, 16), pady=24)
        self.progress_bar.set(0)

        self.info_label = ctk.CTkLabel(bottom, text="打开音频文件开始",
                                        text_color="#555", font=ctk.CTkFont(size=11))
        self.info_label.pack(side="left", expand=True)

        self.segment_count_label = ctk.CTkLabel(bottom, text="", text_color="#888")
        self.segment_count_label.pack(side="right", padx=(0, 8))

        self.btn_cut = ctk.CTkButton(bottom, text="✂ 导出分段", width=110, height=32,
                                      fg_color="#1b9b4e", hover_color="#178a43",
                                      command=self.do_cut, state="disabled")
        self.btn_cut.pack(side="right", padx=(0, 16), pady=12)

        self.draw_empty_state()
        self.win.mainloop()

    # ── 空状态 ──

    def draw_empty_state(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50:
            return
        self.canvas.create_text(w // 2, h // 2 - 20, text="📁",
                                 font=("", 48), fill="#2a2a3a")
        self.canvas.create_text(w // 2, h // 2 + 28, text="拖拽音频文件到此处",
                                 font=("", 14), fill="#444")
        self.canvas.create_text(w // 2, h // 2 + 50, text="或点击右上角「打开文件」",
                                 font=("", 11), fill="#333")

    # ── 文件 ──

    def open_file(self):
        path = ctk.filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[("音频/视频", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.mp4 *.mkv *.webm")]
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str):
        self.audio_path = path
        self.split_points.clear()
        self.current_time = 0
        self.stop_playback()
        self.duration = get_duration(path)
        name = os.path.basename(path)
        self.file_label.configure(text=name[:50] + ("..." if len(name) > 50 else ""))
        self.info_label.configure(text=f"总时长 {fmt_time(self.duration)}  ·  点击标尺跳转  ·  点击波形添加切割点")
        self.btn_cut.configure(state="normal")
        self.progress_bar.set(0)
        self.time_label.configure(text=f"0:00 / {fmt_time(self.duration)}")
        self.segment_count_label.configure(text="")
        threading.Thread(target=self._load_waveform, daemon=True).start()

    def _load_waveform(self):
        self.win.after(0, lambda: self.info_label.configure(text="⏳ 解析波形中..."))
        self.waveform = get_waveform_data(self.audio_path)
        self.win.after(0, self.redraw)
        self.win.after(0, lambda: self.info_label.configure(
            text=f"总时长 {fmt_time(self.duration)}  ·  点击标尺跳转  ·  点击波形添加切割点"))

    # ── 绘制 ──

    def redraw(self, event=None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        if not self.audio_path:
            self.draw_empty_state()
            return

        dur = self.duration if self.duration > 0 else 1
        mid = (h + RULER_H - BOTTOM_PAD) // 2 + RULER_H
        amp_h = (h - RULER_H - BOTTOM_PAD) * 0.42

        # ── 时间标尺 ──
        self.canvas.create_rectangle(0, 0, w, RULER_H, fill="#16162a", outline="")
        self.canvas.create_line(0, RULER_H, w, RULER_H, fill="#2a2a4a")
        # 刻度线
        total_sec = int(dur) + 1
        tick_interval = self._calc_tick_interval(w, dur)
        t = 0.0
        while t <= dur:
            x = int(t / dur * w)
            self.canvas.create_line(x, RULER_H - 8, x, RULER_H, fill="#555")
            self.canvas.create_text(x, RULER_H - 12, text=fmt_time(t),
                                     fill="#777", font=("", 8), anchor="s")
            t += tick_interval

        # ── 分段底色 ──
        all_pts = sorted([0] + self.split_points + [self.duration])
        for i in range(len(all_pts) - 1):
            x1 = int(all_pts[i] / dur * w)
            x2 = int(all_pts[i + 1] / dur * w)
            color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            # 半透明色用浅底色
            self.canvas.create_rectangle(x1, RULER_H, x2, h, fill="", outline="")

        # ── 波形条 ──
        if self.waveform:
            bar_w = w / len(self.waveform)
            # 区分已播放/未播放区域
            playhead_x = int(self.current_time / dur * w) if self.current_time > 0 else 0
            for i, amp in enumerate(self.waveform):
                x = i * bar_w
                bh = max(1.5, amp * amp_h)
                played = x < playhead_x
                # 渐变颜色：高振幅亮，低振幅暗
                brightness = int(60 + amp * 120)
                if played:
                    r, g, b = 0xe9, 0x45, 0x60
                else:
                    r, g, b = 0x4f, 0xc3, 0xf7
                ratio = brightness / 255
                color = f"#{int(r * ratio):02x}{int(g * ratio):02x}{int(b * ratio):02x}"
                self.canvas.create_line(x, mid - bh, x, mid + bh,
                                         fill=color, width=max(1.2, bar_w * 0.75))

        # ── 切割手柄 ──
        for i, pt in enumerate(self.split_points):
            px = int(pt / dur * w)
            color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            # 虚线
            self.canvas.create_line(px, RULER_H, px, h, fill=color, width=1.5, dash=(4, 4))
            # ▲ 三角手柄（从标尺向下突出）
            self.canvas.create_polygon(
                px - HANDLE_SIZE, RULER_H + 2,
                px + HANDLE_SIZE, RULER_H + 2,
                px, RULER_H + HANDLE_SIZE + 5,
                fill=color, outline="#fff", width=1
            )
            # 时间标签
            self.canvas.create_text(px, RULER_H - 13, text=fmt_time(pt),
                                     fill=color, font=("", 8, "bold"), anchor="s")

        # ── 段标签（在波形底部） ──
        for i in range(len(all_pts) - 1):
            x1 = int(all_pts[i] / dur * w)
            x2 = int(all_pts[i + 1] / dur * w)
            if x2 - x1 > 60:
                cx = (x1 + x2) / 2
                seg_dur = all_pts[i + 1] - all_pts[i]
                color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
                # 色块背景
                self.canvas.create_rectangle(cx - 28, h - BOTTOM_PAD + 4,
                                              cx + 28, h - BOTTOM_PAD + 20,
                                              fill="#222233", outline="")
                self.canvas.create_text(cx, h - BOTTOM_PAD + 12,
                                         text=f"第{i + 1}段 · {fmt_time(seg_dur)}",
                                         fill=color, font=("", 8, "bold"))

        # ── 播放头（始终可见，红色粗线 + ▼ 倒三角） ──
        px = int(self.current_time / dur * w)
        # 粗实线贯穿整个波形
        self.canvas.create_line(px, RULER_H, px, h, fill="#e94560", width=3)
        # ▼ 顶部倒三角手柄（可拖拽）
        self.canvas.create_polygon(
            px - 7, 2, px + 7, 2, px, RULER_H - 1,
            fill="#e94560", outline=""
        )
        # 时间标签
        self.canvas.create_text(px, RULER_H - 14, text=fmt_time(self.current_time),
                                 fill="#e94560", font=("", 8, "bold"), anchor="s")
        # 底部圆形手柄
        r = 5
        self.canvas.create_oval(px - r, h - BOTTOM_PAD + 10, px + r, h - BOTTOM_PAD + 20,
                                 fill="#e94560", outline="#fff", width=1)

        # ── 悬停指示 ──
        if self.hover_time >= 0 and self.audio_path:
            hx = int(self.hover_time / dur * w)
            self.canvas.create_line(hx, RULER_H, hx, h, fill="#555", width=1, dash=(2, 6))
            self.canvas.create_text(min(max(hx, 30), w - 30), RULER_H + 16,
                                     text=fmt_time(self.hover_time),
                                     fill="#fff", font=("", 9), anchor="s")

        # 更新底栏
        self._update_segment_info()

    def _calc_tick_interval(self, canvas_w: float, dur: float) -> float:
        """根据画布宽度和时长计算合适的刻度间隔。"""
        rough = dur / (canvas_w / 80)  # 大约每80像素一个刻度
        for interval in [5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600]:
            if rough <= interval:
                return interval
        return max(5, int(rough / 5) * 5)

    def _update_segment_info(self):
        n = len(self.split_points)
        if n == 0:
            self.segment_count_label.configure(text="")
        else:
            self.segment_count_label.configure(text=f"共 {n + 1} 段")

    # ── 鼠标交互 ──

    def on_click(self, event):
        if not self.audio_path or self.duration <= 0:
            return
        w = self.canvas.winfo_width()

        # 点击标尺区域 → 跳转播放位置
        if event.y < RULER_H:
            t = max(0, min(self.duration, event.x / w * self.duration))
            self.seek_to(t)
            return

        # 拖动播放头
        px = self.current_time / self.duration * w
        if abs(event.x - px) < 10:
            self.dragging_playhead = True
            self.canvas.config(cursor="sb_h_double_arrow")
            return

        t = event.x / w * self.duration

        # 检查是否点击手柄
        for i, pt in enumerate(self.split_points):
            px = pt / self.duration * w
            if abs(event.x - px) < HANDLE_SIZE + 6:
                self.drag_idx = i
                self.canvas.config(cursor="sb_h_double_arrow")
                return

        # 添加新的切割点
        t = max(0.3, min(self.duration - 0.3, t))
        self.split_points.append(t)
        self.split_points.sort()
        self.drag_idx = self.split_points.index(t)
        self.canvas.config(cursor="sb_h_double_arrow")
        self.redraw()

    def on_drag(self, event):
        if not self.audio_path or self.duration <= 0:
            return
        w = self.canvas.winfo_width()

        # 拖动播放头
        if self.dragging_playhead:
            t = max(0, min(self.duration, event.x / w * self.duration))
            self.current_time = t
            self.time_label.configure(text=f"{fmt_time(t)} / {fmt_time(self.duration)}")
            self.progress_bar.set(t / self.duration)
            self.redraw()
            return

        # 拖动切割点
        if self.drag_idx < 0:
            return
        t = max(0.3, min(self.duration - 0.3, event.x / w * self.duration))
        self.split_points[self.drag_idx] = t
        self.split_points.sort()
        self.drag_idx = self.split_points.index(t)
        self.redraw()

    def on_release(self, event):
        # 释放播放头：跳转到新位置
        if self.dragging_playhead:
            self.dragging_playhead = False
            self.seek_to(self.current_time)
        self.drag_idx = -1
        self.canvas.config(cursor="")
        self.redraw()

    def on_right_click(self, event):
        if not self.audio_path or not self.split_points or self.duration <= 0:
            return
        w = self.canvas.winfo_width()
        for i, pt in enumerate(self.split_points):
            px = pt / self.duration * w
            if abs(event.x - px) < HANDLE_SIZE + 6:
                self.split_points.pop(i)
                self.drag_idx = -1
                self.redraw()
                return

    def on_hover(self, event):
        if not self.audio_path or self.duration <= 0:
            return
        w = self.canvas.winfo_width()
        self.hover_time = event.x / w * self.duration

        # 标尺区域：指针光标（可跳转）；波形区域：十字/拖拽
        # 靠近播放头：拖拽光标
        near_playhead = False
        px = self.current_time / self.duration * w
        if abs(event.x - px) < 10:
            near_playhead = True
            if abs(event.x - px) < 10:
                near_playhead = True

        if event.y < RULER_H:
            self.canvas.config(cursor="hand2")
        elif near_playhead:
            self.canvas.config(cursor="sb_h_double_arrow")
        else:
            near_handle = False
            for pt in self.split_points:
                px = pt / self.duration * w
                if abs(event.x - px) < HANDLE_SIZE + 6:
                    near_handle = True
                    break
            self.canvas.config(cursor="sb_h_double_arrow" if near_handle else "crosshair")
        self.redraw()

    def clear_points(self):
        self.split_points.clear()
        self.redraw()

    def undo_last_point(self):
        if self.split_points:
            self.split_points.pop()
            self.redraw()

    # ── 播放 ──

    def seek_to(self, time_sec: float):
        """跳转到指定时间，播放中则从新位置继续。"""
        was_playing = self.playing
        if was_playing:
            self.stop_playback()
        self.current_time = time_sec
        self.time_label.configure(text=f"{fmt_time(self.current_time)} / {fmt_time(self.duration)}")
        self.progress_bar.set(self.current_time / self.duration if self.duration > 0 else 0)
        if was_playing:
            self.start_playback()
        self.redraw()

    def toggle_play(self):
        if self.playing:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        if not self.audio_path:
            return
        self.stop_playback()
        self.playing = True
        self.btn_play.configure(text="⏸ 暂停")
        start = self.current_time if self.current_time > 0 else 0
        self.play_proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-ss", str(start),
             "-i", self.audio_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._update_play_time()

    def stop_playback(self):
        self.playing = False
        self.btn_play.configure(text="▶ 播放")
        if self.play_proc:
            try:
                self.play_proc.terminate()
            except Exception:
                pass
            self.play_proc = None
        if self.play_timer_id:
            self.win.after_cancel(self.play_timer_id)
            self.play_timer_id = None

    def _update_play_time(self):
        if not self.playing:
            return
        self.current_time += 0.1
        self.time_label.configure(text=f"{fmt_time(self.current_time)} / {fmt_time(self.duration)}")
        self.progress_bar.set(self.current_time / self.duration if self.duration > 0 else 0)
        self.redraw()
        if self.current_time >= self.duration:
            self.stop_playback()
            self.current_time = 0
            self.time_label.configure(text=f"0:00 / {fmt_time(self.duration)}")
            self.progress_bar.set(0)
            self.redraw()
            return
        self.play_timer_id = self.win.after(100, self._update_play_time)

    # ── 切割导出 ──

    def do_cut(self):
        if not self.audio_path:
            return
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.basename(self.audio_path).rsplit(".", 1)[0]
        ext = os.path.basename(self.audio_path).rsplit(".", 1)[-1]

        all_pts = [0] + sorted(self.split_points) + [self.duration]
        segments = [(all_pts[i], all_pts[i + 1]) for i in range(len(all_pts) - 1)]

        self.info_label.configure(text="切割中...")
        self.btn_cut.configure(state="disabled")

        def _run():
            for i, (s, e) in enumerate(segments):
                out = os.path.join(output_dir, f"{base}_part{i + 1:02d}.{ext}")
                cut_segment(self.audio_path, out, s, e - s)
            self.win.after(0, lambda: self.info_label.configure(
                text=f"✅ 完成！{len(segments)} 段已保存到 {output_dir}"))
            self.win.after(0, lambda: self.btn_cut.configure(state="normal"))

        threading.Thread(target=_run, daemon=True).start()


# ── CLI 兼容模式 ───────────────────────────────────────────

def cli_mode():
    import argparse
    import re

    def parse_time(time_str: str) -> float:
        time_str = time_str.strip()
        if re.match(r'^\d+(\.\d+)?$', time_str):
            return float(time_str)
        parts = time_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        raise ValueError(f"无法解析时间: {time_str}")

    parser = argparse.ArgumentParser(description="音频切割工具 (CLI 模式)")
    parser.add_argument("mode", nargs="?", default="gui",
                        help="'cli' 进入命令行模式，默认打开 GUI")
    parser.add_argument("-i", "--input", help="输入音频文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出目录")
    parser.add_argument("-s", "--split", help="切割时间点 (如 6:30 或 2:00,5:30)")
    parser.add_argument("-r", "--ranges", help="提取时间段 (如 0:30-1:20,2:00-3:15)")
    parser.add_argument("-d", "--delete", help="删除时间段 (如 1:00-2:00)")

    args = parser.parse_args()

    if args.mode != "cli" and not args.input:
        return  # 走 GUI

    if not args.input or not os.path.exists(args.input):
        print("错误：文件不存在"); sys.exit(1)

    if args.split:
        points = [parse_time(p) for p in args.split.split(",")]
        all_pts = [0] + sorted(points) + [get_duration(args.input)]
    elif args.ranges:
        ranges = [(parse_time(r.split("-")[0]), parse_time(r.split("-")[1]))
                   for r in args.ranges.split(",")]
        os.makedirs(args.output, exist_ok=True)
        base = os.path.basename(args.input).rsplit(".", 1)[0]
        ext = os.path.basename(args.input).rsplit(".", 1)[-1]
        for i, (s, e) in enumerate(ranges):
            out = os.path.join(args.output, f"{base}_part{i + 1:02d}.{ext}")
            cut_segment(args.input, out, s, e - s)
            print(f"✅ {out}")
        print("\n完成！")
        return
    elif args.delete:
        s, e = args.delete.split("-")
        s, e = parse_time(s), parse_time(e)
        dur = get_duration(args.input)
        os.makedirs(args.output, exist_ok=True)
        base = os.path.basename(args.input).rsplit(".", 1)[0]
        ext = os.path.basename(args.input).rsplit(".", 1)[-1]
        out = os.path.join(args.output, f"{base}_cut.{ext}")

        concat_list = os.path.join(args.output, "_concat.txt")
        p1 = os.path.join(args.output, "_p1." + ext)
        p2 = os.path.join(args.output, "_p2." + ext)
        if s > 0:
            cut_segment(args.input, p1, 0, s)
        if e < dur:
            cut_segment(args.input, p2, e, dur - e)
        with open(concat_list, "w") as f:
            if s > 0: f.write(f"file '{os.path.abspath(p1)}'\n")
            if e < dur: f.write(f"file '{os.path.abspath(p2)}'\n")
        subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
                         "-c", "copy", "-y", out], check=True, capture_output=True)
        for t in [p1, p2, concat_list]:
            if os.path.exists(t): os.remove(t)
        print(f"✅ {out}\n完成！")
        return
    else:
        parser.print_help()
        return

    os.makedirs(args.output, exist_ok=True)
    base = os.path.basename(args.input).rsplit(".", 1)[0]
    ext = os.path.basename(args.input).rsplit(".", 1)[-1]
    for i in range(len(all_pts) - 1):
        s, e = all_pts[i], all_pts[i + 1]
        out = os.path.join(args.output, f"{base}_part{i + 1:02d}.{ext}")
        cut_segment(args.input, out, s, e - s)
        print(f"✅ {out}")
    print("\n完成！")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        cli_mode()
    elif len(sys.argv) > 1:
        cli_mode()
    else:
        AudioCutterApp()
