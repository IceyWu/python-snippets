"""
人声分离工具 —— 从音频/视频中剥离背景音乐，只保留人声。

方案：Meta demucs (htdemucs) —— 目前 SOTA 级别音源分离
  模型自动下载到 ~/.cache/torch/hub/checkpoints/（约 84MB）

支持格式：
  音频: mp3, wav, flac, ogg, m4a, aac
  视频: mp4, flv, mkv, avi, mov, webm

用法：
  python main.py          → 打开 GUI 界面
  python main.py cli ...  → 命令行模式
"""

import os
import sys
import subprocess
import tempfile
import threading
import re
import customtkinter as ctk
from tkinter import filedialog

# 确保 FFmpeg 在 PATH 中
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

AUDIO_EXT = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')
VIDEO_EXT = ('.mp4', '.flv', '.mkv', '.avi', '.mov', '.webm')
MODELS = ["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_extra"]


def is_video(filepath: str) -> bool:
    return filepath.lower().endswith(VIDEO_EXT)


def is_supported(filepath: str) -> bool:
    return filepath.lower().endswith(AUDIO_EXT + VIDEO_EXT)


def extract_audio(video_path: str) -> str:
    tmp_file = os.path.join(
        tempfile.gettempdir(),
        "vocal_sep_" + os.path.basename(video_path).rsplit('.', 1)[0] + ".mp3"
    )
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-ar", "44100", "-ac", "2", "-ab", "192k", "-f", "mp3",
        "-y", tmp_file
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return tmp_file


def fmt_time(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


# ── GUI ───────────────────────────────────────────────────

class VocalSeparatorApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.win = ctk.CTk()
        self.win.title("人声分离工具")
        self.win.geometry("700x580")
        self.win.minsize(550, 450)

        self.input_files: list[str] = []
        self.output_dir: str = os.path.join(os.path.dirname(__file__), "output")
        self.running = False

        # ── 顶部 ──
        top = ctk.CTkFrame(self.win, fg_color="#1e1e2e", corner_radius=0, height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="🎤 人声分离", font=ctk.CTkFont(size=16, weight="bold"),
                      text_color="#e94560").pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(top, text="基于 Meta demucs", text_color="#666",
                      font=ctk.CTkFont(size=11)).pack(side="left")

        # ── 主内容 ──
        body = ctk.CTkFrame(self.win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # 输入文件
        ctk.CTkLabel(body, text="输入文件", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        file_row = ctk.CTkFrame(body, fg_color="transparent")
        file_row.pack(fill="x", pady=(4, 2))

        self.file_label = ctk.CTkLabel(file_row, text="未选择文件",
                                        fg_color="#2b2b3d", corner_radius=6,
                                        padx=12, pady=6, anchor="w")
        self.file_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(file_row, text="📂 选择文件", width=110, height=30,
                       command=self.pick_files).pack(side="left", padx=(0, 4))
        ctk.CTkButton(file_row, text="📁 选择文件夹", width=110, height=30,
                       command=self.pick_folder).pack(side="left")

        ctk.CTkLabel(body, text="支持 mp3/wav/flac/mp4/mkv 等格式",
                      text_color="#555", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 8))

        # 模型选择
        model_row = ctk.CTkFrame(body, fg_color="transparent")
        model_row.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(model_row, text="分离模型", width=80).pack(side="left", padx=(0, 8))
        self.model_var = ctk.StringVar(value="htdemucs")
        ctk.CTkOptionMenu(model_row, values=MODELS, variable=self.model_var,
                           width=160).pack(side="left")
        ctk.CTkLabel(model_row, text="htdemucs 质量最高",
                      text_color="#555", font=ctk.CTkFont(size=11)).pack(side="left", padx=8)

        # 输出目录
        out_row = ctk.CTkFrame(body, fg_color="transparent")
        out_row.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(out_row, text="输出目录", width=80).pack(side="left", padx=(0, 8))
        self.out_label = ctk.CTkLabel(out_row, text=self.output_dir,
                                       fg_color="#2b2b3d", corner_radius=6,
                                       padx=12, pady=4, anchor="w")
        self.out_label.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(out_row, text="浏览", width=60, height=28,
                       command=self.pick_output).pack(side="left")

        # 进度条
        self.progress = ctk.CTkProgressBar(body, height=10, fg_color="#2b2b3d",
                                            progress_color="#e94560")
        self.progress.pack(fill="x", pady=(8, 4))
        self.progress.set(0)

        # 状态
        self.status_label = ctk.CTkLabel(body, text="就绪", text_color="#888")
        self.status_label.pack(anchor="w")

        # 日志区域
        self.log_box = ctk.CTkTextbox(body, height=180, fg_color="#12121a",
                                       text_color="#aaa", font=ctk.CTkFont(size=11))
        self.log_box.pack(fill="both", expand=True, pady=(8, 8))
        self.log_box.insert("end", "等待开始...\n")
        self.log_box.configure(state="disabled")

        # 开始按钮
        self.btn_start = ctk.CTkButton(body, text="🚀 开始分离", height=38,
                                        fg_color="#e94560", hover_color="#d63852",
                                        command=self.start_separation)
        self.btn_start.pack(fill="x", pady=(4, 0))

        self.win.mainloop()

    def log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def pick_files(self):
        files = filedialog.askopenfilenames(
            title="选择音频/视频文件",
            filetypes=[("支持的格式", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.mp4 *.mkv *.webm *.flv *.avi *.mov")]
        )
        if files:
            self.input_files = list(files)
            names = ", ".join(os.path.basename(f)[:30] for f in self.input_files[:3])
            if len(self.input_files) > 3:
                names += f" ... 等 {len(self.input_files)} 个"
            self.file_label.configure(text=names)
            self.log(f"已选择 {len(self.input_files)} 个文件")

    def pick_folder(self):
        folder = filedialog.askdirectory(title="选择包含音频/视频的文件夹")
        if folder:
            self.input_files = [
                os.path.join(folder, f) for f in os.listdir(folder)
                if is_supported(f)
            ]
            if not self.input_files:
                self.status_label.configure(text="文件夹中未找到支持的音频/视频文件")
                return
            self.file_label.configure(text=f"{folder} ({len(self.input_files)} 个文件)")
            self.log(f"从文件夹找到 {len(self.input_files)} 个文件")

    def pick_output(self):
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_dir = folder
            self.out_label.configure(text=folder)

    def start_separation(self):
        if not self.input_files:
            self.status_label.configure(text="请先选择输入文件")
            return
        if self.running:
            return
        self.running = True
        self.btn_start.configure(state="disabled", text="⏳ 处理中...")
        self.progress.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        threading.Thread(target=self._run_separation, daemon=True).start()

    def _run_separation(self):
        model = self.model_var.get()
        total = len(self.input_files)
        os.makedirs(self.output_dir, exist_ok=True)

        for idx, filepath in enumerate(self.input_files):
            name = os.path.basename(filepath)
            tag = "🎬" if is_video(filepath) else "🎵"

            self.win.after(0, lambda i=idx, n=name, t=tag:
                self.log(f"[{i + 1}/{total}] {t} {n}"))
            self.win.after(0, lambda i=idx: self.status_label.configure(
                text=f"处理中 {i + 1}/{total}..."))
            self.win.after(0, lambda i=idx: self.progress.set(i / total))

            try:
                audio_path = filepath
                tmp = None
                if is_video(filepath):
                    self.win.after(0, lambda: self.log("  ⏳ 提取音频..."))
                    tmp = extract_audio(filepath)
                    audio_path = tmp
                    self.win.after(0, lambda: self.log("  ✅ 音频已提取"))

                base = os.path.basename(audio_path).rsplit('.', 1)[0]
                cmd = [
                    "python", "-m", "demucs",
                    "--two-stems", "vocals",
                    "-n", model,
                    "-o", self.output_dir,
                    "--mp3", "--mp3-bitrate", "320",
                    audio_path
                ]
                self.win.after(0, lambda: self.log("  ⏳ AI 分离中..."))

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                # 手动解码避免 Windows GBK 编码问题
                for line_bytes in proc.stderr:
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if '%' in line and '|' in line:
                        try:
                            pct = int(re.search(r'(\d+)%', line).group(1))
                            self.win.after(0, lambda p=pct, i=idx, t=total:
                                self.progress.set((i + p / 100) / t))
                        except Exception:
                            pass
                    elif line and not line.startswith('['):
                        self.win.after(0, lambda l=line: self.log(f"  {l}"))

                proc.wait()
                if proc.returncode != 0:
                    raise subprocess.CalledProcessError(proc.returncode, cmd)

                if tmp and os.path.exists(tmp):
                    os.remove(tmp)

                out_path = os.path.join(self.output_dir, model, base)
                self.win.after(0, lambda b=base, o=out_path: self.log(
                    f"  ✅ 完成！\n     人声: {o}/vocals.mp3\n     背景: {o}/no_vocals.mp3"))

            except Exception as e:
                self.win.after(0, lambda n=name, err=str(e):
                    self.log(f"  ❌ 失败: {n} - {err}"))

        self.win.after(0, self._done)

    def _done(self):
        self.running = False
        self.progress.set(1)
        self.btn_start.configure(state="normal", text="🚀 开始分离")
        self.status_label.configure(text="✅ 全部完成！")
        self.log(f"\n完成！输出目录: {self.output_dir}")


# ── CLI 兼容模式 ───────────────────────────────────────────

def cli_mode():
    import argparse

    parser = argparse.ArgumentParser(description="人声分离工具 (CLI 模式)")
    parser.add_argument("mode", nargs="?", default="gui",
                        help="'cli' 进入命令行模式")
    parser.add_argument("-i", "--input", default="input", help="输入文件或目录")
    parser.add_argument("-o", "--output", default="output", help="输出目录")
    parser.add_argument("-m", "--model", default="htdemucs",
                        choices=MODELS, help="分离模型")
    args = parser.parse_args()

    if args.mode != "cli":
        return

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        files = [os.path.join(args.input, f) for f in os.listdir(args.input)
                 if is_supported(f)]
    else:
        print(f"错误：路径不存在 - {args.input}"); sys.exit(1)

    os.makedirs(args.output, exist_ok=True)
    for f in files:
        name = os.path.basename(f)
        print(f"处理: {name}")
        audio_path = f
        tmp = None
        if is_video(f):
            print("  提取音频...")
            tmp = extract_audio(f)
            audio_path = tmp
        cmd = ["python", "-m", "demucs", "--two-stems", "vocals",
               "-n", args.model, "-o", args.output, "--mp3",
               "--mp3-bitrate", "320", audio_path]
        subprocess.run(cmd, check=True, capture_output=True)
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        base = os.path.basename(audio_path).rsplit('.', 1)[0]
        print(f"  完成 → {args.output}/{args.model}/{base}/vocals.mp3")
    print("\n全部完成！")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        cli_mode()
    else:
        VocalSeparatorApp()
