# 模块：消息与等待事件（builtin/message）

> 证据：`文件:行`。约定 `[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> 涉及文件：`builtin/message/__init__.py`(220 行)、`structure.py`(167)、`waitEvent.py`(168)。

## 1. 职责

`[事实]` 定义**入站数据模型**（`Message`/`Event`）与**等待事件机制**（`Waiter`），是 adapters 与 handler 之间的共享契约：

- adapters 把平台 payload 打包成 `Message`（如 `mirai/package.py`）
- handler 消费 `Message` 做分发（`handler/messageHandler.py:14`）
- 用户函数用 `Message.wait()` 挂起等待下一条消息

## 2. 入口与关键文件

| 文件 | 关键定义 | 行 |
|---|---|---|
| `__init__.py` | `Equal:28`、`Event:33`、`EventList:36`、`Message:47`、`MessageMatch:168`、`MessageCallback:193`、`Waiter:218`、`EventType:219` | — |
| `structure.py` | `EventStructure:15`、`MessageStructure:25`、`Verify:140`、`File:164` | — |
| `waitEvent.py` | `WaitEvent:9`、`ChannelWaitEvent:61`、`ChannelMessagesItem:90`、`WaitEventsBucket:99`、`wait_events_bucket:168` | — |

`[事实]` 全部 `waiter` 相关名字由 `__init__.py:12-21` 从 `waitEvent` 重导出，因此 `from amiyabot.builtin.message import WaitEvent` 可用。

## 3. 公共 API

### 3.1 `Message`（`__init__.py:47`）

| 方法 | 行 | 说明 |
|---|---|---|
| `send(reply)` | `48-55` | 包在 `bot.processing_context(reply, factory_name)` 内发送；**单条返回 callback，多条返回 list**（`:55`） |
| `recall()` | `57-59` | 需 `message_id` 非空才撤回 |
| `wait(max_time, force=False, level=0, data_filter=None)` | `61-96` | 用户级等待 |
| `wait_channel(target_id, max_time, force=False, level=0, data_filter=None)` | `98-149` | 频道级等待 |
| `copy()` | `151-165` | 深拷贝 |

`[事实]` `send()` 返回类型不对称（`Optional[MessageCallback]` 或 `list`，`:55`）——调用方需自行判断。`[建议]`

`[事实]` `copy()` 的实现有讲究（`:151-165`）：先把 `bot`/`instance` 置 `None`，`deepcopy`，再回填。`[推断]` 目的是避免深拷贝整棵 bot/instance 对象图（含 aiohttp session、logger 等不可拷贝对象）。副作用是副本与原对象**共享同一 `bot`/`instance` 引用**。

`[事实]` `copy()` 被 `handler/messageHandler.py:140` 在每个 handler 校验前调用一次。

### 3.2 `MessageStructure` 公开字段（`structure.py:25-71`）

`[事实]` 分类整理：

| 类别 | 字段 | 行 |
|---|---|---|
| 上下文 | `bot`、`instance`、`factory_name` | `27,28,30` |
| 原始数据 | `message`、`message_id`、`message_type` | `32,33,34` |
| 媒体 | `face`、`image`、`files`、`voice`、`audio`、`video` | `36,37,39,40,41,42` |
| 文本处理 | `text`、`text_prefix`、`text_digits`、`text_unsigned`、`text_original`、`text_words` | `44-49` |
| 提及 | `at_target`、`is_at`、`is_at_all` | `51,53,54` |
| 权限/私信 | `is_admin`、`is_direct` | `55,56` |
| 用户 | `user_id`、`user_openid`、`nickname`、`avatar` | `58,59,67,68` |
| 频道 | `channel_id`、`channel_openid`、`guild_id`、`src_guild_id` | `61,62,64,65` |
| 校验 | `verify` | `70` |
| 时间 | `time` | `71` |

`[事实]` 方法：`__str__:73`、`set_text:90`、`text_convert:97`（jieba 分词 + 中文数字归一，`structure.py:11-12,98-106`）。

`[事实]` `[建议]` **字段极多且全部可变**，`copy()` 深拷贝成本与之成正比（见 [risks.md](../risks.md) R-19）。

### 3.3 `Verify`（`structure.py:140-161`）

`[事实]` 三要素：`result`（是否命中）、`weight`（优先级）、`keypoint`；`__bool__` 取 `result`；`set_attrs(*args)` 按上述顺序赋值。

`[事实]` `on_selected` 回调字段（`handler/messageHandler.py:153-154` 调用）——**前缀剥离的挂钩点**：`factory/implemented.py:82` 把 `update_data` 挂上，命中后剥离前缀（`implemented.py:34-42`）。

### 3.4 关键字匹配（`__init__.py:168-190`）

| 方法 | 行 | 语义 |
|---|---|---|
| `MessageMatch.check_str` | `168` | 子串包含 |
| `MessageMatch.check_equal` | `173` | 全等（配 `Equal`，`__init__.py:28`） |
| `MessageMatch.check_reg` | `182` | 正则 |

`[事实]` 分派在 `factory/implemented.py:13-17` 用 `type(obj)` 查表。

`[建议]` 三个方法**纯函数、零依赖**，是最适合优先补单测的目标（见 [testing-quality.md](../testing-quality.md) §7）。

### 3.5 `MessageCallback`（`__init__.py:193-215`）

`[事实]` 抽象接口，各适配器实现（`kook/builder.py:9`、`mirai/builder.py:14`、`onebot/v11/builder.py:14` 等共 7 个）。

## 4. 等待事件机制（核心）

### 4.1 `WaitEvent`（`waitEvent.py:9-58`）

`[事实]` 字段：`event_id`、`target_id`、`force`、`level`（`:11-14`）、`curr_time`（`:16`）、`data`（`:18`）、`type='user'`（`:19`）、`alive=True`（`:21`）。

`[事实]` `timer(max_time)`（`:26-30`）：每 0.2 秒累加，超时置 `alive=False`。**独立协程**，由 `Message.wait` 起 `asyncio.create_task`（`__init__.py:78`）。

`[事实]` `check_alive()`（`:36-46`）三重校验：

```python
if self.target_id not in wait_events_bucket:
    raise WaitEventCancel(self, 'This event already deleted.')       # :37-38
if self.event_id != wait_events_bucket[self.target_id].event_id:
    raise WaitEventCancel(self, 'Event id not equal.', del_event=False)  # :40-41
# if not self.alive:
#     WaitEventCancel(self, 'Timeout.')                              # :43-44  已注释
return self.alive                                                    # :46
```

`[事实]` **超时分支被注释掉**（`:43-44`）。`[推断]` 这是有意设计：超时应表现为 `return False`（正常「没等到」），而「被顶替」才是异常。`[建议]` 但注释掉的代码是维护负担，应删除或恢复。

`[事实]` `cancel(del_event=True)`（`:54-58`）：置 `alive=False` 并从桶删除。

### 4.2 `ChannelWaitEvent`（`waitEvent.py:61-87`）

`[事实]` 差异点：`data` 初始化为列表（`:65`）、`type='channel'`（`:66`）、有 `token`（`:67`）；`set` 改为 `append`（`:72-74`）、`get` 改为 `pop(0)`（`:76-78`）——**FIFO 队列语义**。

`[事实]` `focus(token):80` / `on_focus(token):83` / `clean():86` 支持「只接收特定焦点消息」，失配抛 `WaitEventOutOfFocus`。

`[事实]` 包装器 `ChannelMessagesItem(event, item)` 带 `close_event()`（`:90-96`）。

### 4.3 `WaitEventsBucket`（`waitEvent.py:99-135`）

`[事实]` 单例 `wait_events_bucket`（`:168`）。`bucket` 是普通 dict（`:103`），`id` 自增受 `asyncio.Lock` 保护（`:120-123`）。

`[事实]` 三个魔术方法**均为容错实现**：`__getitem__` 缺键返回 `None` 而非抛 `KeyError`（`:110-114`），`__delitem__` 吞 `KeyError`（`:116-120`）。`[推断]` 这让删除操作天然幂等，配合 `cancel` 的多次调用是必要的。

### 4.4 key 规则与消费（跨文件，关键）

`[事实]` 三处**必须严格一致**的字符串拼接：

| 场景 | 格式 | 生产 | 消费 |
|---|---|---|---|
| 私信 | `{appid}_{guild_id}_{user_id}` | `message/__init__.py:70` | `messageHandler.py:164` |
| 频道用户 | `{appid}_{channel_id}_{user_id}` | `__init__.py:72` | `messageHandler.py:169` |
| 频道全体 | `{appid}_{channel_id}` | `__init__.py:110` | `messageHandler.py:174` |

`[建议]` 这些 key 是**跨模块隐式协议**，靠人工保持一致——两处任一处改动都会静默失配（等待事件永不触发）。建议抽成共用函数。

`[事实]` `find_wait_event` 优先级（`messageHandler.py:167-180`）：用户级优先，**频道级 `force=True` 时覆盖用户级**（`:179-180`）；`check_alive()` 抛 `WaitEventCancel` 时置 `None`（`:186-187`）。

### 4.5 `level` 与 `force` 的区别（易混淆）

`[事实]`

| 参数 | 作用 | 证据 |
|---|---|---|
| `level` | **权重**，参与 `choice_handlers` 排序，越高越优先于普通 handler | `messageHandler.py:137,148-149` |
| `force` | **覆盖**，仅用于「频道级 waiter 压制用户级 waiter」 | `messageHandler.py:59,179-180` |

`[建议]` 两者语义正交但都叫「优先级」，文档缺失时极易用错。

## 5. 依赖

`[事实]` `asyncio`（timer、lock）、`copy`（`copy()`）、`re`（正则匹配）、`amiyautils.httpRequestsUtils.Response`（`__init__.py:9`）、`amiyalog`（`waitEvent.py:4`）、jieba（经 `structure.py:11`）。

`[事实]` 无第三方重依赖，本模块相对内聚。

## 6. 数据流

```
适配器收包
  └─> package_*_message()           各 adapters/*/package.py
        └─> Message 实例            message/__init__.py:47
              ├─> handler 分发      messageHandler.py:14
              │     └─ copy() 后交给各 handler 校验   :140
              └─> 用户调用 wait()   __init__.py:61
                    ├─> wait_events_bucket.set_event(...)  waitEvent.py:125
                    ├─> create_task(timer)                  __init__.py:78
                    └─> 忙等 check_alive()                  :80-92
                          下一条消息到达时
                          └─> find_wait_event 命中          messageHandler.py:159
                                └─> waiter.set(data)          :64 或 :108
                                      └─> wait() 取出并返回    __init__.py:90
```

`[事实]` 忙等实现（`__init__.py:80-92`）用 `await asyncio.sleep(0)` 轮询 `check_alive()`。`[推断]` 是活跃轮询，短等待可接受，长等待（分钟级）会持续占用调度。`[不确定]` 未测实际 CPU 开销。

## 7. 测试

`[事实]` **无任何测试**（全项目零测试，见 [testing-quality.md](../testing-quality.md)）。

`[建议]` 本模块最适合优先补测的部分（纯逻辑、无 IO）：

| 目标 | 位置 |
|---|---|
| `MessageMatch.check_str/equal/reg` | `__init__.py:168-190` |
| `Verify.__bool__` / `set_attrs` | `structure.py:140-161` |
| `WaitEvent.check_alive` 三分支 | `waitEvent.py:36-46` |
| `WaitEventsBucket.set_event` id 自增 | `waitEvent.py:125-135` |
| `text_convert` 中文数字归一 | `structure.py:97` |

## 8. 风险 / TODO

| 项 | 说明 | 证据 |
|---|---|---|
| R-a | `check_alive` 中被注释的超时分支 | `waitEvent.py:43-44` |
| R-b | key 拼接跨模块重复 3 处，无共用函数 | `__init__.py:70,72,110` ↔ `messageHandler.py:164,169,174` |
| R-c | `send()` 返回类型不对称（单值/list） | `__init__.py:55` |
| R-d | `copy()` 深拷贝在每 handler 调用一次，开销 O(N) | `messageHandler.py:140` |
| R-e | `level` 与 `force` 语义易混淆且无文档 | `messageHandler.py:59,137` |
| R-f | `wait()` 用 `sleep(0)` 忙等轮询 | `__init__.py:80-92` |
| TODO | 本模块无 docstring（对比 `factory/__init__.py` 有中文 docstring） | `waitEvent.py` 全文无 docstring |

## 9. 相关文档

- 分发算法 → [../architecture.md](../architecture.md) §5、§6
- 风险总表 → [../risks.md](../risks.md)
