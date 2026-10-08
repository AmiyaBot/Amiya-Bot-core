# 模块：工厂与插件（factory + handler）

> 证据：`文件:行`。约定 `[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> 涉及文件：`factory/__init__.py`(364 行)、`factoryCore.py`(117)、`factoryTyping.py`(84)、`implemented.py`(116)、`handler/messageHandler.py`(189)。

## 1. 职责

`[事实]` 这五个文件共同构成框架的**注册表 + 分发 + 插件**中枢：

| 文件 | 单一职责 | 证据 |
|---|---|---|
| `factoryCore.py` | **纯容器**：持有 7 个生命周期钩子 + 注册表，含插件聚合逻辑 | `FactoryCore:7` |
| `factoryTyping.py` | 类型契约与数据类 | `GroupConfig:35`、`MessageHandlerItem:46` |
| `implemented.py` | 关键字/前缀/私信校验的**具体算法** | `MessageHandlerItemImpl:11` |
| `factory/__init__.py` | 面向用户的装饰器 + 插件装卸 | `BotHandlerFactory:17` |
| `handler/messageHandler.py` | **唯一分发中心** | `message_handler:14` |

`[事实]` 分层清晰：`factoryCore` 不知道分发，`messageHandler` 不知道插件装载。`[推断]` 这是本仓库设计得最好的部分。

## 2. 入口与关键文件

`[事实]` 容器初始化（`factoryCore.py:9-30`）——**14 个键**，是理解全局注册表的最佳单一位置：

```python
self.__container = {
    'prefix_keywords': list(),              # :11  触发词
    'event_handlers': dict(),               # :13  事件响应器
    'message_handlers': list(),             # :14  消息响应器
    'exception_handlers': dict(),           # :15  异常处理器
    'message_handler_id_map': dict(),       # :17  handler→factory 反查
    'process_event_created': list(),        # :19  ┐
    'process_message_created': list(),      # :20  │
    'process_message_before_waiter_set': list(),  # :21  │ 7 个生命周期
    'process_message_before_handle': list(),      # :22  │
    'process_message_before_send': list(),        # :23  │
    'process_message_after_send': list(),         # :24  │
    'process_message_after_handle': list(),       # :25  ┘
    'group_config': dict(),                 # :27  组设置
    'timed_tasks': list(),                  # :29  定时任务
}
```

`[事实]` `factory_name` 默认 `'default_factory'`（`:33`）。

## 3. 公共 API

### 3.1 注册装饰器（`factory/__init__.py`）

`[事实]` 定义在 `BotHandlerFactory`，被 `BotInstance`/`PluginInstance`/`AmiyaBot` 继承：

| 装饰器 | 行 | 参数 | 落地容器 |
|---|---|---|---|
| `on_message` | `73-117` | `group_id, keywords, verify, check_prefix, allow_direct, direct_only, level` | `message_handlers`（`:113`）+ `message_handler_id_map`（`:112`） |
| `on_event` | `119-143` | `events`（默认 `'__all_event__'`） | `event_handlers`（`:133-139`） |
| `on_exception` | `145-169` | `exceptions`（默认 `Exception`） | `exception_handlers`（`:159-165`） |
| `timed_task` | `171-205` | `each, sub_tag, run_when_added, **kwargs` | `timed_tasks`（`:189-201`） |

`[事实]` 非装饰器：`set_group_config`（`:214-215`）、`set_prefix_keywords`（`:217-219`）、`remove_timed_task`（`:207-208`）、`run_timed_tasks`（`:210-212`）。

`[事实]` **关键设计**：`on_message` 注册时会记录 `message_handler_id_map[id(func)] = self.factory_name`（`:112`）。`[推断]` 因为 handler 会被聚合成扁平列表（见 §4），分发时需反查「这个函数属于哪个 factory」才能取对应配置。这是用 `id(func)` 而非函数引用做键的原因。

`[事实]` `timed_task` 的 `sub_tag` 自动追加 `key{len}` 序号（`:196`），避免同 tag 冲突。

### 3.2 生命周期钩子注册器（`factoryCore.py:91-117`）

`[事实]` 7 个方法，形如：

```python
def message_before_send(self, handler: BeforeSendHandlerType):
    self.get_container('process_message_before_send').append(handler)   # :108
    return handler                                                       # :109
```

`[事实]` 全部返回 `handler`，因此**可作装饰器直接使用**。

### 3.3 类型契约（`factoryTyping.py`）

`[事实]` 这是全项目类型信息最集中的地方：

| 类型 | 行 | 说明 |
|---|---|---|
| `KeywordsType` | `10` | `str \| Equal \| re.Pattern \| list[...]` |
| `CheckPrefixType` | `11` | `bool \| list[str]` |
| `FunctionType` | `21` | `Callable[[Message], ChainReturn]` |
| `VerifyMethodType` | `22` | 返回值 `bool \| (bool,int) \| (bool,int,Any)` |
| `EventHandlerType` | `23` | `Callable[[EventType, BotAdapterProtocol], NoneReturn]` |
| `ExceptionHandlerType` | `24` | `Callable[[Exception, BotAdapterProtocol, ...], NoneReturn]` |
| 7 个钩子类型 | `26-32` | 各自精确签名 |
| `GroupConfig` | `35-43` | `dataclass`，含 `__str__` 返回 group_id |
| `MessageHandlerItem` | `46-84` | `dataclass` + 2 个 abstractmethod |

`[事实]` 类型别名区（`:72-84`）定义 13 个容器类型别名。

`[建议]` 这些标注质量不低但**无检查器验证**（无 mypy/pyright，见 [testing-quality.md](../testing-quality.md)）。

## 4. 插件系统与聚合机制

### 4.1 `get_with_plugins()`（`factoryCore.py:38-61`）——最精巧的一段

`[事实]` 用**调用栈帧**推断要聚合哪个属性：

```python
def get_with_plugins(self, attr_name: Optional[str] = None):
    if not attr_name:
        attr_name = inspect.getframeinfo(inspect.currentframe().f_back)[2]   # :40  用调用者函数名！
    self_attr = self.get_container(attr_name)
    attr_type = type(self_attr)
    if attr_type is list:
        return self_attr + list(chain(*(getattr(plugin, attr_name)
                                       for _, plugin in self.plugins.items())))   # :46
    if attr_type is dict:
        value = {**self_attr}                                                  # :49
        for _, plugin in self.plugins.items():
            plugin_value = getattr(plugin, attr_name)
            for k in plugin_value:
                if k not in value:
                    value[k] = plugin_value[k]                                 # :53
                else:
                    value[k] += plugin_value[k]                                # :55
                if isinstance(value[k], list):
                    value[k] = list(set(value[k]))                             # :58-59  去重
        return value
```

`[事实]` 这就是为什么所有属性都写成同名同义的 property：

```python
@property
def message_handlers(self) -> MessageHandlers:
    return self.get_with_plugins()      # factory/__init__.py:46-47
```

`[推断]` `:40` 通过 `f_back` 取**调用方的函数名**作为 `attr_name`，因此 property 名必须与容器键名**完全一致**，否则 `get_container` 抛 `KeyError`。`[建议]` 这是隐式耦合，改 property 名会以 `KeyError` 形式失败，且报错信息不含 attr_name。

`[事实]` dict 类型聚合用 `+=` 合并同键 list（`:55`），并对 list 值 `list(set(...))` 去重（`:58-59`）——`[建议]` 依赖元素可哈希，若注册的函数对象不可哈希会抛错（函数对象可哈希，故当前安全）。

### 4.2 `BotInstance`（`factory/__init__.py:225`）

| 方法 | 行 | 说明 |
|---|---|---|
| `start` | `226-228` | **抽象**，子类实现 |
| `load_plugin` | `230-268` | 三种加载形态 |
| `install_plugin` | `270-295` | 断言 plugin_id 唯一（`:286`） |
| `uninstall_plugin` | `297-319` | 清理定时任务 + 模块 + 可选删文件 |
| `reload_plugin` | `321-331` | 深拷贝 path → 卸载 → 重装 |
| `combine_factory` | `333-334` | 把主工厂挂为 `plugins['__factory__']` |

`[事实]` 插件加载形态（`:237-259`）：

| 输入 | 分支 | 机制 |
|---|---|---|
| 目录 | `:240-243` | `temp_sys_path` + `import_module(basename)` |
| `.py` 文件 | `:244-247` | `temp_sys_path` + `import_module(strip('.py'))` |
| 其他（zip） | `:248-259` | `zipimport.zipimporter` 或 `extract_zip` 后 import |

`[事实]` 统一取实例：`instance: PluginInstance = getattr(module, 'bot')`（`:261`）——**约定模块必须暴露名为 `bot` 的对象**。

`[事实]` `uninstall_plugin` 断言 `plugin_id != '__factory__'`（`:298`），保护上面那层特殊键。

### 4.3 `PluginInstance`（`factory/__init__.py:337-364`）

`[事实]` 构造参数：`name, version, plugin_id, plugin_type=None, description=None, document=None, priority=1`（`:338-347`）。

`[事实]` 它继承 `BotHandlerFactory`，因此**拥有与主 bot 完全相同的注册能力**（`on_message` 等）。`[事实]` `factory_name = plugin_id`（`:360`），使 `message_handler_id_map` 能反查到插件。

`[事实]` `install()`/`uninstall()` 是**空方法**（`:362-363`），供子类覆写。

## 5. 分发主流程（`handler/messageHandler.py`）

`[事实]` `message_handler(bot, data)`（`:14`）——按顺序执行 6 个阶段：

| 阶段 | 行 | 行为 |
|---|---|---|
| ① 日志路由 | `18-25` | 按 `appid` 缓存独立 `LoggerManager` |
| ② 事件分流 | `28-34` | 非 `Message` → `event_handler`，**直接 return** |
| ③ `message_created` | `46-53` | 可改写；返回 `False` 丢弃；返回非 None 替换 |
| ④ 查找 waiter | `56` | `find_wait_event(data)` |
| ⑤ 强制 waiter | `59-65` | `waiter.force` → 直接 `set(data)` 后 return |
| ⑥ 选择 handler | `68` | `choice_handlers(...)` → 分 MessageHandlerItem / WaitEvent |

`[事实]` 命中 `MessageHandlerItem` 后（`:72-101`）：反查 `factory_name`（`:73`）→ `message_before_handle` 生命周期（`:79-83`，返回 `False` 可拦截）→ `handler.action(data)`（`:87`）→ str 自动包成 `Chain`（`:92-93`）→ `data.send(reply)`（`:95`）→ `message_after_handle`（`:98-99`）。

`[事实]` 命中 `WaitEvent` 后（`:103-108`）：`message_before_waiter_set` → `handler.set(data)`。

### 5.1 `choice_handlers`（`:133-156`）——调度核心

`[事实]` 算法：

```python
candidate = []
if waiter:
    candidate.append((Verify(True, waiter.level), waiter))     # :137  waiter 进候选
for item in handlers:
    check = await item.verify(data.copy())                     # :140  每个 handler 校验副本
    if check:
        candidate.append((check, item))
_sorted = sorted(candidate, key=lambda n: n[0].weight, reverse=True)  # :148
selected = _sorted[0]                                                  # :149
data.verify = selected[0]                                              # :152
if data.verify.on_selected:
    data.verify.on_selected()                                          # :154
```

`[事实]` `event_handler`（`:111-130`）：先取 `'__all_event__'` 的 handler（`:113-114`），再把单个 `Event` 包成 `EventList`（`:116-117`），按事件名追加专属 handler（`:122-123`），用 `_log.catch` 包裹每个调用（`:129-130`）。

## 6. 校验算法（`factory/implemented.py`）

`[事实]` `MessageHandlerItemImpl`（`:11`）继承 `MessageHandlerItem` 并实现两个抽象方法。

`[事实]` `verify` 的执行顺序（`:44-113`）：

| 步骤 | 行 | 判定 |
|---|---|---|
| 1. 私信准入 | `48-60` | `direct_only` 与 `allow_direct` 组合判断 |
| 2. 前缀 / @ | `63-91` | `is_at` 直接通过（`:71`）；否则查前缀（`:74-82`）；`Equal` 特例放行（`:86-91`） |
| 3. 自定义校验 | `94-111` | `custom_verify`，支持 `bool` 或 `(bool,int[,Any])` 元组 |
| 4. 关键字匹配 | `113` | `__check` |

`[事实]` `__check`（`:12-32`）用 `type(obj)` 查分派表：

```python
methods = {
    str: MessageMatch.check_str,
    Equal: MessageMatch.check_equal,
    re.Pattern: MessageMatch.check_reg,
}                                       # :13-17
```

`[事实]` list 类型递归（`:26-30`）。

`[事实]` `update_data`（`:34-42`）返回闭包，挂到 `result.on_selected`（`:82`），命中后剥离前缀并写入 `data.text_prefix`（`:38-39`）。

`[事实]` **关键字收窄分支（`:86-91`）—— 有意行为，非缺陷**：

```python
if need_check_prefix and not flag and not isinstance(self.keywords, Equal):
    equal_filter = [n for n in self.keywords if isinstance(n, Equal)] if isinstance(self.keywords, list) else []
    if equal_filter:
        self.keywords = equal_filter          # :89  ← 收窄为 Equal 子集，供 :113 消费
    else:
        return result
...
return self.__check(result, data, self.keywords)   # :113  依赖 :89 写入的结果
```

`[事实]` 说明：`:84-85` 的注释表明意图是「前缀未通过时，转而校验列表中的 `Equal` 项」。`:89` 的写入**被 `:113` 依赖**——不写回则 `__check` 会拿到未收窄的完整列表，该分支失去意义。

`[事实]` `grep -n "self.keywords"` 仅命中 `:86,87,89,113`，除注册时赋值（`factory/__init__.py:110`）外无其他读写方，因此不存在对外的可观察状态污染。

`[事实]` **修正记录**：本节原先判定此处为「跨消息状态泄漏缺陷」，系本次审计的**误判**，经代码复核后撤回（详见 [../risks.md](../risks.md) R-20）。

### 6.1 命中关键字回传契约（值得补文档）

`[事实]` `verify()` 链路刻意保留「哪个关键字命中」的信息：

| 环节 | 行为 | 证据 |
|---|---|---|
| `check_str` / `check_equal` | 返回 `(True, weight, 命中的关键字)` | `builtin/message/__init__.py:172,177` |
| `check_reg` | 返回 `(True, weight, 正则分组列表)` | `:183-187` |
| `__check` | `result.set_attrs(*method(...))` | `implemented.py:22` |
| `set_attrs` | 按 `result`/`weight`/`keypoint` 顺序赋值 | `structure.py:154-162` |
| `Verify.keypoint` | 承接命中关键字；经 `data.verify` 暴露给用户函数 | `structure.py:141`；`handler/messageHandler.py:152` |

`[建议]` 即注册函数可用 `data.verify.keypoint` 取到命中的关键字。`[不确定]` 该语义在仓库中无文档记载（`on_message` docstring 仅称「触发关键字」，`factory/__init__.py:88`；`keypoint` 无仓库内消费方）——**建议补充说明**。

## 7. 依赖 / 数据流 / 测试 / 风险 → 见续篇

`[事实]` 为满足「单文件 ≤300 行」约束，以下内容拆到 [factory-and-plugins-impl.md](factory-and-plugins-impl.md)：

| 节 | 内容 |
|---|---|
| §7 | 依赖清单 |
| §8 | 完整数据流（注册 → 分发 → 插件聚合） |
| §9 | 建议优先补测的目标与位置 |
| §10 | 本模块风险 / TODO 全表（含 R-19 深拷贝、`get_with_plugins` 隐式耦合等） |

### 本模块最该记住的 3 点

1. `[事实]` **`get_with_plugins()` 靠调用栈帧推断属性名**（`factoryCore.py:40`）——新增「属性 ↔ 容器键」必须**同名**，否则 `KeyError`。
2. `[事实]` **命中关键字回传契约未文档化**：`verify()` 会把命中的关键字写入 `Verify.keypoint`（`implemented.py:22` → `structure.py:158`），经 `data.verify` 暴露给用户函数，但仓库内无任何说明且无消费方。
3. `[事实]` **7 个生命周期钩子标注 `# todo`**，属已知未完成设计（`factory/__init__.py:63,69`；`handler/messageHandler.py:29,45,60,77,97,104`）。

---

## 相关文档

- 架构与调用链 → [../architecture.md](../architecture.md)
- 等待事件 → [message-and-waiter.md](message-and-waiter.md)
- 本模块续篇（依赖/数据流/风险） → [factory-and-plugins-impl.md](factory-and-plugins-impl.md)
- 风险总表 → [../risks.md](../risks.md)
