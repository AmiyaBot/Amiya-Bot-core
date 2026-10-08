# 模块：适配器（amiyabot/adapters）

> 证据：`文件:行`。约定 `[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> 规模：适配器共约 3,400 行，是仓库最大的子系统（`adapters/` 下 33 个 `.py`）。

## 1. 职责

`[事实]` 把各聊天平台的协议差异**收敛到统一契约**，使上层 handler 无需感知平台：

- 入站：平台 payload → `Message`/`Event`
- 出站：`Chain` → 平台 API 调用
- 连接：维护 WebSocket 长连接与心跳

## 2. 适配器契约

### 2.1 `BotAdapterProtocol`（`adapters/__init__.py:19`）

`[事实]` **不是真正的 ABC**——未继承 `abc.ABC`（`:19`），因此 `@abc.abstractmethod` 不被强制：

| 待实现方法 | 行 |
|---|---|
| `close()` | `:72-77` |
| `start(handler)` | `:79-86` |
| `send_chain_message(chain, is_sync=False)` | `:88-97` |
| `build_active_message_chain(chain, user_id, channel_id, direct_src_guild_id)` | `:99-112` |
| `recall_message(message_id, data=None)` | `:114-122` |

`[事实]` 基类提供的现成能力：

| 成员 | 行 | 说明 |
|---|---|---|
| `__init__(appid, token, private=False)` | `:20-38` | 初始化 `host`/`ws_port`/`http_port`/`log`/`bot` 等 |
| `set_alive(status)` | `:43-44` | |
| `send_message(chain, user_id, channel_id, direct_src_guild_id)` | `:46-58` | 主动发送：先 build chain，再包 `processing_context` |
| `get_websocket_connection(mark, url, headers)` | `:60-66` | 异步上下文管理器，吞掉 `ignore_errors` |
| `api` property | `:68-70` | 默认返回空 `BotInstanceAPIProtocol()` |

`[事实]` `HANDLER_TYPE` 定义于 `:16`。

### 2.2 `BotInstanceAPIProtocol`（`adapters/apiProtocol.py:6`）

`[事实]` 二层契约：`get`（`:7`）、`post`（`:11`）、`request`（`:15`）为抽象；`get_user_avatar` 有默认实现返回 `''`（`:19-20`）。`[事实]` `UnsupportedMethod` 异常定义于 `:23`。

### 2.3 `WebSocketConnect`（`adapters/__init__.py:130-169`）

`[事实]` 统一 WS 连接封装，`ignore_errors` 元组含 7 类（`socket.gaierror`、`asyncio.CancelledError`、`TimeoutError`、`ConnectionClosedError`、`ConnectionClosedOK`、`InvalidStatusCode`、`ManualCloseException`）（`:131-139`）。`ManualCloseException` 定义于 `:125`。

`[事实]` `[建议]` 连接失败只 `log.error` 不抛出（`:156-159`），`__aenter__` 可能返回 `None`（`:150` 返回类型为 `Optional`）——调用方需判空。

### 2.4 ⚠️ `headers` 是不可改动的**同步**契约

`[事实]` **改动前必读。** `headers` 在适配器层是一个跨 5 个实现、共 **15 处读取点** 的**统一同步契约**，由两种机制实现：

| 实现方式 | 位置 |
|---|---|
| `@property def headers` | `kook/api.py:17`、`qqGuild/api.py:29`、`qqGroup/api.py:18`、`onebot/v11/api.py:12`、`onebot/v12/api.py:12` |
| 普通实例属性 | `adapters/__init__.py:33`、`onebot/v11/__init__.py:37`、`onebot/v12/__init__.py:37` |

`[事实]` 读取点（全部按**同步取值**使用）：
- `kook/api.py:24,32,40,67`
- `qqGuild/api.py:40,48,54,62`
- `onebot/v11/api.py:19,27,35`
- `onebot/v12/api.py:26`
- `adapters/__init__.py:154`：`websockets.connect(..., additional_headers=self.headers)`

**约束** `[推断]` 两条必须遵守：

1. **必须保持同步。** 若单独把某一个适配器（如 `qqGroup`）改为 `async def headers`，同名属性在 5 个实现间语义分裂（协程 vs dict）。任何按 `adapter.api.headers` 的统一写法——**包括第三方插件**——都会在该适配器上拿到 coroutine 而报错，造成**大面积用户故障**。
2. **必须可以无副作用地重复读取。** `headers` 被上述 15 处直接读取，任何一次额外读取都会触发其内部逻辑。

`[事实]` 已知的技术债：`qqGroup/api.py:17-45` 的 `headers` 是唯一在此契约下**带网络 I/O 与状态写入**（`:36-37` 写 `access_token`/`expires_time`）的实现——因为 QQ 群的 token 需请求换取，而契约又要求同步属性，二者本质冲突，属**设计妥协**。

`[事实]` `:19` 的缓存判定（`not access_token or expires_time - time.time() <= 60`）使请求**并非每次执行**，且 `timeout=3` 是超时上限而非实际耗时，故实际影响有限。

`[事实]` **决策记录**：项目作者已确认保持现状、不改动代码。详见 [../risks.md](../risks.md) R-15。

`[建议]` 若将来确需消除事件循环占用，**唯一不破坏契约**的方向是：让 `headers` 退化为**纯读缓存的同步 property**，把刷新移到后台异步任务（可复用 `TasksControl.add_timed_task`，`builtin/lib/timedTask/__init__.py:27`）。

## 3. 适配器全表

`[事实]` 连接方式除注明外均为**主动 WebSocket 客户端**（`websockets.connect`，`adapters/__init__.py:154`）+ HTTP 发送：

| 适配器 | import 路径 | 类名 | 类定义 | 工厂函数 |
|---|---|---|---|---|
| KOOK | `adapters.kook` | `KOOKBotInstance` | `kook/__init__.py:17` | **无**（直接用类） |
| Mirai | `adapters.mirai` | `MiraiBotInstance` | `mirai/__init__.py:26` | `mirai_api_http`（`:19`） |
| CQHttp | `adapters.cqhttp` | `CQHttpBotInstance`（继承 OneBot11） | `cqhttp/__init__.py:14` | `cq_http`（`:7`） |
| OneBot v11 | `adapters.onebot.v11` | `OneBot11Instance` | `onebot/v11/__init__.py:25` | `onebot11`（`:18`） |
| OneBot v12 | `adapters.onebot.v12` | `OneBot12Instance` | `onebot/v12/__init__.py:25` | `onebot12`（`:18`） |
| ComWeChat | `adapters.comwechat` | `ComWeChatBotInstance`（继承 OneBot12） | `comwechat/__init__.py:18` | `com_wechat`（`:11`） |
| QQ 频道 | `adapters.tencent.qqGuild` | `QQGuildBotInstance` | `tencent/qqGuild/__init__.py:28` | `qq_guild_shards`（`:19`） |
| QQ 频道沙箱 | 同上 | `QQGuildSandboxBotInstance` | `tencent/qqGuild/__init__.py:245` | 同上（`sandbox=True`） |
| QQ 群 | `adapters.tencent.qqGroup` | `QQGroupBotInstance` | `tencent/qqGroup/__init__.py:19` | `qq_group`（`:104`） |
| QQ 全域 | `adapters.tencent.qqGlobal` | `QQGlobalBotInstance` | `tencent/qqGlobal/__init__.py:8` | `qq_global`（`:35`） |
| 测试 | `adapters.test` | `TestInstance` | `test/__init__.py:27` | `test_instance`（`:14`） |
| ~~废弃别名~~ | ~~`adapters.tencent`~~ | ~~`TencentBotInstance` / `TencentSandboxBotInstance`~~ → **已移除**（原 `tencent/__init__.py:4,7`）；该文件现仅剩 re-export | — |

`[事实]` `adapters/onebot/__init__.py` 是 **0 行空文件**。

### 3.1 默认适配器

`[事实]` **QQ 频道**：`amiyabot/__init__.py:53` `adapter: typing.Type[BotAdapterProtocol] = QQGuildBotInstance`。

`[推断]` 影响：
- 不传 `adapter` ⇒ 连腾讯官方 API（`qqGuild/api.py:34` `https://api.sgroup.qq.com`），需有效 appid/token。
- `[事实]` `factory/__init__.py:33` 统一以 `adapter(appid, token)` 调用；QQ 频道构造器签名恰为 `(appid, token, shard_index=0, shards=1)`（`qqGuild/__init__.py:29`），因此它是**唯一能用裸类充当 adapter 的**。
- `[事实]` 参数注解 `Type[BotAdapterProtocol]`（`factory/__init__.py:22`）与实际传入的闭包工厂**类型不符**。

### 3.2 三种构造风格并存

`[事实]` `[建议]` 不一致：

| 风格 | 适配器 |
|---|---|
| 模块级闭包工厂 | `mirai_api_http`、`cq_http`、`onebot11`、`onebot12`、`com_wechat`、`qq_guild_shards`、`test_instance` |
| 类属性 `build_adapter` | `qq_group`（`qqGroup/__init__.py:38-55`）、`qq_global` |
| 裸类 | `KOOKBotInstance` |

## 4. 平台实现要点

### 4.1 KOOK（`adapters/kook/`，约 400 行）

`[事实]` `KOOKAPI`（`api.py:11`）硬编码 `https://www.kookapp.cn/api/v3`（`:13`）。`[事实]` `WSPayload`（`__init__.py:212`）处理平台协议；`KOOKMessageCallback`（`builder.py:9`）；`RolePermissionCache`（`package.py:8`）。`[事实]` 心跳在 `__init__.py:113-131`（`heartbeat_interval` + `wait_heartbeat`）。

### 4.2 Mirai（`adapters/mirai/`，约 500 行）

`[事实]` 文件最全的适配器：`__init__.py`、`api.py`、`builder.py`、`forwardMessage.py`、`package.py`、`payload.py`。`[事实]` `MiraiPostPayload`（`payload.py:7`）是基类，派生出 `WebsocketAdapter`（`:86`）与 `HttpAdapter`（`:108`）——**双连接模式**。`[事实]` 是**唯一支持合并转发**的两个适配器之一（`MiraiForwardMessage`，`forwardMessage.py:9`）。

### 4.3 OneBot 11/12（`adapters/onebot/`）

`[事实]` 结构对称：各自 `api.py`/`builder.py`/`package.py`。`[事实]` `onebot/v12/api.py:20,31` 显式 `raise UnsupportedMethod`（`apiProtocol.py:23`）——**唯一对不支持方法显式报错的适配器**。`[建议]` 其他适配器可对齐。

### 4.4 腾讯系（`adapters/tencent/`，约 1,500 行，最大）

`[事实]` 三层继承：

```
QQGuildAPI ──> QQGroupAPI (qqGroup/api.py:8) ──> ...
QQGuildBotInstance ──> QQGroupBotInstance (qqGroup/__init__.py:19)
                            └──> QQGlobalBotInstance (qqGlobal/__init__.py:8)
```

`[事实]` `qqGuild/api.py` 525 行，是**全仓库最大的单文件**。`[事实]` `IntentsClass` 枚举体系在 `intents.py:8-36`（`CommonIntents`/`PublicIntents`/`PrivateIntents`/`GroupIntents`）。`[事实]` `QQGroupChainBuilder` 用 `PortSingleton` 元类（`qqGroup/builder.py:41,76`）——`[推断]` 确保单例端口分配。`[事实]` `qqGlobal` 内嵌一个 `QQGuildBotInstance` 做双路由（`qqGlobal/__init__.py:20,29-32`）。

#### 4.4.1 QQ 官方 API v2 能力（已接入）

> `[事实]` 官方文档：<https://bot.q.qq.com/wiki/develop/api-v2/>（核对日期 2026-09）。

**全量群消息（非 @ 消息）**

`[事实]` 官方新增 `GROUP_MESSAGE_CREATE`（群消息·全量模式）：机器人在开放平台开启「接收所有消息」后，群内**每条**消息（不限 @）都会推送，事件体与 `GROUP_AT_MESSAGE_CREATE` **完全一致**。

| 项 | 结论 | 证据 |
|---|---|---|
| intent | 仍为 `GROUP_AND_C2C_EVENT (1<<25)`，**无新 intent 位** | `intents.py:36-38`；官方 intent 表未列该事件名 |
| 事件白名单 | `qqGroup/package.py` 的 `FULL_MESSAGE_CREATED` | 原先遗漏，事件落入 `Event` 分支 |
| 开关 | **无**——直接静默解析为 `Message` | `qqGroup/package.py`（按设计决定，见下） |

`[事实]` 全量消息一律解析为 `Message`，仅如实标记 `is_at`（是否 @ 了机器人），**框架不做任何过滤**——是否响应由使用者的前缀触发词/关键字逻辑决定，与 KOOK 等适配器一致。

`[事实]` **两条被否决的中间设计**（记录以免重复引入）：

1. **`receive_all_messages` 开关**（曾实现后移除）：用于在未开启时把全量事件降级为 `Event`。经需求方明确要求移除——框架不应替用户决定是否处理某类消息。
2. **`Message.is_full_message` 字段**（曾实现后移除）：原意是与 `is_at` 正交，以区分「全量通道的未 @ 消息」。经核对 `factory/implemented.py:62-82` 后被否决，理由有二：
   - **无实际效果**：`verify()` 中 `is_at=True` 跳过前缀检查，但 `else` 分支在 `prefix_keywords` 为空时（`implemented.py:76`）**同样放行**。默认机器人未调用 `set_prefix_keywords`，两条路径殊途同归，该字段不改变任何分发结果。
   - **语义错误**：开启全量后 `GROUP_AT_MESSAGE_CREATE` 与 `GROUP_MESSAGE_CREATE` **都会推送**，无法据此判断消息来源，字段是伪信息。

`[事实]` KOOK 适配器（`kook/package.py:30`）同样只设 `is_at`、**无**任何全量标记字段，是既有适配器的既有实践。

**新增 intent `GROUP_MEMBER_EVENT (1<<24)`**

`[事实]` `GROUP_JOIN_REQUEST`（用户申请加群）走 `1<<24`（`intents.py:GroupMemberIntents`）。`[事实]` 官方明示：**订阅无权限的 intent 会致 WebSocket 返回 `4014` 并断开连接**——故默认不订阅，由 `subscribe_group_member_event` 显式开启。

**其他已接入能力**

| 能力 | 实现位置 |
|---|---|
| 自定义 Markdown（`markdown.content`，无需模板） | `element.py:MarkdownContent`、`Chain.markdown_content()` |
| 引用回复 `message_reference` | `qqGroup/builder.py:PayloadBuilder`（`chain.reference=True`） |
| 群/单聊消息撤回 | `qqGroup/api.py:delete_group_message/delete_private_message` |
| 富媒体分片上传 | `qqGroup/api.py:upload_prepare/upload_part_finish` |
| 群管理（12 接口） | `qqGroup/api.py`（⚠️ 多需白名单，错误码 `11253`） |
| 互动事件回应 | `qqGroup/api.py:put_interaction_response` |
| 流式消息 | `qqGroup/api.py:post_stream_message`（仅单聊） |

**`[事实]` 已修复的既有缺陷**

1. `QQGroupMessageCallback.recall()` 原为 `...` 空实现 → 群消息撤回**完全不可用**；且 `recall_message` 继承自 `qqGuild`，会去调**频道** `/channels/...` 端点。现已覆盖为群/单聊端点。
2. `qqGroup` 的 `PayloadBuilder` 原不处理 `At`/`AtAll`（`qqGuild/builder.py:107-112` 有）→ `Chain.__init__` 自动 `at()` 被**静默丢弃**。现补上 `At`/`AtAll` 分支，与 `qqGuild` 行为一致（`<@openid>` / `<@everyone>`）。

**`[事实]` 未接入项（有意留待）**：自定义菜单 `GET/PUT /v2/menu`、指令面板 6 接口、入群自动审批策略 6 接口。`[事实]` 这些接口对普通 bot 需白名单/内邀，实际不可用。`[事实]` 域名统一 `api.bot.qq.com` 已为官方要求，但 `api.sgroup.qq.com` 实测仍可用（HTTP 401 而非 DNS 失败），故**未强制迁移**以避免回归。

### 4.5 `test` 适配器（`adapters/test/`）

`[事实]` **唯一被动服务端**模式：`TestInstance`（`__init__.py:27`）起 `TestServer`（`server.py:22`，继承 `amiyahttp.HttpServer`），在 `/{appid}` 开 WS 端点（`server.py:40-62`）。`[事实]` 客户端指向 `https://console.amiyabot.com/#/test`（`__init__.py:40`）。`[事实]` 图片 base64 落盘 `testTemp/images/`（`server.py:99-107`），退出时 `rmtree`（`:36-38`）。

`[事实]` **随包发布**：`setup.py:109` `find_packages` 无排除；实测 wheel 含 `amiyabot/adapters/test/*`。`[事实]` 全仓无引用，是**发布了但未导出**的适配器。

`[推断]` 风险：`server.py:109` 显式处理 `host == '0.0.0.0'`，说明该用法存在；此时 `/{appid}` **无鉴权**（`:40-44`），可注入伪造消息驱动机器人 + 无限制落盘。详见 [../risks.md](../risks.md) R-17。

### 4.6 废弃别名 —— **已移除**

`[事实]` 该文件原为 17 行：`:4`、`:7` 定义两个子类别名（`TencentBotInstance` / `TencentSandboxBotInstance`），`:10-17` 是**被注释掉的 `print()` 弃用提示**。

`[事实]` **本次已删除两个别名与注释块**，文件现仅剩 1 行 re-export：

```python
from .qqGuild import QQGuildBotInstance, QQGuildSandboxBotInstance
```

`[事实]` 保留 `:1` re-export 的用意：`from amiyabot.adapters.tencent import QQGuildBotInstance` 这类写法继续可用，避免扩大破坏面。

`[推断]` 原提示用 `print()` 而非 `warnings.warn`、且整体注释 → **弃用提示从未真正生效**，旧名用户是在**移除时才感知**的（表现为 `ImportError`）。`[事实]` 这也是「无正式弃用机制」的实例证据，详见 [../risks-api.md](../risks-api.md) R-9 与 [../public-api.md](../public-api.md) §4。

`[事实]` 删除的安全性已核实：仓库内部**零引用**这两个别名，全部代码直接引用 `amiyabot.adapters.tencent.qqGuild`（`amiyabot/__init__.py:17`、`qqGroup/__init__.py:6`、`qqGlobal/__init__.py:2,3`）；且默认适配器是 `QQGuildBotInstance`（`amiyabot/__init__.py:53`），非别名。

## 5. 重复与复用

`[事实]` **8 处独立实现** `build_message_send`：`kook/builder.py:50`、`mirai/builder.py:26`、`onebot/v11/builder.py:41`、`onebot/v12/builder.py:29`、`test/builder.py:8`、`comwechat/builder.py:17`、`qqGuild/builder.py:96`、`qqGroup/builder.py:252`。签名不一致（有的带 `api`，有的带 `chain_only`）。

`[事实]` **8 处独立实现** `package_*_message`：`kook/package.py:13`、`mirai/package.py:5`、`onebot/v11/package.py:5`、`onebot/v12/package.py:7`、`qqGuild/package.py:11`、`qqGroup/package.py:5`、`qqGlobal/package.py:6`、`comwechat/package.py:5`。

`[事实]` **7 处独立实现** `*MessageCallback`（每适配器一个）。

`[事实]` 真正的复用靠**继承**而非抽取：

| 复用 | 证据 |
|---|---|
| `comwechat/package.py:6` 直接调 `package_onebot12_message` | `[事实]` |
| `comwechat/__init__.py:18` 继承 `OneBot12Instance` | `[事实]` |
| `cqhttp/__init__.py:14` 继承 `OneBot11Instance` | `[事实]` |
| `cqhttp/api.py:8` `get_user_avatar = MiraiAPI.get_user_avatar` | `[事实]` 跨模块复用 |
| `test/builder.py` 是 `onebot/v11/builder.py` 的复制改造 | `[推断]` |

`[建议]` `cqhttp/api.py:8` 的跨模块复用**语义可疑**：CQHttp 实例并不经过 Mirai 服务，仅借用其「改小尺寸头像」兜底逻辑。

## 6. 依赖

`[事实]` `websockets`（`adapters/__init__.py:4`，含 `websockets.legacy.client`）、`aiohttp`/`requests`（经 `amiyabot.network.*`）、`amiyahttp`（`test/server.py`）、`amiyautils`（`create_dir`/`get_public_ip`/`random_code`）、`amiyalog`、`playwright`（间接，经 `messageChain`）。

`[事实]` 内部依赖：`amiyabot.builtin.message`、`amiyabot.builtin.messageChain`、`amiyabot.typeIndexes`（`:9-11`）。

`[事实]` 网络访问经 `amiyabot.network.*` shim：6 处导入 `httpRequests`（`kook/api.py:5`、`mirai/api.py:8`、`qqGuild/api.py:6`、`onebot/v11/api.py:3`、`onebot/v12/api.py:3` 等）+ `mirai/api.py:7` 导入 `download_async`。

## 7. 数据流

```
入站（以 QQ 频道为例）
  WS 收包  qqGuild/__init__.py:107,153
    └─> payload 解析  qqGuild/package.py:11  package_*_message
          └─> Message / Event
                └─> handler 回调  →  amiyabot/__init__.py:80  __message_handler

出站
  用户返回 Chain
    └─> Message.send        builtin/message/__init__.py:48
          └─> processing_context       factory/__init__.py:61
                └─> instance.send_chain_message(chain, is_sync=True)
                      └─> build_message_send(...)   各 adapters/*/builder.py
                            └─> 平台 REST 调用       各 adapters/*/api.py
                                  └─> MessageCallback 实例返回

主动发送
  bot.send_message(...)   adapters/__init__.py:46
    ├─> build_active_message_chain  各适配器实现（补 user_id/channel_id）
    └─> 同一 processing_context 路径
```

`[事实]` **两条出站路径都经过 `processing_context`**（`adapters/__init__.py:55`、`builtin/message/__init__.py:49`），因此 `message_before_send`/`after_send` 钩子对二者都生效。

## 8. 测试

`[事实]` **无自动化测试**。

`[事实]` 实际验证手段是手动联调：`test` 适配器 + `https://console.amiyabot.com/#/test`（`test/__init__.py:40`）。`[推断]` 这在 CI 中不可自动化。

`[建议]` 可测的纯逻辑：各 `builder.py` 的 `build_message_send`（输入 Chain → 输出 payload dict），无需真实网络。`[建议]` 这也是把 8 份重复实现抽出共享基类的契机。

## 9. 风险 / TODO

| 项 | 说明 | 证据 |
|---|---|---|
| **R-15** | `headers` property 内同步 `requests`（**已知设计约束**：缓存判定使其低频；契约要求 `headers` 同步，不可改异步） | `qqGroup/api.py:19-33` |
| **R-6** | 5 个适配器无限重连无退避；QQ 频道递归 `create_task` | `kook:46`、`mirai:55`、`onebot/v11:60`、`onebot/v12:60`、`comwechat:23`、`qqGuild:73-77` |
| **R-17** | `test` 适配器随包发布；`0.0.0.0` 下无鉴权 | `test/server.py:40-44,109` |
| **R-8** | `BotAdapterProtocol` 非真 ABC | `adapters/__init__.py:19` |
| **R-18** | URL 硬编码不可配置 | `kook/api.py:13`、`qqGuild/api.py:34` 等 |
| R-l | 8 份 `build_message_send` + 8 份 `package_*_message` 重复 | 见 §5 |
| R-m | `test/builder.py` 复制自 `onebot/v11/builder.py` | 改动易漏 |
| ~~R-n~~ | ~~弃用提示被注释，静默失效~~ → **已处理**：两个弃用类别名与注释块均已移除，文件仅剩 re-export | 见 §4.6 |
| R-o | 大量直接下标访问 JSON（`json[...]`），结构异常即 `KeyError` | `kook/__init__.py:43-44,82`、`qqGuild/__init__.py:114`、`qqGuild/api.py:289` |
| R-p | WS 主循环外层无 `except`（只有 `try/finally`），异常终止连接任务 | `kook/__init__.py:61-111` |
| R-q | `qqGuild/api.py:296-306` 重试无退避（`asyncio.sleep(0)`），3 次连续打 API | `qqGuild/api.py:296-306` |
| R-r | `qqGuild/api.py:299-305` 三次失败后**隐式返回 `None`**，调用方 `:209` 仍包成 Callback | `qqGuild/__init__.py:209` |
| R-s | `qqGroup/api.py:39-40` 异常被吞，随后返回空 token 的 Authorization 头 | `qqGroup/api.py:39-43` |
| `[不确定]` | KOOK 每次心跳 `create_task(self.wait_heartbeat())`（`:122`）是否累积任务，未经运行时验证 | `kook/__init__.py:113-131` |
| TODO | 无适配器级（per-adapter）单元测试 | — |

## 10. 相关文档

- 架构与调用链 → [../architecture.md](../architecture.md)
- 打包与发布 → [../packaging-release.md](../packaging-release.md)
- 风险总表 → [../risks.md](../risks.md)
