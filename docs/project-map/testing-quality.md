# 测试与质量（testing-quality）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。

## 1. 结论先行

`[事实]` **本项目没有任何自动化测试**。

| 测试设施 | 状态 | 证据 |
|---|---|---|
| pytest | 无配置、无依赖、无用例 | `ls pytest.ini` 不存在；`requirements.txt` 无 pytest |
| unittest | 无用例文件 | `find . -name "test_*.py" -o -name "*_test.py"` → 无结果 |
| tox | 无 | `ls tox.ini noxfile.py` 均不存在 |
| coverage | 无 | 无 `.coveragerc` |
| hypothesis | 无 | 未声明 |
| CI 测试步骤 | **无** | `pylint.yml:11-24` 只有 checkout/setup/install/pylint |

`[事实]` 仓库中唯一名为 `test` 的目录是 **`amiyabot/adapters/test/`**，那是**测试用的适配器**（连接 `console.amiyabot.com` 测试控制台），**不是测试套件**：

- `adapters/test/__init__.py:27` `class TestInstance(BotAdapterProtocol)`
- `adapters/test/server.py:22` `class TestServer(HttpServer)`
- `[事实]` 全仓无任何地方 import 它（除自身）；它是**发布了但未导出**的可选适配器。

`[建议]` 首次为项目补测试时，优先覆盖无副作用的核心逻辑（见 §5）。

## 2. 测试框架与位置

`[事实]` 无。

`[事实]` 唯一的「验证手段」是：
1. 手动 `pylint`（`scripts/pylint.sh:1`）
2. 手动 `black`（`scripts/black.sh:1`）
3. 通过 `adapters/test` 连测试控制台做人工联调（`adapters/test/__init__.py:40` 提示走 `https://console.amiyabot.com/#/test`）

`[推断]` 第 3 条是实际的「集成测试」替代品，但它是**手动、外部、不可自动化**的。

## 3. 如何运行（现状）

`[事实]` 无测试命令可跑。可跑的质量命令：

```bash
# lint（CI 会跑，PR 门禁）
pylint amiyabot --rcfile=pylint.conf

# 格式化（CI 不跑，需本地手动）
black amiyabot --skip-string-normalization --line-length 120
```

`[事实]` 证据：`scripts/pylint.sh:1`、`scripts/black.sh:1`、`.github/workflows/pylint.yml:24`。

`[建议]` **本次不执行** pylint/black（遵守「只识别配置、不贸然全量执行」约束）。若要跑，注意 `pylint.conf` 有 660+ 行配置，首次运行耗时较长。

## 4. CI 实际跑什么

`[事实]` 逐字对照两条 workflow：

### `pylint.yml`（PR 门禁）

| 步骤 | 内容 | 行 |
|---|---|---|
| 触发 | `pull_request` | `:3` |
| Python | 矩阵 `['3.10']` | `:10` |
| 安装 | `pip install -r requirements.txt` + `pip install pylint` | `:19-21` |
| 清理 | `pylint amiyabot --rcfile=pylint.conf` | `:24` |

`[事实]` **CI 会安装并跑 pylint**，但**不会**：
- 跑任何测试（无测试）
- 跑 `black` 格式检查
- 跑类型检查（mypy/pyright 均未配置）
- 在多 Python 版本上验证

### `pypi.yml`（发布）

`[事实]` 仅构建 + 发布，无任何质量门（`:24-34`）。

`[推断]` 综合：**质量门只有 pylint 一道，且只在 PR 上**。直接 push 到 master 会绕过 lint 并触发布（`pypi.yml:3-6`）。见 [risks.md](risks.md) R-3、R-16。

## 5. 覆盖率与类型检查

`[事实]` **覆盖率：无**。无 coverage 工具、无阈值、无报告。

`[事实]` **类型检查：无**。逐项确认：

| 工具 | 配置 | 结论 |
|---|---|---|
| mypy | `mypy.ini` / `setup.cfg` / `pyproject.toml` 都不存在 | 无 |
| pyright | `pyrightconfig.json` 不存在 | 无 |
| `py.typed` | 不存在 | 无 |
| `.pyi` 存根 | 不存在 | 无 |

`[事实]` 但源码**内部标注质量不低**：`factory/factoryTyping.py:10-32` 有完整 Callable 别名，`:35-84` 用 `dataclass` + 类型别名建模。

`[推断]` 类型标注是「写给人和 IDE 的」，未进入验证闭环（无检查器）。

`[建议]` 见 [risks.md](risks.md) R-7。

## 6. Lint 与格式化配置细节

`[事实]` **pylint**（`pylint.conf`，22301 字节，660+ 行）：

| 项 | 值 | 行 |
|---|---|---|
| `max-line-length` | `120` | `:339` |
| `disable` | 一长串（起始 `:423`） | `:423+` |
| `enable` | `c-extension-no-member` | `:472` |
| `ignore` | `CVS` | `:49` |
| `ignore-comments` / `ignore-docstrings` / `ignore-imports` / `ignore-signatures` | 均 `yes` | `:533,536,539,542` |
| `ignored-argument-names` | `_.*\|^ignored_\|^unused_` | `:660` |
| `ignore-long-lines` | 放过纯 URL 行 | `:329` |

`[事实]` `[推断]` `ignore-docstrings=yes` 意味着缺失 docstring 不报错——与代码中大量中文 docstring 并存，说明是刻意放宽。

`[事实]` **black**：`--skip-string-normalization --line-length 120`（`scripts/black.sh:1`）。

`[事实]` `[建议]` **black 与 pylint 的 `disable` 列表未对齐验证**，且 `black` 不在 CI。`[推断]` 本地跑 black 后可能引入 CI 看不到的格式漂移。

`[事实]` **无 `isort`、无 `ruff`、无 `pre-commit`**：

```
$ ls .pre-commit-config.yaml
No such file or directory
```

`[事实]` 但 `.editorconfig` 存在并规定：`indent_style=space`、`indent_size=4`、`end_of_line=lf`、`insert_final_newline=true`、`trim_trailing_whitespace=true`（`.editorconfig:3-8`）。`[推断]` 这是唯一的跨编辑器一致性保障。

## 7. 改动后的最小验证闭环（[建议]，当前并不存在）

`[事实]` 当前**没有可自动执行的验证闭环**；以下是**建议建立**的最小闭环，按「性价比」排序：

| 优先级 | 动作 | 为什么 | 可行性 |
|---|---|---|---|
| P0 | `python -c "import amiyabot"` | 验证包可导入、依赖齐、无语法错 | `[事实]` 立即可用 |
| P0 | `pylint amiyabot --rcfile=pylint.conf` | 与 CI 一致，避免 PR 被拒 | `[事实]` 立即可用 |
| P1 | `black --check amiyabot --skip-string-normalization --line-length 120` | 统一风格（加 `--check` 才可入 CI） | 需装 black |
| P2 | 补纯逻辑单测（见下） | 目前零测试 | 需装 pytest |
| P3 | `mypy amiyabot --ignore-missing-imports` | 现有标注够多，收益快 | 需装 mypy |

`[建议]` **零副作用、最适合优先补测的模块**（纯函数/纯数据结构，不触网不落盘）：

| 目标 | 位置 | 测什么 |
|---|---|---|
| `MessageMatch.check_str/equal/reg` | `builtin/message/__init__.py:168-190` | 关键字匹配三态 |
| `text_convert` | `builtin/message/structure.py:97` | 中文数字/分词归一 |
| `MessageHandlerItemImpl.update_data` | `factory/implemented.py:34-42` | 前缀剥离 |
| `Chain` 链式构造 | `builtin/messageChain/__init__.py:21-222` | 元素顺序/自动 at |
| `ver_num` / `incr_version` | `setup.py:10,30` | **版本自增规则**（纯函数，易测，且是最高风险点） |
| `create_image` | `builtin/lib/imageCreator.py:112` | 文字转 PNG 尺寸/颜色标记 |
| `EventBus.publish/subscribe` | `builtin/lib/eventBus.py:15,23` | 订阅分发 |
| `choice_handlers` 排序 | `handler/messageHandler.py:133` | 权重择优、waiter 优先 |

`[建议]` `setup.py` 的 `incr_version` 是**纯函数且是发版核心**（`1.9.9→2.0.0` 边界），零测试覆盖下最值得先补。`[事实]` 该函数逻辑在 `setup.py:30-44`，分支覆盖点约 5 个。

## 8. 证据命令

```
ls pytest.ini tox.ini noxfile.py .pre-commit-config.yaml mypy.ini pyrightconfig.json setup.cfg pyproject.toml
find . -name "test_*.py" -o -name "*_test.py"
find . -name "py.typed" -o -name "*.pyi"
grep -n "max-line-length\|^disable\|^enable" pylint.conf
cat .github/workflows/pylint.yml
cat scripts/pylint.sh scripts/black.sh
cat .editorconfig
```

## 相关文档

- 运行环境 → [runbook.md](runbook.md)
- CI 与发布 → [packaging-release.md](packaging-release.md)
- 风险排序 → [risks.md](risks.md)
