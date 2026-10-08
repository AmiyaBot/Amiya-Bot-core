# 打包与发布（packaging-release）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。所有结论附 `文件:行` 或命令输出。

## 1. 构建后端与打包配置

`[事实]` **legacy setuptools，`setup.py` 单文件驱动，无 `pyproject.toml`**。

```
$ ls pyproject.toml setup.cfg tox.ini noxfile.py
（全部 No such file or directory）
```

| 配置文件 | 状态 | 证据 |
|---|---|---|
| `pyproject.toml` | **不存在** | `ls` 报错 |
| `setup.py` | 存在，119 行，唯一构建入口 | `setup.py:1-119` |
| `setup.cfg` | **不存在** | `ls` 报错 |
| `MANIFEST.in` | 存在，仅 1 行 | `MANIFEST.in:1` |
| `wheel` 依赖 | 代码直接 `from wheel.bdist_wheel import bdist_wheel` | `setup.py:6` |

`[事实]` `setup.py:4` `import setuptools`，`:99` `setuptools.setup(...)` → 后端为 setuptools（非 hatchling/poetry/flit/pdm/maturin）。

`[建议]` `[事实]` `setup.py:6` **硬依赖 `wheel` 包**，但 `requirements.txt` 里没有 `wheel`，`setup.py` 也没有 `setup_requires`。本地 `pip install .` 或构建时需要预先有 `wheel`；CI 里靠 `.github/workflows/pypi.yml:27` `pip install setuptools wheel twine` 显式补上。`[推断]` 直接 `python setup.py bdist_wheel` 在没有 wheel 的环境会 `ImportError`。

`[建议]` 迁到 `pyproject.toml` + PEP 621 是长期方向，但因版本号来自构建期联网（见 §3），迁移需先解决版本来源问题。**本次不改动。**

## 2. 版本号如何产生和同步（本项目最关键机制）

`[事实]` **源码中不存在 `__version__`**：

```
$ grep -rn "__version__" --include="*.py" amiyabot/
（无输出）
```

`[事实]` `setup.py:101` 写了 `version='0.1.0'`，但**该值从不生效**——它在 `bdist_wheel` 阶段被覆盖：

```python
# setup.py:60-73  CustomBdistWheelCommand.finalize_options()
latest_version = get_new_version()          # :61  联网取 PyPI 最新版
if self.auto_increment_version:             # :62
    new_version = incr_version(latest_version)   # :63  自增
    print(f'Auto-incrementing version to: {new_version}')
    self.distribution.metadata.version = new_version   # :65  覆盖
else:
    new_version = incr_version(latest_version)
    release_new = input(f'new?: {new_version} (Y/n)')  # :68  交互式提问！
    ...
self.distribution.metadata.version = new_version   # :73
```

`[事实]` 三条支撑函数：

| 函数 | 行为 | 证据 |
|---|---|---|
| `ver_num(v)` | `'2.1.0'`→`210`；`<1000` 时 ×10 | `setup.py:10-14` |
| `get_new_version()` | 请求 `https://pypi.python.org/pypi/amiyabot/json`，取 `releases` 最大版 | `setup.py:17-25` |
| `incr_version(v)` | `1.0.9`→`1.1.0`；`1.9.9`→`2.0.0`；非三段则补 `.1` | `setup.py:30-44` |

`[事实]` 实测当前状态：本地 `0.1.0`，PyPI 最新 `2.1.0`（PyPI JSON `info.version`），共 51 个版本。

`[事实]` **版本不写入任何源码或文件**，只在内存里改 `distribution.metadata.version`。`[推断]` 后果：

1. 源码树永远是 `0.1.0`，与发布版无关。
2. `import amiyabot; amiyabot.__version__` → `AttributeError`。`[推断]`（由 grep 无 `__version__` 推出）
3. 运行时只能靠 `importlib.metadata.version('amiyabot')`（需已安装）或 `pip show amiyabot` 取版本。
4. `git tag` 从未打过（`git tag` 输出为空），版本与提交无对应关系。`[事实]`

`[建议]` 见 [risks.md](risks.md) R-1、R-2。**本次不改动。**

## 3. 随机 build number（污染文件名的来源）

`[事实]` `setup.py:75-77`：

```python
# 加入一个随机数的BuildNumber保证Action可以重复执行
build_number = random.randint(0, 1000)
self.build_number = f'{build_number}'
```

`[事实]` 该值进入了实际发布产物名——PyPI 上 2.1.0 的文件名是：

```
amiyabot-2.1.0-535-py3-none-any.whl      (11,426,233 bytes, upload_time 2026-02-25T08:01:29)
```

其中 `535` 即随机数。`[事实]` 注释自述目的是「保证 Action 可以重复执行」（避免同版本重复上传被 PyPI 拒绝）。`[推断]` 这是用**污染产物名**换取「重复构建不报错」的权衡。

`[建议]` 更规范的做法是：版本号已在 PyPI 侧唯一，重复构建本就应该被拒绝而非绕过。**本次不改动。**

## 4. 包数据与 MANIFEST（已确认存在缺陷）

`[事实]` **MANIFEST.in 指向不存在的目录**：

```ini
# MANIFEST.in:1
recursive-include amiyabot/assets *.ttf
```

```
$ ls -d amiyabot/assets
ls: amiyabot/assets: No such file or directory
$ ls -d amiyabot/_assets
amiyabot/_assets
```

`[事实]` 真实资源目录是 `amiyabot/_assets`（**带下划线**），MANIFEST.in 写的是 `amiyabot/assets`（**无下划线**）。`[事实]` 全仓除 MANIFEST.in 外**没有任何地方**引用 `amiyabot/assets`：

```
$ grep -rn "assets" --include="*.py" amiyabot/ setup.py
setup.py:95:  for root, dirs, files in os.walk('amiyabot/_assets'):
imageCreator.py:15:  ...'../../_assets/font/HarmonyOS_Sans_SC.ttf'
messageChain/__init__.py:18:  ...'../../_assets/markdown/template.html'
```

`[事实]` MANIFEST.in 历史上只被改过一次，即初始提交（`git log --oneline -- MANIFEST.in` 仅 1 条），而 `_assets` 目录后续有多次独立提交。`[推断]` 该文件**陈旧失修**，目录改名时未同步。

`[事实]` `_assets` 下 **10 个文件、无 `__init__.py`**，因此不是 Python 包：

```
amiyabot/_assets/font/HarmonyOS_Sans_SC.ttf
amiyabot/_assets/font/font.css
amiyabot/_assets/markdown/js/{highlight,marked,vue}.min.js
amiyabot/_assets/markdown/style/github-markdown{,-dark}.css
amiyabot/_assets/markdown/style/highlight/{vs,vs2015}.min.css
amiyabot/_assets/markdown/template.html          (共 8.2 MB)
```

`[事实]` `setup.py:94-97` 的收集逻辑：

```python
data_files = []
for root, dirs, files in os.walk('amiyabot/_assets'):
    for item in files:
        data_files.append(os.path.join(root, item))   # 收集的是「含目录前缀的相对路径」
```

`[事实]` `setup.py:110` `data_files=[('amiyabot', data_files)]`——**目标目录已是 `amiyabot`，而每个元素又自带 `amiyabot/_assets/...` 前缀**。

`[推断]` 三重问题：

1. **MANIFEST.in 完全失效**：模式匹配不到任何文件（目录名错），且即便改对，`*.ttf` 也只收字体，**漏掉 `font.css`、`template.html`、全部 js/css**。而 `template.html` 是 `Chain.markdown()` 的必需模板（`messageChain/__init__.py:18,190`）。`[事实]`（模式过窄）+ `[推断]`（后果）
2. **sdist 中资源可能缺失**：`include_package_data=True`（`:111`）只对**包内**文件生效，而 `_assets` 非包（无 `__init__.py`）。`[推断]`
3. **wheel 中落点可能偏移**：`data_files` 元素含 `amiyabot/` 前缀 + 目标目录 `'amiyabot'`，可能落到 `amiyabot/amiyabot/_assets/...`，与运行时期望的 `<site-packages>/amiyabot/_assets/`（`imageCreator.py:15`、`messageChain/__init__.py:18` 用 `../../_assets/` 相对定位）不一致。`[不确定]` 未实机构建验证。

`[事实]` **已对 PyPI 上的正式 wheel 做实际解包校验**（下载 11,426,233 字节的 `amiyabot-2.1.0-535-py3-none-any.whl`，读 `namelist()` 与 `RECORD`）。结论**修正了纯静态推断**，见 §8。

`[建议]` 修法与优先级见 [risks.md](risks.md) R-4。**本次不改动。**

## 5. 入口点

`[事实]` `setup.py:99-117` 的 `setuptools.setup(...)` **没有 `entry_points` 参数**：

```
$ grep -n "entry_points\|console_scripts\|gui_scripts" setup.py
（无输出）
```

`[事实]` 因此：

- **无 `console_scripts`** → 安装后不产生任何命令。
- **无 `gui_scripts`**。
- **无插件 entry points 机制**：插件不做 entry-point 发现，而是在运行时由 `BotInstance.load_plugin()` 动态加载目录 / `.py` / zip（`factory/__init__.py:230-268`），统一以模块属性 `bot` 作为实例（`:261`）。

`[事实]` 项目类型因此是**库/框架**，使用方式为 `README.md:27-41` 的 `asyncio.run(bot.start())`。

## 6. CI/CD 发布流程

`[事实]` 两条 workflow，职责分离：

### 6.1 `pypi.yml` — 发布（Trusted Publishing）

| 项 | 值 | 行 |
|---|---|---|
| 触发 | `push` 到 `master` | `:3-6` |
| runner | `ubuntu-latest`，Python `3.10` | `:11`,`:22` |
| 环境 | `environment: release` | `:12` |
| 权限 | `id-token: write` | `:13-14` |
| 构建 | `python setup.py bdist_wheel --auto-increment-version` | `:31` |
| 发布 | `pypa/gh-action-pypi-publish@release/v1` | `:34` |

`[事实]` **全文件无任何 `secrets.` 引用** → 采用 OIDC Trusted Publishing，**无长期 token 泄漏面**。这是本仓库安全实践上的亮点。

`[事实]` `--auto-increment-version`（`:31`）对应 `setup.py:50-53` 的自定义 option，使 `finalize_options` 走 `:62-65` 分支**跳过交互式 `input()`**。`[推断]` 若手动构建忘带该 flag，`setup.py:68` 的 `input()` 会在非交互环境挂起或 `EOFError`。

### 6.2 `pylint.yml` — 质量门

| 项 | 值 | 行 |
|---|---|---|
| 触发 | `pull_request` | `:3` |
| Python | 矩阵仅 `['3.10']` | `:10` |
| 步骤 | 装 `requirements.txt` + `pylint` → `pylint amiyabot --rcfile=pylint.conf` | `:20-24` |

`[事实]` **CI 中没有任何测试步骤**（无 pytest/unittest/coverage）。

## 7. 是否发布到 PyPI / TestPyPI

`[事实]` **发布到正式 PyPI，无 TestPyPI 环节**。

| 项 | 值 | 证据 |
|---|---|---|
| 目标 | 正式 PyPI | `.github/workflows/pypi.yml:34` 无 `repository-url`（该参数缺失即默认 PyPI；TestPyPI 需显式指定） |
| 最新版本 | `2.1.0` | PyPI JSON `info.version` |
| 版本总数 | 51 | `len(releases)` |
| 首次发布 | `2022-05-31` | PyPI JSON 最早 `upload_time` |
| 发布间隔 | — | `[推断]` master 每次 push 都可能发版 |

`[建议]` 无 TestPyPI 预发布环节，意味着**发布验证只能靠正式包**。见 [risks.md](risks.md) R-3。
## 8. 发布产物实测 → 见 [packaging-release-wheel.md](packaging-release-wheel.md)

`[事实]` 已对 PyPI 正式 wheel（`amiyabot-2.1.0-535-py3-none-any.whl`，11,426,233 字节）做解包校验，读取 `namelist()` / `RECORD` / `METADATA` / `WHEEL`。

**核心结论**（详见续篇）：

| 结论 | 说明 |
|---|---|
| ✅ 资源**未丢失** | 10 个 `_assets` 文件均在 `amiyabot/_assets/**`，与运行时预期一致 |
| ⚠️ 资源**被重复落盘** | 同一份文件（sha256 相同）另存一份到 `.data/data/amiyabot/*`，且**目录结构被展平** |
| ✅ 版本覆盖**已证实** | METADATA 为 `Version: 2.1.0`，证明 `setup.py:101` 的 `0.1.0` 被 `:65` 覆盖 |
| ❌ 原「资源可能整体缺失」推断 | **被实测否定**（`include_package_data` + git 追踪兜住） |

`[建议]` 可优化点：删除 `setup.py:94-97,110` 的 `data_files` 逻辑（只产生无用重复，浪费约 2.7 MB）；修正 `MANIFEST.in:1` 目录名。

**本次不改动。**

---

## 9. 发布注意事项（操作清单）

`[事实]` 由上述证据汇总，发布相关必须知道的点：

1. **push 到 `master` 即触发发布**（`.github/workflows/pypi.yml:3-6`）。`[事实]` 当前分支就是 `master`。
2. **版本号不是你填的**：由 PyPI 最新版自增决定（`setup.py:61-63`）。要让版本体现出预期语义，只能靠控制发布时机。
3. **手动构建必须带 `--auto-increment-version`**，否则 `setup.py:68` 会交互式提问。
4. **手动构建需要能联网到 PyPI**（`setup.py:18`），离线构建会失败。
5. **批量发布脚本**：`scripts/publish.sh:1` 是 `twine upload dist/*`（面向手动场景，与 CI 的 OIDC 路径并存）。
6. **构建环境需预装 `wheel`**（`setup.py:6`）。

`[建议]` 本仓库发布流程的核心风险是「merge PR → 意外发版 → 永久占用 PyPI 版本号」（PyPI 版本不可删除、不可覆盖）。详见 [risks.md](risks.md) R-3。

---

## 10. 已解决 / 仍待验证

- ✅ `[事实]` 正式 wheel 内 `_assets` 的实际落点 → 已实测确认，见 [packaging-release-wheel.md](packaging-release-wheel.md)。
- `[不确定]` 仍待验证：**sdist**（`.tar.gz`）中 `_assets` 是否完整——本次只校验了 wheel 分发包。`[推断]` 若 sdist 在非 git 环境构建，因 `MANIFEST.in:1` 失效可能存在缺失风险。

---

## 相关文档

- 版本来源与项目身份 → [overview.md](overview.md)
- **发布产物实测详情** → [packaging-release-wheel.md](packaging-release-wheel.md)
- 依赖与 extras → [dependencies.md](dependencies.md)
- 风险排序 → [risks.md](risks.md)
