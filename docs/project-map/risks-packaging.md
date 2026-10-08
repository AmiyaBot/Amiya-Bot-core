# 风险与雷区 · 打包与依赖分册（risks-packaging）

> 本文件是 [risks.md](risks.md) 的续篇，收录 🟡 中severity的 **打包与依赖**类风险。
> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。所有结论附 `文件:行`。
> **本文档只描述风险，不做任何代码/配置改动。**

> ℹ️ 下文节号沿用母文档（R-4 起），便于对照。

---

## 🟡 R-4 · `data_files` 重复落盘 + 展平；`MANIFEST.in` 失效

**证据** `[事实]`（**已实测正式 wheel 验证，见 [packaging-release.md](packaging-release.md) §8**）

```
amiyabot/_assets/font/HarmonyOS_Sans_SC.ttf,sha256=uEhdcux...,8261128
amiyabot-2.1.0-535.data/data/amiyabot/HarmonyOS_Sans_SC.ttf,sha256=uEhdcux...,8261128
```

`[事实]` 同一 sha256、同一字节数出现两次；10 个资源全部重复。

`[事实]` `MANIFEST.in:1` 是 `recursive-include amiyabot/assets *.ttf`，而真实目录是 `amiyabot/_assets`（`ls -d amiyabot/assets` → No such file）。

**影响** `[推断]`
- **wheel 体积翻倍**（约 11.4 MB，实际内容约 8.7 MB），安装/下载成本无谓增加。
- `.data/data/amiyabot/*` 把 `font/`、`markdown/js/`、`markdown/style/` **目录结构展平**，成为 10 个孤立文件——运行时**用不到**这段副本。
- 资源**没有丢失**（实测确认），因为 `include_package_data=True`（`setup.py:111`）+ git 追踪兜住了。但这是**偶然生效**，依赖 VCS 插件可用。

**修正**：此前静态推断「资源可能整体缺失」**已被实测否定**，此处如实修正。

**建议**
1. 删除 `setup.py:94-97,110` 的 `data_files` 逻辑（只产生无用重复）。
2. 修 `MANIFEST.in:1` → `recursive-include amiyabot/_assets *`。
3. 改用 `package_data` 显式声明。

**本次不改动。**

---

## 🟡 R-12 · 隐式依赖未声明

**证据** `[事实]` 以下 import 在 `requirements.txt` 中**无对应声明**：

| 包 | import 位置 |
|---|---|
| `websockets`（含 `websockets.legacy.client`） | `adapters/__init__.py:4,8` |
| `requests` | `network/download.py:4`、`qqGroup/api.py:3` |
| `certifi` | `network/download.py:2` |
| `pydantic` | `network/httpServer.py:3` |
| `wheel` | `setup.py:6`（构建期） |

**影响** `[推断]`
- 目前能工作是因为它们是已声明依赖的**传递依赖**（如 `amiyahttp` 带来 `websockets`/`pydantic`）。
- 一旦上游 `requirements.txt` 变更依赖树，本包会直接 `ImportError`——且失败点可能在 `import amiyabot` 顶层（`adapters/__init__.py:4`）。
- `setup.py:6` 依赖 `wheel` 但无 `setup_requires`，干净环境 `python setup.py bdist_wheel` 会 `ImportError`。

**建议** 把这些包显式加入 `requirements.txt`（或把 `websockets` 等提升为直接依赖声明）。

**本次不改动。**

---

## 🟡 R-14 · playwright 急切导入

**证据** `[事实]` 模块顶层导入，无延迟/降级：

```
browserService/__init__.py:1   from playwright.async_api import async_playwright, ...
browserService/launchConfig.py:2  from playwright.async_api import Browser, ...
browserService/pageContext.py:1   from playwright.async_api import Page
browserService/pagePool.py:3      from playwright.async_api import ViewportSize
```

`[事实]` 两条到达路径：
- `amiyabot/__init__.py:30` → `browserService/__init__.py:1`
- `messageChain/element.py:6`（`from ...browserService import *`）→ `messageChain/__init__.py:6` → `amiyabot/__init__.py:33`

**影响** `[推断]`
- `import amiyabot` **强制要求安装 `playwright`**，即便用户只用文字消息。
- playwright 是较重的依赖（含 Node 侧驱动），显著抬高安装成本与镜像体积。
- `[事实]` 浏览器**二进制**并非 import 期必需，只在 `browserService/__init__.py:28`（`launch()`）或 `element.py:106`（渲染 HTML）时才需要；`AmiyaBot.start(launch_browser=False)` 默认不启动（`amiyabot/__init__.py:66-70`）。

**建议** 把 `browserService` 改为函数内惰性导入或 `TYPE_CHECKING` 守卫 + `try/except ImportError` 降级，使「不装 playwright 也能用核心功能」。

**本次不改动。**

---

## 🟡 R-17 · `test` 适配器随包发布；`0.0.0.0` 下无鉴权

**证据** `[事实]`

- `[事实]` 随包发布：`setup.py:109` `find_packages(include=['amiyabot', 'amiyabot.*'])` 无排除；实测 wheel 含 `amiyabot/adapters/test/{__init__,builder,server}.py`。
- `[事实]` 默认绑定 `127.0.0.1:32001`（`adapters/test/__init__.py:14`）。

```python
# adapters/test/server.py:109
return f'http://%s:{self.port}/{temp_file_path}' % ('localhost' if self.host == '0.0.0.0' else self.host)
```

`[事实]` 端点 `/{appid}` **无 token、无白名单校验**（`test/server.py:40-44`）。`[事实]` base64 图片直接落盘 `testTemp/images/<random>.png`（`:99-107`），无大小/数量限制。

**影响** `[推断]`
- 若使用者把 `host` 改为 `0.0.0.0`（`server.py:109` 显式处理了这种情况，说明有人这么做），端点变为**网络可达且无鉴权**：任意人可注入伪造消息/事件**驱动机器人执行功能**。
- 无限制的 base64 落盘构成**磁盘耗尽**面。
- `[不确定]` 实际可利用性未做运行时验证；路由中 `appid` 未校验（`server.py:40`）。

**建议** 默认强制 loopback + 共享密钥校验 + 尺寸/配额限制；或在发布包中排除该子包。

**本次不改动。**

---
