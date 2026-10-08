# 依赖（dependencies）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。

## 1. 一览

`[事实]` 依赖**全部写在 `requirements.txt`**（13 行），由 `setup.py` 读取后作为 `install_requires`：

```python
# setup.py:88-92
with open('requirements.txt', mode='r', encoding='utf-8') as req:
    requirements = sorted(req.read().lower().strip('\n').split('\n'))

with open('requirements.txt', mode='w', encoding='utf-8') as req:
    req.write('\n'.join(requirements))
```

`[事实]` **没有 `pyproject.toml` / `setup.cfg`**，所以 `project.dependencies` / `install_requires` / `extras_require` 均不存在，**项目没有任何 extras / optional-dependencies**：

```
$ grep -rn "extras_require\|optional-dependencies" setup.py
（无输出）
```

`[建议]` `[事实]` 注意 `setup.py:91-92` 会把排序后的依赖**写回 `requirements.txt`** —— `import setup.py`（或任何构建）都会修改工作区文件内容（仅重排序）。`[推断]` 这是构建脚本的副作用，会污染 git status。见 [risks.md](risks.md) R-11。

## 2. 运行时依赖（全部为强制依赖）

`[事实]` `requirements.txt:1-13`：

| # | 依赖 | 约束 | 用途 | 证据 |
|---|---|---|---|---|
| 1 | `amiyahttp` | `~=0.0.7` | HTTP 服务端（test 适配器） | `adapters/test/server.py:1` 侧 |
| 2 | `amiyalog` | `~=0.0.3` | 日志（`logger`、`LoggerManager`、`log.catch`） | `factory/__init__.py:7`、`adapters/__init__.py:12` |
| 3 | `amiyautils` | `~=0.0.4` | 工具（`random_code`、`import_module`、`temp_sys_path`、`argv`） | `amiyabot/__init__.py:8`、`factory/__init__.py:8` |
| 4 | `jieba` | `~=0.42.1` | 中文分词（`Message.text_words`） | `amiyabot/__init__.py:1,44` |
| 5 | `aiohttp` | `~=3.12.13` | 异步 HTTP（下载） | `network/download.py:3` |
| 6 | `Pillow` | `~=11.2.1` | 图片生成 | `builtin/lib/imageCreator.py:6` |
| 7 | `playwright` | `~=1.53.0` | 浏览器渲染（`Chain.html/markdown`） | `browserService/__init__.py:1` |
| 8 | `graiax-silkcoder` | `~=0.3.6` | 语音编码（silk） | `adapters/mirai/api.py` 侧 |
| 9 | `audioop-lts` | `~=0.2.1; python_version>='3.13'` | 补 3.13 移除的 `audioop` | `requirements.txt:9` |
| 10 | `apscheduler` | `~=3.11.0` | 定时任务 | `timedTask/scheduler.py:2-4` |
| 11 | `dhash` | `~=1.4` | 图片感知哈希 | 适配器侧 |
| 12 | `peewee` | `~=3.18.1` | ORM | `database/__init__.py:1` |
| 13 | `pymysql` | `~=1.1.1` | MySQL 驱动 | `database/__init__.py:2` |

`[事实]` 另有**未在 `requirements.txt` 声明但被直接 import 的依赖**（间接依赖或隐含依赖）：

| 包 | import 位置 | 状态 |
|---|---|---|
| `websockets` | `adapters/__init__.py:4`（`websockets.legacy.client`） | `[事实]` 未在 requirements 中；`[推断]` 作为某依赖的传递依赖被装上 |
| `requests` | `network/download.py:4`、`qqGroup/api.py:3` | `[事实]` 未声明 |
| `certifi` | `network/download.py:2` | `[事实]` 未声明 |
| `pydantic` | `network/httpServer.py:3` | `[事实]` 未声明 |
| `wheel` | `setup.py:6` | `[事实]` 构建期依赖，未声明 |
| `black` / `pylint` | `scripts/*.sh` | `[事实]` 开发工具，未声明 |

`[建议]` 见 [risks.md](risks.md) R-12。`[推断]` 这些能工作是因为它们恰好是已声明依赖的传递依赖（如 `amiyahttp` 带 `websockets`/`pydantic`），一旦上游改依赖树就会 `ImportError`。这是典型的隐式依赖风险。

## 3. 开发依赖

`[事实]` **没有开发依赖声明**：

| 文件 | 状态 |
|---|---|
| `requirements-dev.txt` / `requirements/*.txt` | 不存在 |
| `pyproject.toml` `[project.optional-dependencies]` | 不存在（无 pyproject） |
| `extras_require` | 不存在 |

`[事实]` 开发工具靠**脚本硬编码调用**：

| 脚本 | 内容 | 证据 |
|---|---|---|
| `scripts/black.sh` | `black amiyabot --skip-string-normalization --line-length 120` | `:1` |
| `scripts/pylint.sh` | `pylint amiyabot --rcfile=pylint.conf` | `:1` |
| `scripts/publish.sh` | `twine upload dist/*` | `:1` |

`[事实]` CI 装的是 `pylint`（`pylint.yml:21`）和 `setuptools wheel twine`（`pypi.yml:27`）；**CI 从不安装 `black`**。`[推断]` 格式化靠本地手动跑，无 CI 强制。

## 4. 依赖是否锁定

`[事实]` **完全没有锁定**：

- 无 `requirements.lock`、`uv.lock`、`poetry.lock`、`Pipfile.lock`（`ls` 均不存在）。
- 约束全部用 `~=`（兼容版本），即允许 patch 级（`~=X.Y.Z` 实际允许 `>=X.Y.Z, ==X.*`）自动升级。
- 无 hash 校验。

`[事实]` 实测一处**本地与线上已不一致**：

| 依赖 | 本仓库 `requirements.txt:3` | PyPI 2.1.0 元数据 `requires_dist` |
|---|---|---|
| `amiyautils` | `amiyautils~=0.0.4` | `amiyautils~=0.0.5` |

`[事实]` 该差异来自 PyPI JSON 的 `info.requires_dist`。`[推断]` 说明**当前 master 的依赖声明落后于已发布版本**——本地构建出的包会要求 `amiyautils~=0.0.4`，与 `2.1.0` 的 `~=0.0.5` 不同。

`[不确定]` 该差异是否会导致实际问题（`~=0.0.4` 允许 `0.0.4` 与 `0.0.5`？—— 不，`~=0.0.4` 等价于 `>=0.0.4, ==0.0.*`，实际**包含 0.0.5**）。`[推断]` 因此运行时影响有限，但**声明与发布产物不一致本身就是配置漂移证据**。

`[建议]` 见 [risks.md](risks.md) R-13。

## 5. 风险依赖

`[事实]` 按风险性质分类：

### 5.1 自有生态包（最大单点风险）

`amiyahttp`、`amiyalog`、`amiyautils` 三个 `amiya*` 包是**同作者的前置生态**，被核心路径重度依赖：

- `amiyabot/__init__.py:7-8` 顶层即导入 `amiyalog.logger` 与 `amiyautils.random_code`。
- `factory/__init__.py:7-8` 依赖 `amiyalog.logger`、`amiyautils` 的 4 个函数。
- `adapters/__init__.py:12` 依赖 `LoggerManager`。

`[推断]` 风险：
1. `~=0.0.x` 说明三个包都**处于 0.0.x 早期阶段**（未到 1.0，无 API 稳定性承诺）。
2. `[事实]` 它们**不在本仓库**，无法在本次只读探索中审计。
3. `[推断]` 任何 `amiya*` 包的 break change 会直接打断框架，而版本约束 `~=0.0.3` 这类只锁 `0.0.*`，**允许自动升到 0.0.9**。
4. `[事实]` `amiyalog` 的 `log.catch()` 被用作**全局异常处理骨架**（`amiyabot/__init__.py:84`、`messageHandler.py:129`）——语义行为依赖外部包。

`[建议]` 这是本项目依赖侧最需要关注的点：核心异常语义外包给了 0.0.x 包。

### 5.2 体积/安装重依赖

`[事实]` `playwright~=1.53.0`（`requirements.txt:7`）是**强制运行时依赖**，且是**急切导入**：

```
$ grep -rn "playwright" --include="*.py" amiyabot/
browserService/launchConfig.py:2:  from playwright.async_api import ...
browserService/__init__.py:1:      from playwright.async_api import async_playwright, ...
browserService/pageContext.py:1:   from playwright.async_api import Page
browserService/pagePool.py:3:      from playwright.async_api import ViewportSize
```

`[事实]` 导入链：`amiyabot/__init__.py:30` → `browserService/__init__.py:1`。**第二条路径**：`messageChain/element.py:6` `from ...browserService import *` → `messageChain/__init__.py:6` → `amiyabot/__init__.py:33`。

`[推断]` 后果：**`import amiyabot` 强制要求安装 `playwright` Python 包**，即便用户从不用 `Chain.html/markdown`。`[事实]` 浏览器**二进制**只在运行时才需要（`browserService/__init__.py:28` 的 `launch()`、`element.py:106`），即 `playwright install chromium` 是可选运行时步骤。`[事实]` `AmiyaBot.start(launch_browser=False)` 默认不启动浏览器（`amiyabot/__init__.py:66-70`）。

`[建议]` 没有 `try/except ImportError` 降级，也没有 `TYPE_CHECKING` 守卫。见 [risks.md](risks.md) R-14。

### 5.3 版本约束过宽的相关依赖

`[事实]` 全部约束均为 `~=` 兼容式。`[推断]` 对 0.x 包（`amiya*`、`graiax-silkcoder`）而言 `~=0.0.x` 语义弱：允许同 minor 内自动升版。

`[事实]` `aiohttp~=3.12.13` 是较严的约束（锁 3.12.x）；`peewee~=3.18.1`、`pymysql~=1.1.1`、`Pillow~=11.2.1` 同样锁 minor。

### 5.4 已确认的同步调用阻塞风险

`[事实]` `requests`（同步库）在异步上下文中被用于网络：

```python
# amiyabot/adapters/tencent/qqGroup/api.py:17-33  —— headers 是 property
@property
def headers(self):
    if not self.access_token or self.expires_time - time.time() <= 60:
        res = requests.post(url='https://bots.qq.com/app/getAppAccessToken',
                            ..., timeout=3)
```

`[事实]` 该 property 被 `qqGuild/api.py:36-63` 的异步 `get`/`post`/`request` 读取。**但 `:19` 的缓存判定使请求并非每次执行**——仅首次或剩余有效期 ≤ 60 秒时才发（`qqGroup/api.py:19`，`timeout=3` 为超时上限而非实际耗时）。`[事实]` 该项目作者已确认「请求并非每次执行、耗时很短」，决定保持现状。见 [risks.md](risks.md) R-15（**已知设计约束**）。

`[事实]` `network/download.py:18-50` 的 `download_sync` 也用 `requests`，但另提供 `download_async`（`:53`）用 `aiohttp`；`[事实]` 适配器中用的是异步版（`mirai/api.py:7` 导入 `download_async`）。

## 6. 依赖相关证据命令

```
cat requirements.txt
grep -rn "^import \|^from " --include="*.py" amiyabot/ | grep -E "websockets|requests|certifi|pydantic"
grep -rn "playwright" --include="*.py" amiyabot/
grep -n "install_requires\|extras_require" setup.py
curl -s https://pypi.org/pypi/amiyabot/json   # → info.requires_dist
ls requirements*.txt *.lock poetry.lock uv.lock
```

## 相关文档

- 打包与发布 → [packaging-release.md](packaging-release.md)
- 运行环境搭建 → [runbook.md](runbook.md)
- 风险排序 → [risks.md](risks.md)
