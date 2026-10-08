# 模块：内置能力库（builtin/lib + builtin/messageChain + database）

> 证据：`文件:行`。约定 `[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> 涉及：`builtin/lib/eventBus.py`(45)、`imageCreator.py`(197)、`timedTask/`、`browserService/`、`builtin/messageChain/`(570)、`database/__init__.py`(131)。

## 1. 职责

`[事实]` 四个相对独立的「能力」子系统：

| 子系统 | 职责 | 文件 |
|---|---|---|
| `messageChain` | 出站回复消息 DSL | `__init__.py`(222)、`element.py`(241)、`keyboard.py`(107) |
| `lib/eventBus` | 进程内发布/订阅 | `eventBus.py`(45) |
| `lib/timedTask` | apscheduler 定时任务封装 | `__init__.py`(57)、`scheduler.py`(43) |
| `lib/browserService` | playwright 浏览器与页面池 | `__init__.py`(83)、`launchConfig.py`(33)、`pagePool.py`(98)、`pageContext.py` |
| `lib/imageCreator` | Pillow 文字转图片 | `imageCreator.py`(197) |
| `database` | peewee ORM + 自动迁移 | `__init__.py`(131) |

`[事实]` `builtin/__init__.py` 与 `builtin/lib/__init__.py` 均为 **0 行空文件**，不承担 re-export 职责。

## 2. `messageChain` —— 出站 DSL

### 2.1 `Chain`（`messageChain/__init__.py:21`）

`[事实]` 构造：`Chain(data=None, at=True, reference=False, chain_builder=None)`（`:22-28`）。`[事实]` 若 `data and at and not data.is_direct`，自动 `.at(enter=True)`（`:42-43`）——**私信不自动 at**。`[事实]` 默认 `ChainBuilder()`，`use_default_builder` 标记（`:45-46`）；`builder` setter 会把新 builder 下发给链上已有元素（`:52-59`）。

`[事实]` 全部链式方法（均 `return self`）：

| 方法 | 行 | 产出 | 方法 | 行 | 产出 |
|---|---|---|---|---|---|
| `.at()` | `61` | `At` | `.voice()` | `151` | `Voice` |
| `.at_all()` | `71` | `AtAll` | `.video()` | `155` | `Video` |
| `.tag()` | `75` | `Tag` | `.html()` | `159` | `Html` |
| `.face()` | `79` | `Face` | `.markdown()` | `181` | → `.html(md_template,...)` |
| `.text()` | `83` | `Text`/`Face` 混排 | `.markdown_template()` | `202` | `Markdown` |
| `.text_image()` | `114` | 调 `create_image` → `.image` | `.embed()` | `212` | `Embed` |
| `.image()` | `134` | `Image` | `.ark()` | `216` | `Ark` |
| | | | `.extend()` | `220` | `Extend` |

`[事实]` `.text()` 支持内联颜色标记 `[cl 文字@#ff0000 cle]` → `text_image`（`:83-112`）。

### 2.2 元素与 Builder（`messageChain/element.py`）

`[事实]` 14 个元素 dataclass：`At:30`、`AtAll:35`、`Tag:39`、`Face:44`、`Text:49`、`Image:54`、`Voice:68`、`Video:82`、`Html:95`、`Embed:156`、`Ark:174`、`Markdown:188`、`Extend:212`、`CQCode:222`；联合类型 `CHAIN_ITEM:226`、`CHAIN_LIST:241`。

`[事实]` **`ChainBuilder` 定义在 `element.py:12`，不在 `__init__.py`**。4 个可覆写 classmethod 钩子：`get_image:13`、`get_voice:17`、`get_video:21`、`on_page_rendered:25`，默认原样返回。

`[事实]` `Image`/`Voice`/`Video` 各有异步 `get()` 走 builder 钩子（`element.py:59,73,86`）。`[事实]` `Html.create_html_image()`（`:104-152`）是**唯一调用浏览器服务**的地方（`:106`），失败被 `log.error` 吞掉后返回 `None`（`:118-120`）。

`[事实]` `InlineKeyboard` 在 `keyboard.py`；行/按钮上限各 5（`:64-65,98-99`），`dict()` 走 `asdict`（`:106-107`）。

### 2.3 配置常量

`[事实]` `ChainConfig`（`__init__.py:16-18`）：

```python
max_length = argv('text-max-length', int) or 100          # :17
md_template = os.path.join(cur_file_folder, '../../_assets/markdown/template.html')  # :18
```

`[事实]` `[建议]` `md_template` 路径**无存在性检查**，缺文件时表现为渲染失败。详见 [../risks.md](../risks.md) R-4。

## 3. `lib/eventBus` —— 进程内事件总线

`[事实]` 45 行，实现紧凑。`EventBus`（`:10`）内部 `__subscriber: Dict[EventName, Dict[SubscriberID, Subscriber]]`（`:13`），**以 `id(method)` 为键**（`:28,32,40`）。

| 方法 | 行 | 行为 |
|---|---|---|
| `publish(event_name, data=None)` | `15-21` | 协程用 `asyncio.create_task`，普通函数直接调 |
| `subscribe(event_name, method=None)` | `23-36` | 传 `method` 立即注册；不传则返回装饰器 `register`（`:31-36`） |
| `unsubscribe(event_name, method)` | `38-42` | 按 `id` 删除 |

`[事实]` 单例 `event_bus = EventBus()`（`:45`），由 `amiyabot/__init__.py:28` 导出。`[事实]` 可作 `@event_bus.subscribe('name')` 装饰器用。

`[推断]` 用 `id()` 做键：绑定方法/临时包装对象难以稳定注销；模块级函数与长生命周期对象方法无此问题。

`[建议]` 纯逻辑、无 IO，适合优先补单测。

## 4. `lib/timedTask` —— 定时任务

`[事实]` 基于 **apscheduler**（`scheduler.py:2-4` 导入 `AsyncIOScheduler`/`AsyncIOExecutor`；`requirements.txt:10` = `apscheduler~=3.11.0`）。

`[事实]` `Scheduler(AsyncIOScheduler)`（`scheduler.py:9`）配置：`AsyncIOExecutor`、`coalesce=False`、`max_instances=1`（`:10-18`）；单例 `scheduler`（`:28`）；3 条监听器只做 debug 日志（`:31-43`）。

`[事实]` `Task` dataclass（`timedTask/__init__.py:10-17`）：`func, each, tag, sub_tag, run_when_added, kwargs`。

`[事实]` `TasksControl`（`:20-57`）：

| 方法 | 行 | 行为 |
|---|---|---|
| `start()` | `22-25` | 幂等启动；注册 `SignalHandler.on_shutdown.append(scheduler.shutdown)`（`:24`） |
| `add_timed_task(task)` | `27-45` | `run_when_added` 先 `create_task`（`:29-30`）；`each` 非空用 `interval`（`:32-39`）；否则裸 `add_job`（`:40-45`） |
| `remove_task(tag, sub_tag=None)` | `47-57` | 按 job id 前缀移除 |

`[事实]` job id 统一为 `f'{task.tag}.{task.sub_tag}'`。

`[事实]` 注册链：`@bot.timed_task(each=...)`（`factory/__init__.py:171-205`）→ `Task(...)`（`:191-200`，`sub_tag` 自动带 `key{len}`，`:196`）→ `run_timed_tasks()`（`:210-212`）→ `TasksControl.add_timed_task`。

`[推断]` `add_job` 未做重复 id 保护；`max_instances=1` 只限制**并发实例数**，不防重复 job id，重复注册可能触发 apscheduler `ConflictingIdError`。`[不确定]` 未运行时验证。

## 5. `lib/browserService` —— 浏览器与页面池

`[事实]` `BrowserService`（`__init__.py`）：`launch(config)`（`:20-38`）→ `async_playwright().start()`（`:28`）→ `config.launch_browser`（`:29`）→ `page_pool_size` 非零则建 `PagePool`（`:32-33`）；`close()`（`:40-44`）；`open_page(width,height)`（`:46-65`）。单例 `basic_browser_service`（`:83`）。

`[事实]` `BrowserLaunchConfig`（`launchConfig.py:15-33`）：`browser_type='chromium'`（`:17`）、`page_pool_size` 取自 `argv`（`:9,19`）、`debug` 取自 `argv`（`:20`）；`launch_browser` 用 `getattr(playwright, self.browser_type)` + `headless=not BROWSER_LAUNCH_WITH_HEADED`（`:26-29`）。默认 `1280×720`、渲染等待 `200ms`（`:6-8`）。

`[事实]` `PagePool.acquire_page`（`pagePool.py:35-72`）：队列空且 `size < max_size` 则新建，否则 `await queue.get()`（`:60-62`）；viewport 设置失败且报 "context or browser has been closed" 时 `size -= 1` 并递归重试（`:64-70`）。`release_page`（`:74-89`）清 cookie/storage 后 `goto('about:blank')` 归还。`PagePoolContext.__aexit__` 归还而非关闭（`:92-98`）。

### ⚠️ 急切导入（重要）

`[事实]` **playwright 在模块顶层导入，无延迟/降级**：

```
browserService/__init__.py:1   from playwright.async_api import async_playwright, ConsoleMessage, Error as PageError
browserService/launchConfig.py:2  from playwright.async_api import Browser, BrowserType, BrowserContext, Page, Playwright
browserService/pageContext.py:1   from playwright.async_api import Page
browserService/pagePool.py:3      from playwright.async_api import ViewportSize
```

`[事实]` 到达该模块的**两条路径**：
1. `amiyabot/__init__.py:30` → `browserService/__init__.py:1`
2. `messageChain/element.py:6`（`from ...browserService import *`）→ `messageChain/__init__.py:6` → `amiyabot/__init__.py:33`

`[推断]` 结论：**`import amiyabot` 强制要求安装 `playwright` Python 包**。`[事实]` 但浏览器**二进制**仅运行时需要（`__init__.py:28` 或 `element.py:106`）。`[事实]` `AmiyaBot.start(launch_browser=False)` 默认不启动浏览器（`amiyabot/__init__.py:66-70`）。

`[建议]` 改为函数内惰性导入 + `try/except ImportError` 降级。详见 [../risks.md](../risks.md) R-14。

## 6. `lib/imageCreator` —— 文字转图片

`[事实]` 纯 Pillow，与浏览器/HTML 无关（对比 `Chain.html`）。

`[事实]` `create_image(text='', width=0, height=None, padding=10, max_seat=None, font_size, line_height, color, bgcolor, images=None)`（`:112-123`）→ 返回 **`bytes`**（`:194-197`）。

`[事实]` `FontStyle`（`:14-19`）：

```python
file: str = os.path.join(cur_file_folder, '../../_assets/font/HarmonyOS_Sans_SC.ttf')   # :15
font_size = 15; line_height = 16; color = '#000000'; bgcolor = '#ffffff'
```

`[事实]` `TextParser.__init__` 用 `ImageFont.truetype(FontStyle.file, font_size)`（`:46`）；`__parse`（`:57-95`）支持 `[cl 文字@#ff0000 cle]` 内联颜色（`:59-68`）；`__font_seat` 借 1×1 临时图量宽（`:102-106`）。`[事实]` 自适应宽度 = 文本宽 + padding×2 + 50（`:153`）；高度 = `(line+2) × line_height`（`:156`）。`[事实]` `images` 参数按 `pos` 负值做右/下对齐（`:173-192`）。

`[推断]` 字体缺失时抛 Pillow 的 `OSError: cannot open resource`（`:46`），无友好提示。

## 7. `database` —— ORM 与自动迁移

`[事实]` 双后端：

| 后端 | 构造 | 证据 |
|---|---|---|
| SQLite（默认） | `SqliteDatabase(database, pragmas={'timeout': 30})` | `:107` |
| MySQL | `ReconnectMySQLDatabase(ReconnectMixin, MySQLDatabase, ABC)` | `:28`、`:104` |

`[事实]` `MysqlConfig` dataclass（`:12-25`）：`host/port/user/password`，`dict()` 方法（`:19-25`）。

`[事实]` `connect_database`（`:93-107`）：MySQL 分支先 `CREATE DATABASE IF NOT EXISTS ... CHARACTER SET utf8`（`:100`）再连接；非 MySQL 分支 `create_dir(database, is_file=True)`（`:106`）。类型错误抛 `DatabaseConfigError`（`:55-60,95-96`）。

`[事实]` `ModelClass`（`:31`）提供 `batch_insert`（`:33-38`，按 `chunk_size=200` 分块）与 `insert_or_update`（`:41-52`，MySQL 时带 `conflict_target`）。

`[事实]` 工具函数：`convert_model`（`:110`）、`query_to_list`（`:120`）、`select_for_paginate`（`:124-131`，返回 `{list, total}`）。

### ⚠️ `@table` 自动迁移（最危险）

`[事实]` `table(cls)`（`:63-90`）：`create_table()`（`:70`）→ 读 `select * ... limit 1` 的 `description` 得实际列（`:72-75`）→ 与模型字段做**双向差集**：

```python
for f in set(model_columns) - set(table_columns):
    migrate_list.append(migrator.add_column(table_name, f, getattr(cls, f)))   # :80-81
for f in set(table_columns) - set(model_columns):
    migrate_list.append(migrator.drop_column(table_name, f))                   # :84-85
if migrate_list:
    migrate(*tuple(migrate_list))                                             # :88
```

`[事实]` 表名由 `pascal_case_to_snake_case(cls.__name__)` 生成（`:67`）。

`[推断]` **改字段名或删字段 = 下次启动静默 `DROP COLUMN` 丢数据**，无备份、无确认、无日志。这是全项目**最危险的设计**。详见 [../risks.md](../risks.md) R-5。

`[事实]` 字段类型判定用 `type(n) in [peewee.FieldAccessor, peewee.ForeignKeyAccessor]`（`:74`）。

## 8. 依赖

`[事实]` `messageChain`：`re`、`amiyabot.builtin.message`、`imageCreator`、`browserService`（间接）。
`[事实]` `eventBus`：仅 `typing`+`asyncio`（最内聚）。
`[事实]` `timedTask`：`apscheduler`、`amiyalog`、`SignalHandler`。
`[事实]` `browserService`：`playwright`、`amiyautils.argv`、`amiyalog`。
`[事实]` `imageCreator`：`Pillow`、`re`/`os`/`math`。
`[事实]` `database`：`peewee`（含 `playhouse.migrate`/`shortcuts`）、`pymysql`、`amiyautils`。

## 9. 数据流

```
出站渲染
  Chain.text()  ──────────────────> Text 元素
  Chain.text_image() ─> create_image(bytes) ─> .image(...)      imageCreator.py:112
  Chain.html()/markdown()
     └─> Html.create_html_image()   element.py:104
           └─> basic_browser_service.open_page()   browserService/__init__.py:46
                 └─> PagePool.acquire_page()       pagePool.py:35
                       └─> playwright page.goto + screenshot
     （失败 → log.error 吞掉 → 返回 None，element.py:118-120）

定时任务
  @bot.timed_task(each=N)   factory/__init__.py:171
    └─> Task(func, each, tag, sub_tag)          :191-200
          └─> run_timed_tasks()                 :210
                └─> TasksControl.add_timed_task timedTask/__init__.py:27
                      └─> scheduler.add_job(interval)   :32-39

事件总线
  @event_bus.subscribe('x')  eventBus.py:23
  event_bus.publish('x', d)  :15  → 协程走 create_task，普通函数直接调

数据库
  connect_database(...)  database/__init__.py:93
    └─> @table 装饰的 Model
          └─> create_table + 差集比对 + add/drop_column   :63-90
```

## 10. 测试

`[事实]` **无自动化测试**。

`[建议]` 优先补测（纯逻辑/无副作用）：

| 目标 | 位置 | 测什么 |
|---|---|---|
| `create_image` | `imageCreator.py:112` | 输出尺寸、颜色标记解析 |
| `EventBus.publish/subscribe/unsubscribe` | `eventBus.py:15,23,38` | 订阅分发、id 键语义 |
| `Chain` 链式构造 | `messageChain/__init__.py:21-222` | 元素顺序、自动 at、私信不 at |
| `Chain.text()` 颜色标记 | `__init__.py:83` | `[cl x@#ff0000 cle]` 解析 |
| `InlineKeyboard` 上限 | `keyboard.py:64,98` | 5 行/5 按钮边界 |
| `convert_model`/`select_for_paginate` | `database/__init__.py:110,124` | 需内存 SQLite |

`[建议]` `create_image` 与 `Chain` 链式 API 是**用户最常接触**的部分，性价比最高。

## 11. 风险 / TODO

| 项 | 说明 | 证据 |
|---|---|---|
| **R-5** | `@table` 自动 `drop_column` 静默删列丢数据 | `database/__init__.py:84-85` |
| **R-14** | playwright 急切导入，强制安装 | `browserService/__init__.py:1` |
| **R-4** | `md_template` 路径无存在性检查 | `messageChain/__init__.py:18` |
| R-t | `FontStyle.file` 无存在性检查，缺文件报 Pillow 原始错误 | `imageCreator.py:15,46` |
| R-u | `add_job` 无重复 id 保护（`[不确定]` 是否抛 `ConflictingIdError`） | `timedTask/__init__.py:32-45` |
| R-v | `Html` 渲染失败静默返回 `None`（`log.error` 吞掉） | `element.py:118-120` |
| R-w | `EventBus` 用 `id(method)` 做键，绑定方法难注销 | `eventBus.py:28,32,40` |
| R-x | `PagePool` 递归重试（`:64-70`）无深度上限 | `pagePool.py:64-70` |
| `[不确定]` | `create_dir(database, is_file=True)` 对 SQLite 的内存库（`':memory:'`）行为未验证 | `database/__init__.py:106` |
| TODO | `builtin/__init__.py`、`builtin/lib/__init__.py` 为 0 行空文件，不做 re-export | — |
| TODO | `browserService` 无降级路径，无法「不装 playwright 用核心功能」 | — |

## 12. 相关文档

- 架构与调用链 → [../architecture.md](../architecture.md)
- 依赖风险 → [../dependencies.md](../dependencies.md)
- 风险总表 → [../risks.md](../risks.md)
