import os
import shutil
import customtkinter as ctk
from tkinter import filedialog


class ModernFileDeleterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("现代文件/文件夹删除器")
        self.geometry("500x400")

        # Configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # Sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="文件删除器", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="外观模式:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # Main frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        # Path entry and browse button
        self.path_entry = ctk.CTkEntry(self.main_frame, placeholder_text="选择文件或文件夹路径")
        self.path_entry.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="ew")
        self.browse_button = ctk.CTkButton(self.main_frame, text="浏览", command=self.browse_item, width=100)
        self.browse_button.grid(row=0, column=1, padx=(10, 20), pady=(20, 10), sticky="e")

        # Delete button
        self.delete_button = ctk.CTkButton(self.main_frame, text="删除", command=self.delete_item, fg_color="red",
                                           hover_color="dark red")
        self.delete_button.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # Status text box
        self.status_textbox = ctk.CTkTextbox(self.main_frame, height=200, wrap="word")
        self.status_textbox.grid(row=2, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="nsew")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def browse_item(self):
        path = filedialog.askdirectory(title="选择要删除的文件夹或文件")
        if path:
            self.path_entry.delete(0, ctk.END)
            self.path_entry.insert(0, path)

    def delete_item(self):
        path = self.path_entry.get()
        if not path:
            self.status_textbox.insert(ctk.END, "请先选择要删除的文件或文件夹\n")
            return

        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            self.status_textbox.insert(ctk.END, f"已成功删除: {path}\n")
            self.path_entry.delete(0, ctk.END)
        except Exception as e:
            self.status_textbox.insert(ctk.END, f"删除失败: {str(e)}\n")

        self.status_textbox.see(ctk.END)


if __name__ == "__main__":
    app = ModernFileDeleterApp()
    app.mainloop()

print("程序已退出")