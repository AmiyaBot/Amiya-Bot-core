# 模块：工厂与插件 · 续篇（factory-and-plugins-impl）

> 本文件是 [factory-and-plugins.md](factory-and-plugins.md) 的续篇（§7 起）：依赖、数据流、测试建议、风险清单。
> 证据：`文件:行`。约定 `[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> 之所以单独成篇：为满足「单文件 ≤300 行」约束。

> ℹ️ 下文节号沿用母文档（§7 起），便于对照。

---

## 7. 依赖

`[事实]` `inspect`（栈帧推断，`factoryCore.py:1`）、`itertools.chain`（`:3`）、`amiyabot.builtin.*`、`amiyabot.adapters`（类型）、`amiyautils`（`temp_sys_path`/`extract_zip`/`import_module`/`delete_module`/`remove_prefix_once`）、`amiyalog`、`zipimport`/`shutil`/`copy`/`os`（插件装卸）。

## 8. 数据流

```
用户脚本 @bot.on_message(...)
  └─> BotHandlerFactory.on_message:73
        └─> 创建 MessageHandlerItemImpl:97
              ├─> message_handler_id_map[id(func)] = factory_name   :112
              └─> message_handlers.append(handler)                  :113
                    （存进本 factory 的 __container）

入站消息
  └─> message_handler                       handler/messageHandler.py:14
        ├─> bot.message_handlers             ← get_with_plugins() 聚合本 factory + 全部插件
        ├─> choice_handlers  逐个 verify(data.copy())
        │     └─> 按 weight 排序取第一
        ├─> handler.action(data) → 用户函数 → Chain
        └─> data.send(reply) → processing_context → instance

插件
  └─> BotInstance.load_plugin(path)
        └─> import module → getattr(module,'bot')   factory/__init__.py:261
              └─> install_plugin → plugins[plugin_id] = instance   :293
                    └─> 此后 get_with_plugins() 自动把插件的注册项并入
```

## 9. 测试

`[事实]` **无测试**。

`[建议]` 优先补测（纯逻辑，无 IO）：

| 目标 | 位置 |
|---|---|
| `update_data` 前缀剥离 | `implemented.py:34-42` |
| `__check` 类型分派（str/Equal/re.Pattern/list） | `implemented.py:12-32` |
| `verify` 私信准入组合（4 种） | `implemented.py:48-60` |
| `choice_handlers` 排序与 waiter 优先 | `messageHandler.py:133-156` |
| `get_with_plugins` list/dict 聚合 | `factoryCore.py:38-61` |
| `timed_task` sub_tag 序号生成 | `factory/__init__.py:191-200` |

## 10. 风险 / TODO

| 项 | 说明 | 证据 |
|---|---|---|
| ~~R-20~~ | ~~`verify` 内 `self.keywords = equal_filter` 原地改写 handler 状态~~ → **经复核为有意行为，已撤回**（写入供 `:113` 消费） | `implemented.py:89,113` |
| D-1 | `Verify.keypoint`（命中关键字）契约**无文档**且仓库内无消费方 | `structure.py:141`；`implemented.py:22` |
| R-19 | `choice_handlers` 每 handler 一次 `data.copy()`（深拷贝） | `messageHandler.py:140` |
| R-g | `get_with_plugins` 用**调用者函数名**推断属性名，隐式耦合 | `factoryCore.py:40` |
| R-h | `weight` 并列时先注册者胜，无 tie-break、无文档 | `messageHandler.py:148-149` |
| R-i | 7 个生命周期钩子标注 `# todo`，说明设计未完成 | `factory/__init__.py:63,69`；`messageHandler.py:29,45,60,77,97,104` |
| R-j | `load_plugin` 无沙箱/签名（设计使然，但需知悉） | `factory/__init__.py:230-268` |
| R-k | `PluginInstance.install/uninstall` 是空方法体 `...` | `factory/__init__.py:362-363` |
| TODO | 分发无索引（线性扫描），handler 多时是热点 | `messageHandler.py:139` |

## 11. 相关文档

- 架构与调用链 → [../architecture.md](../architecture.md)
- 等待事件 → [message-and-waiter.md](message-and-waiter.md)
- 风险总表 → [../risks.md](../risks.md)
