# 风险与雷区 · 低severity 分册（risks-low）

> 本文件是 [risks.md](risks.md) 的续篇，收录 🟢 低 / 低中severity风险与附录。
> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。所有结论附 `文件:行`。
> **本文档只描述风险，不做任何代码/配置改动。**
>
> 高severity风险（🔴/🟠/🟡）见 → [risks.md](risks.md)。

## 🟢 R-8 · `BotAdapterProtocol` 非真 ABC

**证据** `[事实]` `amiyabot/adapters/__init__.py:19`：

```python
class BotAdapterProtocol:        # :19  未继承 abc.ABC
    @abc.abstractmethod          # :72
    async def close(self): ...
```

`[事实]` 5 个 `@abc.abstractmethod` 分别在 `:72`、`:79`、`:88`、`:99`、`:114`。

**影响** `[推断]`
- 因未继承 `abc.ABC`（或 `metaclass=ABCMeta`），`@abstractmethod` **不被强制**：漏实现的方法在**实例化时不报错**，直到运行时调用才 `NotImplementedError`。
- 自定义适配器容易漏实现 `recall_message` 等，故障延迟暴露。

**建议** 改为 `class BotAdapterProtocol(abc.ABC)`。

**本次不改动。**

---

## 🟢 R-13 · 依赖声明漂移

**证据** `[事实]`

| 依赖 | 本仓库 | 线上 2.1.0 |
|---|---|---|
| `amiyautils` | `requirements.txt:3` → `~=0.0.4` | wheel METADATA `Requires-Dist: amiyautils~=0.0.5` |

**影响** `[推断]` `~=0.0.4` 语义为 `>=0.0.4, ==0.0.*`，**实际包含 0.0.5**，因此运行时影响有限；但**声明与发布产物不一致**本身是配置漂移证据，说明 master 落后于已发布状态。

**建议** 统一 `requirements.txt` 与发布版本；引入 lock 或最低版本对齐检查。

**本次不改动。**

---

## 🟢 R-11 · `setup.py` 构建时写回 `requirements.txt`

**证据** `[事实]` `setup.py:88-92`：

```python
with open('requirements.txt', mode='r', encoding='utf-8') as req:
    requirements = sorted(req.read().lower().strip('\n').split('\n'))

with open('requirements.txt', mode='w', encoding='utf-8') as req:   # 写回！
    req.write('\n'.join(requirements))
```

**影响** `[推断]`
- 任何构建/导入 `setup.py` 都会**修改工作区文件**（把依赖排序并小写）。
- 会污染 `git status`，并可能在 CI 中造成「意料之外的 diff」。
- `[事实]` 当前 `requirements.txt` 已是排序状态（第 1-13 行），说明该副作用**已经发生过**。

**建议** 移除写回（构建脚本不应有副作用）。

---

## 🟢 R-18 · 硬编码 URL，无代理/自建域名支持

**证据** `[事实]`

| 目标 | URL | 位置 |
|---|---|---|
| KOOK API | `https://www.kookapp.cn/api/v3` | `kook/api.py:13` |
| QQ 频道 API | `https://api.sgroup.qq.com` | `qqGuild/api.py:34` |
| QQ 频道沙箱 | `https://sandbox.api.sgroup.qq.com` | `qqGuild/api.py:34` |
| QQ 群 token | `https://bots.qq.com/app/getAppAccessToken` | `qqGroup/api.py:22` |
| 头像 CDN | `https://q1.qlogo.cn/...` | `mirai/api.py:43,46` |
| 头像 CDN | `https://q.qlogo.cn/headimg_dl?...` | `mirai/package.py:26` |
| PyPI（构建期） | `https://pypi.python.org/pypi/amiyabot/json` | `setup.py:18` |

**影响** `[推断]` 无法通过配置切换自建/代理域名；企业内网、镜像环境受限。仅 QQ 频道有 `sandbox` 布尔切换（`qqGuild/api.py:34`）。

**建议** 抽出可配置的 endpoint/base-url。

---

## 🟢 R-19 · `choice_handlers` 深拷贝 × N + 无并列保护

**证据** `[事实]` `amiyabot/handler/messageHandler.py:139-149`：

```python
for item in handlers:
    check = await item.verify(data.copy())        # :140  ← 每个 handler 一次深拷贝
    if check:
        candidate.append((check, item))
...
_sorted = sorted(candidate, key=lambda n: n[0].weight, reverse=True)   # :148
selected = _sorted[0]                                                   # :149
```

`[事实]` `Message.copy()` 是 `copy.deepcopy`（`builtin/message/__init__.py:151-165`）。

**影响** `[推断]`
- 每条入站消息要对**每个**已注册 handler 做一次 `deepcopy(Message)` → O(handler 数) 次深拷贝，插件多时是主要开销。
- `weight` 并列时**先注册者胜**（`sorted` 稳定排序 + 取 `[0]`），行为隐式、无文档说明，插件优先级冲突难以排查。
- `[不确定]` 未做基准测试，实际开销取决于 `Message` 对象图大小。

**建议** 考虑浅拷贝 + 显式保护字段；对并列 `weight` 增加确定性 tie-break 并文档化。

---

## 🟢 R-21 · 模块级副作用：`signal.signal` 在 import 时执行

**证据** `[事实]` `amiyabot/signalHandler.py:25`：

```python
signal.signal(signal.SIGINT, sigint_handler)     # :25  模块顶层，import 即注册
```

`[事实]` 该模块由 `amiyabot/__init__.py:25` 导入。

**影响** `[推断]`
- **import `amiyabot` 就改写进程的 SIGINT 处理**，覆盖宿主的既有 handler。
- 若宿主脚本想自定义 Ctrl+C 行为，会被静默覆盖。
- 在非主线程 import 时 `signal.signal` 会抛 `ValueError: signal only works in main thread`。
- `[事实]` `sigint_handler` 内部 `sys.exit(0)` 被注释掉（`:22`），因此按 Ctrl+C **不会退出进程**——只执行关停钩子。`[推断]` 若不显式退出，宿主可能需再按一次或手动终止。

**建议** 把信号注册改为显式函数调用（由 `AmiyaBot.start()` 触发），而非 import 副作用。

**本次不改动。**

---

## 🟢 R-22 · `signalHandler` 无 SIGTERM 处理

**证据** `[事实]` `amiyabot/signalHandler.py:25` 只注册 `SIGINT`；全文件无 `SIGTERM`：

```
$ grep -n "SIGTERM\|SIGINT" amiyabot/signalHandler.py
22:    # sys.exit(0)
25: signal.signal(signal.SIGINT, sigint_handler)
```

`[推断]` 影响：
- 容器/进程管理器默认用 `SIGTERM` 终止，此时 `SignalHandler.exec_shutdown_handlers()` **不会执行**。
- 表现为：数据库连接、浏览器进程、WebSocket 未优雅关闭；定时任务（`TasksControl` 已注册 `scheduler.shutdown`，`timedTask/__init__.py:24`）不被触发。

**建议** 同时注册 `SIGTERM`。

**本次不改动。**

---

## 附：本次探索**确认不成立**的担忧（如实修正）

`[事实]` 为避免误导，列出经实测**被否定**的假设：

| 假设 | 实测结果 |
|---|---|
| 「GitHub Actions 里可能硬编码了 PyPI token / secrets 泄漏」 | **不成立**。`pypi.yml` 全文件无 `secrets.`，用 OIDC Trusted Publishing（`:13-14`） |
| 「`_assets` 资源在发布的 wheel 中整体缺失」 | **不成立**。实测 10 个资源均在 `amiyabot/_assets/**`（`namelist()` 校验）；`[事实]` 另有一份无用副本在 `.data/data/` |
| 「`MANIFEST.in` 失效导致 `template.html` 等非 ttf 资源丢失」 | **不成立**（wheel 场景）。被 `include_package_data` + git 追踪兜住；`[不确定]` sdist 场景未验证 |
| 「`setup.py` 版本号 `0.1.0` 就是实际发布版本」 | **不成立**。wheel METADATA 实测为 `Version: 2.1.0`，证明被 `setup.py:65` 覆盖 |

## 相关文档

- 高风险总表 → [risks.md](risks.md)
- 打包与版本细节 → [packaging-release.md](packaging-release.md)
- 依赖风险 → [dependencies.md](dependencies.md)
