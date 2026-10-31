# PaperHub 本地版 0.1.0

PaperHub 0.1.0 是本地科研资料的 Qt 索引预览程序。它在用户点击“扫描并更新索引”后读取选定目录，支持 PDF、EPUB、PPT/PPTX、HTML/HTM、MP4/MOV，计算文件大小、MD5 和 SHA-256，并把稳定文件记录写入指定的 SQLite 数据库。重复扫描保留文件 ID；同一路径内容变化时提示冲突并保留数据库中的旧摘要。程序不修改、移动或删除资料文件。

本版本是[需求方案](docs/需求方案.md)的第一阶段。自动监听、文件命名与归档、正文检索、HTML/Excel/BibTeX 导出、Zotero 双向同步尚未实现；不能把当前索引当作已完成的 Zotero 同步。

## 安装与运行

在本仓库目录中使用带 PySide6 的 Python 环境：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m paperhub
```

也可用 `paperhub --library /path/to/library --database /path/to/index.sqlite3` 预填路径。启动时不扫描；在窗口中确认两个路径后点击按钮。数据库文件的上级目录必须已存在。建议将数据库放在受控的独立目录，不放入 Zotero 数据目录。`python3 -m paperhub --help` 可在不加载 Qt 的情况下查看参数。

## 验证

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m paperhub --help
```

索引规则和数据边界见[资料规则与数据模型](docs/资料规则与数据模型.md)。
