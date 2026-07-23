# 批量创建 Excel 文件

从 txt 名称列表批量生成 `.xlsx` 文件。

## 运行

1. 安装依赖：`pip install -r requirements.txt`
2. 准备一个 `name_list.txt`，每行一个文件名（不含后缀）
3. 修改 `main.py` 中的路径：
   - `file_dir`：输出目录
   - `txt_file_path`：名称列表文件路径
   - `suffix`：文件后缀（默认 `.xlsx`）
4. 运行：`python main.py`
