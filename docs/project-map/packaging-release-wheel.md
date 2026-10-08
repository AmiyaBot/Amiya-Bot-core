# 发布产物实测（packaging-release-wheel）

> 本文件是 [packaging-release.md](packaging-release.md) 的续篇 §8，记录对**正式 PyPI wheel** 的实际解包校验。
> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。
> 之所以单独成篇：本节含完整证据链（RECORD/sha256/METADATA），篇幅较长。

> ℹ️ 下文节号沿用母文档（§8），便于对照。

---

## 8. 发布产物实测（对正式 wheel 的解包校验）✅ 已实测

`[事实]` 方法与命令：

```bash
curl -sL -o real.whl \
  https://files.pythonhosted.org/packages/73/0f/f60c80bfb113df72b7550d77b0b9bb217eb5fdbe37f51fc04018e28cb892/amiyabot-2.1.0-535-py3-none-any.whl
# 大小 11,426,233 字节，与 PyPI JSON 记录一致
python3 -c "import zipfile; z=zipfile.ZipFile('real.whl'); print(len(z.namelist()))"
# → 100 个条目
```

`[事实]` `amiyabot-2.1.0.dist-info/WHEEL`：

```
Wheel-Version: 1.0
Generator: setuptools (79.0.1)
Root-Is-Purelib: true
Build: 535                ← 随机 build number 进了元数据
Tag: py3-none-any
```

### 8.1 关键发现：`_assets` **实际有发布**，但路径与预期不同

`[事实]` 静态推断曾担心资源缺失。**实测表明资源全部在 wheel 里，且每个文件出现了两次**：

| 落点 | 路径形态 | 条目数 | 是否符合运行时预期 |
|---|---|---|---|
| ① 包内正确路径 | `amiyabot/_assets/font/...`、`amiyabot/_assets/markdown/...` | 10 | ✅ 与 `imageCreator.py:15`、`messageChain/__init__.py:18` 的 `../../_assets/` 一致 |
| ② `data_files` 展平落点 | `amiyabot-2.1.0-535.data/data/amiyabot/*.ttf\|css\|js\|html` | 10 | ❌ 被**展平**、且多一层 `.data/data/` |

`[事实]` 路径①的完整清单（10 个，含目录结构）：

```
amiyabot/_assets/font/HarmonyOS_Sans_SC.ttf
amiyabot/_assets/font/font.css
amiyabot/_assets/markdown/template.html
amiyabot/_assets/markdown/js/highlight.min.js
amiyabot/_assets/markdown/js/marked.min.js
amiyabot/_assets/markdown/js/vue.min.js
amiyabot/_assets/markdown/style/github-markdown.css
amiyabot/_assets/markdown/style/github-markdown-dark.css
amiyabot/_assets/markdown/style/highlight/vs.min.css
amiyabot/_assets/markdown/style/highlight/vs2015.min.css
```

`[事实]` 路径②的完整清单（10 个，**目录结构丢失**）：

```
amiyabot-2.1.0-535.data/data/amiyabot/HarmonyOS_Sans_SC.ttf
amiyabot-2.1.0-535.data/data/amiyabot/font.css
amiyabot-2.1.0-535.data/data/amiyabot/github-markdown-dark.css
amiyabot-2.1.0-535.data/data/amiyabot/github-markdown.css
amiyabot-2.1.0-535.data/data/amiyabot/highlight.min.js
amiyabot-2.1.0-535.data/data/amiyabot/marked.min.js
amiyabot-2.1.0-535.data/data/amiyabot/template.html
amiyabot-2.1.0-535.data/data/amiyabot/vs.min.css
amiyabot-2.1.0-535.data/data/amiyabot/vs2015.min.css
amiyabot-2.1.0-535.data/data/amiyabot/vue.min.js
```

`[事实]` **RECORD 中的 sha256 完全一致**，证明①②是**同一份文件的两次落盘**。例如：

```
amiyabot/_assets/font/HarmonyOS_Sans_SC.ttf,sha256=uEhdcuxAuQMO4ZsQpdJKFN9EbptNm369VL_V83QWH3k,8261128
amiyabot-2.1.0-535.data/data/amiyabot/HarmonyOS_Sans_SC.ttf,sha256=uEhdcuxAuQMO4ZsQpdJKFN9EbptNm369VL_V83QWH3k,8261128
```

`[推断]` 因此 **wheel 体积被重复计算**：字体 8,261,128 字节被存了两遍，加上其余资源，wheel 约 11.4 MB，而实际内容约 8.7 MB。

### 8.2 为什么资源仍然进了 wheel（修正推断）

`[事实]` 路径①的存在说明 `include_package_data=True`（`setup.py:111`）+ git 追踪的文件被 setuptools 的 VCS 文件查找器纳入了。`[事实]` 10 个资源全部被 git 追踪（`git ls-files amiyabot/_assets | wc -l` → `10`），且在 `git ls-files` 的包目录范围内。

`[推断]` **修正结论**：`MANIFEST.in:1` 的失效目录名（`amiyabot/assets` vs `amiyabot/_assets`）**并未导致资源丢失**，因为真正起作用的是 `include_package_data` 的 VCS 追踪机制。此前「资源可能整体缺失」的静态推断**被实测否定**。

`[事实]` 但这属于**偶然正确**：它依赖 (a) VCS 插件可用、(b) 文件已 `git add`。`[推断]` 若从 sdist 或非 git 快照构建，结果可能不同。`[不确定]` 未验证 sdist 场景。

`[事实]` 路径②正是 `setup.py:94-97` + `:110` 那套 `data_files` 逻辑的产物，且**印证了「落点偏移」推断**：目标目录 `'amiyabot'` + 元素自带前缀，最终落到 `<pkg>.data/data/amiyabot/`，**并丢失了 `_assets` 与下级目录结构**。

### 8.3 实测修正后的结论表

| 原静态推断 | 实测结果 | 判定 |
|---|---|---|
| `_assets` 可能整体缺失 | 实际**完整存在**于 `amiyabot/_assets/**` | ❌ 推断被否定 |
| `data_files` 落点偏移 | **确认偏移**，落到 `.data/data/amiyabot/` 且展平 | ✅ 推断成立 |
| `MANIFEST.in` 完全失效 | 模式确实匹配不到，但被 VCS 机制兜住 | ⚠️ 部分成立 |
| `template.html` 等非 ttf 会漏 | 实际未漏（VCS 机制兜住） | ❌ 推断被否定 |
| wheel 体积浪费 | **确认浪费**，10 个资源存了两份 | ✅ 新发现 |

`[建议]` 实测指向的真实可优化点：
1. **删除或修正 `data_files` 逻辑**（`setup.py:94-97,110`）——它只产生重复且路径错误的副本，无正面价值。修掉可直接减小 wheel 体积。
2. 修正 `MANIFEST.in:1` 为 `recursive-include amiyabot/_assets *`，让 sdist 构建不依赖 VCS 插件兜底。
3. 改为 `package_data` 显式声明，语义最清晰。

### 8.4 METADATA 实测

`[事实]` `amiyabot-2.1.0.dist-info/METADATA`（节选）：

```
Metadata-Version: 2.4
Name: amiyabot
Version: 2.1.0                    ← 与 setup.py:101 的 0.1.0 不同，证明被覆盖
Summary: Python 异步渐进式机器人框架
License: MIT Licence
Requires-Python: >=3.10
Requires-Dist: amiyautils~=0.0.5  ← 与本地 requirements.txt:3 的 ~=0.0.4 不同
Dynamic: version ...              ← 无 classifiers 字段
```

`[事实]` METADATA **无 `Classifier:` 行**，与 §「无 classifiers」结论一致（`setup.py:99-117`）。

`[事实]` `Version: 2.1.0` 实测证实：`setup.py:101` 的 `0.1.0` 确实被 `setup.py:65` 的赋值覆盖。

`[事实]` `top_level.txt` 内容为 `amiyabot`（单行），确认导入名。
