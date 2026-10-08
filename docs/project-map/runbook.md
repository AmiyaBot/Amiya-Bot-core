# 运行手册（runbook）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> `[事实]` 本项目**没有 CLI 入口**（无 `entry_points`，`setup.py:99-117`；无 `__main__.py`），所有「启动」都由**用户自己的脚本**发起。

## 1. 本地安装

`[事实]` 前置条件：Python `>=3.10`（`setup.py:112`）。本机实测 `3.13.3`。

### 1.1 从 PyPI 安装（普通用户）

```bash
pip install amiyabot
```

`[事实]` `README.md:23` 即此命令。`[事实]` 最新发布版 `2.1.0`。

### 1.2 从源码安装（开发者）

`[事实]` 本仓库是 legacy `setup.py` 项目，**无 `pyproject.toml`**。`[建议]` 推荐可编辑安装：

```bash
pip install -e .
```

`[事实]` 注意三个坑：

| 坑 | 证据 |
|---|---|
| `setup.py:6` 直接 `from wheel.bdist_wheel import ...`，**必须先有 `wheel` 包** | `setup.py:6`；CI 里靠 `pypi.yml:27` 显式装 |
| `setup.py:88-92` 会在导入时**写回** `requirements.txt`（排序+小写），污染 git status | `setup.py:91-92` |
| 直接 `python setup.py bdist_wheel` 不带 `--auto-increment-version` 会**卡在交互式 `input()`** | `setup.py:68` |

`[建议]` 因此本地不要随手跑 `python setup.py ...`；用 `pip install -e .`。

### 1.3 可选：安装浏览器二进制

`[事实]` `[推断]` `playwright` **库**是强制依赖且急切导入（`requirements.txt:7`、`browserService/__init__.py:1`），但**浏览器二进制不是 import 期必需**——只在真正渲染 HTML 时才需要：

- 入口一：`AmiyaBot.start(launch_browser=True)`（`amiyabot/__init__.py:69-70`）
- 入口二：`Chain.html()` / `Chain.markdown()`（`messageChain/__init__.py:159,181` → `element.py:106`）

`[建议]` 只有用到上述功能时才需要：

```bash
playwright install chromium
```

`[事实]` 默认 `browser_type='chromium'`（`browserService/launchConfig.py:17`），默认 `headless=True`（`:29`，`BROWSER_LAUNCH_WITH_HEADED` 未设时）。

## 2. 最小可运行示例

`[事实]` 直接来自 `README.md:27-41`（已核对与代码一致）：

```python
import asyncio
from amiyabot import AmiyaBot, Message, Chain

bot = AmiyaBot(appid='******', token='******')

@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')

asyncio.run(bot.start())
```

`[事实]` **默认适配器是 QQ 频道**（`amiyabot/__init__.py:53` `adapter=QQGuildBotInstance`）。`[推断]` 不传 `adapter` 时会去连 `https://api.sgroup.qq.com`（`qqGuild/api.py:34`），非腾讯环境会走重试路径。

`[建议]` 做本地实验时显式指定适配器，`README.md:67-86` 给了 OneBot 11 的例子：

```python
from amiyabot.adapters.onebot.v11 import onebot11
bot = AmiyaBot(appid='...', token='...',
               adapter=onebot11(host='127.0.0.1', http_port=8080, ws_port=8060))
```

`[事实]` `[建议]` **完全离线**时用 `test` 适配器最方便（本地起 WS 服务端，不需要真机器人）：

```python
from amiyabot.adapters.test import test_instance
bot = AmiyaBot(appid='test', token='test', adapter=test_instance(host='127.0.0.1', port=32001))
```

`[事实]` `test_instance` 默认 `host='127.0.0.1', port=32001`（`adapters/test/__init__.py:14`）。⚠️ `[建议]` **不要**把 `host` 改成 `0.0.0.0`——该端点无鉴权（见 [risks.md](risks.md) R-17）。

## 3. 常用调试命令

`[事实]` 项目提供的脚本（`scripts/`）：

```bash
# lint —— 与 CI 完全一致（pylint.yml:24）
bash scripts/pylint.sh
# 等价于：pylint amiyabot --rcfile=pylint.conf

# 格式化 —— CI 不跑，需本地手动
bash scripts/black.sh
# 等价于：black amiyabot --skip-string-normalization --line-length 120

# 发布（手动场景，与 CI 的 OIDC 路径并存）
bash scripts/publish.sh
# 等价于：twine upload dist/*
```

`[事实]` 没有测试命令可跑（项目零测试，见 [testing-quality.md](testing-quality.md)）。

`[建议]` 最高频的冒烟检查：

```bash
python -c "import amiyabot; print('ok')"     # 验证包可导入、依赖齐全
```

`[建议]` 确认实际安装版本（因为**源码里没有 `__version__`**，`import amiyabot; amiyabot.__version__` 会 `AttributeError`）：

```bash
pip show amiyabot | head -3
# 或
python -c "import importlib.metadata as m; print(m.version('amiyabot'))"
```

`[事实]` 证据：`grep -rn "__version__" amiyabot/` 无输出。

## 4. 运行时配置

`[事实]` **本项目不读取任何环境变量**：

```
$ grep -rn "os.environ\|getenv" --include="*.py" amiyabot/
（无输出）
```

`[事实]` 所有运行时配置都是**宿主脚本的命令行参数**，由 `amiyautils.argv` 读取：

| 参数 | 类型 | 默认 | 作用 | 证据 |
|---|---|---|---|---|
| `--text-max-length` | int | `100` | `Chain.text()` 单条文本长度上限 | `messageChain/__init__.py:17` |
| `--browser-width` | int | `1280` | 渲染视口宽 | `launchConfig.py:6` |
| `--browser-height` | int | `720` | 渲染视口高 | `launchConfig.py:7` |
| `--browser-render-time` | int | `200` | 渲染等待毫秒 | `launchConfig.py:8` |
| `--browser-page-pool-size` | int | `0` | 页面池大小（0=不池化） | `launchConfig.py:9,19` |
| `--browser-launch-with-headed` | bool | 未设 | 有头模式（默认无头） | `launchConfig.py:10,29` |
| `--debug` | bool | 未设 | 调试（挂 console/pageerror 监听） | `launchConfig.py:20`、`browserService/__init__.py:57-59` |

`[推断]` 即：配置通过**运行宿主脚本时传参**生效，例如 `python main.py --debug --text-max-length 200`。`[建议]` 这是隐式配置，新人不看代码不会知道。

`[事实]` 程序化配置的入口是 `GroupConfig`（`factory/factoryTyping.py:35-40`）：

```python
GroupConfig(group_id, check_prefix=True, allow_direct=False, direct_only=False)
```

`[事实]` 通过 `bot.set_group_config(config)` 注册（`factory/__init__.py:214-215`），并在 `@bot.on_message(group_id=...)` 时被绑定（`:100`）。`[事实]` 另有 `bot.set_prefix_keywords([...])`（`:217-219`）。

## 5. 数据库

`[事实]` `connect_database(database, is_mysql=False, config=None)`（`database/__init__.py:93`）：

```python
# SQLite（默认）
db = connect_database('resource/amiya.db')

# MySQL
from amiyabot.database import connect_database, MysqlConfig
db = connect_database('amiyadb', is_mysql=True,
                      config=MysqlConfig(host='127.0.0.1', port=3306, user='root', password=''))
```

| 行为 | 说明 | 证据 |
|---|---|---|
| MySQL 会先建库 | `CREATE DATABASE IF NOT EXISTS` | `database/__init__.py:100` |
| MySQL 自动重连 | `ReconnectMySQLDatabase(ReconnectMixin, MySQLDatabase)` | `:28` |
| SQLite 自动建目录 | `create_dir(database, is_file=True)` | `:106`，pragmas `timeout: 30`（`:107`） |
| 配置类型错误 | 抛 `DatabaseConfigError` | `:55-60,95-96` |

`[事实]` `@table` 装饰器**启动时自动建表 + 自动迁移**（`:63-90`）。

### ⚠️ 最重要的运行陷阱

`[事实]` `database/__init__.py:84-85` 会对「表里有、模型里没有」的列执行 **`drop_column`**：

```python
for f in set(table_columns) - set(model_columns):
    migrate_list.append(migrator.drop_column(table_name, f))
```

`[推断]` **改 peewee 模型的字段名或删字段 = 下次启动静默删列丢数据**。详见 [risks.md](risks.md) R-5。`[建议]` 生产环境改 schema 前务必备份数据库文件。

## 6. 目录与运行时产物

`[事实]` `.gitignore:1-19` 揭示了运行时产生的目录：

| 路径 | 来源 | 证据 |
|---|---|---|
| `/resource/` | 资源目录（数据库/图片等） | `.gitignore:3` |
| `/plugins/` | 插件目录 | `.gitignore:4` |
| `/logs/` | 日志 | `.gitignore:8` |
| `/testTemp/` | `test` 适配器的临时图片 | `.gitignore:9`、`adapters/test/server.py:26` |
| `/.idea/`、`/__pycache__/`、`/build/`、`/dist/`、`/venv/`、`/*.egg-info/` | 常规 | `.gitignore:1-10` |
| `main*.py`、`test*.json` | 用户脚本（不入库） | `.gitignore:18-19` |

`[事实]` 日志落点：`LOG_FILE_SAVE_PATH/bots/<appid>` —— `handler/messageHandler.py:7,21` 用 `amiyalog` 的 `LOG_FILE_SAVE_PATH` 常量，按 appid 分文件。

`[事实]` `adapters/test/server.py:36-38` 退出时会 `shutil.rmtree('testTemp')` 清理。

`[事实]` QQ 群适配器会 `create_dir(options.resource_path)` 与 `create_dir(path, is_file=True)`（`qqGroup/builder.py:78,105`）——`[推断]` 资源目录由适配器 builder 选项决定。

## 7. 常见错误与解决

`[事实]` / `[推断]` 混合，按「报错信息 → 原因 → 解决」组织：

| 现象 | 原因 | 证据 | 解决 |
|---|---|---|---|
| `ModuleNotFoundError: No module named 'playwright'` | playwright 是**急切导入**的强制依赖 | `browserService/__init__.py:1` → `amiyabot/__init__.py:30` | `pip install playwright`（**不需要** `playwright install`） |
| `AttributeError: module 'amiyabot' has no attribute '__version__'` | **源码无 `__version__`** | `grep -rn "__version__"` 无输出 | 用 `pip show amiyabot` 或 `importlib.metadata.version` |
| 构建时卡住等待输入 / `EOFError` | `setup.py:68` 的交互式 `input()` | `setup.py:68` | 加 `--auto-increment-version`（`setup.py:50-53`），或直接用 `pip install -e .` |
| 构建时报连不上 PyPI | 版本号来自构建期联网 | `setup.py:18` | 需可访问 `pypi.python.org`；离线环境无法构建 |
| `ModuleNotFoundError: No module named 'wheel'` | `setup.py:6` 硬依赖 `wheel`，但未声明 | `setup.py:6`；`requirements.txt` 无 wheel | `pip install wheel` |
| `OSError: cannot open resource`（字体） | `_assets` 字体路径不对 | `imageCreator.py:15`、`:46` | 确认安装后 `amiyabot/_assets/font/HarmonyOS_Sans_SC.ttf` 存在（实测 wheel 内**存在**） |
| `Chain.markdown()` 渲染空白/报错 | `template.html` 找不到 | `messageChain/__init__.py:18,190` | 同上，确认 `amiyabot/_assets/markdown/template.html` 存在（实测 wheel 内**存在**） |
| 启动后每 10 秒重连、刷日志 | 适配器连不上服务端，重连**无上限无退避** | `kook/__init__.py:46-48` 等 5 处 | 检查适配器 host/port 与目标服务；这是设计行为，不会放弃 |
| QQ 群偶发短暂卡顿（首次或临近 token 过期时） | `headers` property 内同步 `requests` 刷新 token；`timeout=3` 为**上限** | `qqGroup/api.py:19-33` | **已知设计约束，非缺陷**：`:19` 缓存判定使其并非每次执行，且请求耗时很短。`[建议]` 若需消除，须保持 `headers` **同步**契约、把刷新移到后台任务（[risks.md](risks.md) R-15） |
| 数据库某列数据突然消失 | `@table` 自动 `drop_column` | `database/__init__.py:84-85` | 改模型字段名导致；先备份（[risks.md](risks.md) R-5） |
| `git status` 出现 `requirements.txt` 改动 | `setup.py:91-92` 导入时写回排序结果 | `setup.py:91-92` | `git checkout requirements.txt`；避免直接跑 `setup.py` |
| `assert plugin_id not in self.plugins` 失败 | 重复安装同一 plugin_id | `factory/__init__.py:286` | 先 `uninstall_plugin(id)`（`:297`） |
| `assert not self.__ready, 'MultipleAccounts already started'` | `MultipleAccounts.start()` 被调两次 | `amiyabot/__init__.py:129` | 只调一次 |
| `WaitEventOutOfFocus` | `wait_channel()` 的 focus 消息 id 不匹配 | `waitEvent.py` 异常类；`amiyabot/__init__.py:86` 已列入忽略 | 属正常控制流，已被框架忽略 |

## 8. 排障检查清单

`[建议]` 按顺序执行：

```bash
# 1. 包能导入吗（依赖齐全、无语法错）
python -c "import amiyabot; print('import ok')"

# 2. 装的是哪个版本（源码查不到 __version__）
pip show amiyabot | head -3

# 3. 依赖是否齐全
pip check

# 4. 与 CI 一致的 lint
pylint amiyabot --rcfile=pylint.conf

# 5. 资源文件在不在
python -c "import amiyabot,os; p=os.path.dirname(amiyabot.__file__); print(os.path.exists(os.path.join(p,'_assets','font','HarmonyOS_Sans_SC.ttf')))"

# 6. git 工作区是否干净（排除 setup.py 副作用）
git status --short
```

`[事实]` 第 5 步依据运行时实际使用的路径（`imageCreator.py:15` 用 `../../_assets/font/...`，即 `<pkg>/_assets/font/...`）。

## 9. 明确不要做的事（本次任务约束）

`[事实]` 依据任务约束，以下操作**本次均未执行、也不应随意执行**：

- ❌ 不要跑全量 `pytest` / `tox` / `nox` / `pre-commit` —— 项目根本没配置（见 [testing-quality.md](testing-quality.md)）
- ❌ 不要构建或发布：`python setup.py bdist_wheel`、`twine upload`、`bash scripts/publish.sh`
- ❌ 不要向 `master` push —— 会**自动发布到正式 PyPI**（[risks.md](risks.md) R-3）
- ❌ 不要在生产库上改 peewee 模型字段名（自动删列，[risks.md](risks.md) R-5）
- ❌ 不要把 `test` 适配器的 host 设为 `0.0.0.0`（无鉴权，[risks.md](risks.md) R-17）

## 相关文档

- 依赖与安装细节 → [dependencies.md](dependencies.md)
- 发布流程 → [packaging-release.md](packaging-release.md)
- 风险总表 → [risks.md](risks.md)
