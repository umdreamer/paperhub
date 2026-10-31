# SQLite 资料与附件索引实施计划

> 目标 Issue：[ #2 ](https://github.com/umdreamer/paperhub/issues/2)。每一步在当前会话执行；每次提交先运行所列测试。

**目标：** 用 Python 标准库建立可重复打开的 SQLite 主索引，并支持资料条目与文件的多对多关联。

**结构：** `paperhub/store.py` 只负责数据库连接、建表和最小写入接口；`tests/test_store.py` 使用临时真实数据库验证行为。后续扫描、GUI 与 Zotero 接入各自 Issue。

**技术：** Python 3、`sqlite3`、`unittest`、`tempfile`。

## 任务 1：建库与持久化

文件：`tests/test_store.py`、`paperhub/store.py`。

- [ ] 写测试：`with tempfile.TemporaryDirectory()` 创建 `index.sqlite3`；调用 `open_store(path)`，插入一条 `work`；关闭并重开后查询同一 ID；检查 `PRAGMA foreign_keys` 为 1。
- [ ] 运行 `python3 -m unittest tests.test_store -v`，确认因 `paperhub.store` 缺失失败。
- [ ] 实现 `open_store(path)`：`sqlite3.connect`、`PRAGMA foreign_keys=ON`、`CREATE TABLE IF NOT EXISTS work`、`asset`、`work_asset`、`zotero_link`；返回连接。`work` 和 `asset` 使用文本 UUID 主键，`asset.path` 唯一，关系以 `(work_id, asset_id, role)` 为键。
- [ ] 运行 `python3 -m unittest tests.test_store -v` 和 `python3 -m compileall -q paperhub tests`；通过后提交，消息只引用 `#2` 并记录实际命令。

## 任务 2：关系与约束

文件：`tests/test_store.py`、`paperhub/store.py`。

- [ ] 写测试：同一个 `work` 关联两个 `asset`，其中一个 `asset` 再关联第二个 `work`；查询得到三条关系；重复 `asset.path` 和重复 `(library_id, item_key)` 触发 `sqlite3.IntegrityError`；不同路径但相同 MD5、SHA-256 可并存；可选元数据为 `NULL`。
- [ ] 运行 `python3 -m unittest tests.test_store -v`，确认新测试因缺少接口或约束失败。
- [ ] 增加最小接口：`add_work(conn, kind, title=None, work_id=None)`、`add_asset(conn, path, size, md5, sha256, asset_id=None)`、`link_asset(conn, work_id, asset_id, role)`、`link_zotero(conn, work_id, library_id, item_key)`；ID 默认由 `uuid.uuid4()` 生成。写入使用参数化 SQL，不吞并唯一约束错误。
- [ ] 运行 `python3 -m unittest discover -s tests -v`、`python3 -m compileall -q paperhub tests`、`git diff --check`；通过后提交，消息只引用 `#2`。

## Issue 验收

复跑全部 `unittest`；检查文件系统中只增加源码、测试和计划，不接触现有 Papers 文献库；把命令、结果及未验证范围记入 Issue。Issue 在分支合并且远端 `main` 核验后关闭。
