import os
import shutil
import customtkinter as ctk
from tkinter import filedialog
import threading

class MinimalistFileDeleter(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("极简文件删除器")
        self.geometry("400x300")
        ctk.set_appearance_mode("dark")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Create and place widgets
        self.create_widgets()

    def create_widgets(self):
        # Futuristic title
        self.title_label = ctk.CTkLabel(self, text="极简文件删除器", font=("Roboto", 24))
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="ew")

        # Frame for input and buttons
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(self.input_frame, placeholder_text="选择文件或文件夹路径")
        self.path_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        # 在 input_frame 中添加下拉框
        self.type_menu = ctk.CTkOptionMenu(
            self.input_frame, 
            values=["文件夹", "文件"],
            width=80
        )
        self.type_menu.grid(row=0, column=1, padx=(0, 10))
        self.type_menu.set("文件夹")  # 设置默认值

        self.browse_button = ctk.CTkButton(self.input_frame, text="浏览", command=self.browse_item, width=60)
        self.browse_button.grid(row=0, column=2)  # 将列号改为2

        # Circular progress bar (initially hidden)
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate", width=200)
        self.progress.grid(row=2, column=0, pady=20)
        self.progress.grid_remove()

        # Delete button
        self.delete_button = ctk.CTkButton(self, text="删除", command=self.delete_item, fg_color="#FF5252", hover_color="#FF1744")
        self.delete_button.grid(row=3, column=0, pady=(0, 20))

        # Status label
        self.status_label = ctk.CTkLabel(self, text="", font=("Roboto", 12))
        self.status_label.grid(row=4, column=0, pady=(0, 10))

    def browse_item(self):
        path = ""
        if self.type_menu.get() == "文件夹":
            path = filedialog.askdirectory(title="选择要删除的文件夹")
        else:
            path = filedialog.askopenfilename(title="选择要删除的文件")
        
        if path:
            self.path_entry.delete(0, ctk.END)
            self.path_entry.insert(0, path)

    def delete_item(self):
        path = self.path_entry.get()
        if not path:
            self.status_label.configure(text="请先选择要删除的文件或文件夹", text_color="#FFC107")
            return

        def delete_thread():
            self.delete_button.configure(state="disabled")
            self.progress.grid()
            self.progress.start()
            self.status_label.configure(text="正在删除...", text_color="#03A9F4")

            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                self.status_label.configure(text=f"已成功删除: {path}", text_color="#4CAF50")
                self.path_entry.delete(0, ctk.END)
            except Exception as e:
                self.status_label.configure(text=f"删除失败: {str(e)}", text_color="#FF5252")

            self.progress.stop()
            self.progress.grid_remove()
            self.delete_button.configure(state="normal")

        threading.Thread(target=delete_thread).start()

if __name__ == "__main__":
    app = MinimalistFileDeleter()
    app.mainloop()
