# 风险与雷区 · API/兼容性分册（risks-api）

> 本文件是 [risks.md](risks.md) 的续篇，收录 🟡 中severity的 **API 文档与兼容性**类风险。
> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。所有结论附 `文件:行`。
> **本文档只描述风险，不做任何代码/配置改动。**

> ℹ️ 下文节号沿用母文档（R-7 起），便于对照。

---

## 🟡 R-7 · 无 `py.typed`，下游类型推断被静默忽略

**证据** `[事实]`

```
$ find . -name "py.typed" -o -name "*.pyi" | grep -v .venv
（无输出）
```

`[事实]` 但内部标注规范：`factory/factoryTyping.py:10-32` 定义整套 Callable 别名；`:35-84` 用 dataclass + 类型别名建模。

**影响** `[推断]`
- 本包对 mypy/pyright 呈现为 untyped，**下游拿不到任何类型信息**，错误只能运行时发现。
- 已投入的类型标注工作未被下游消费，投入产出比低。

**建议** 加 `py.typed` 并在 `setup.py` 声明 `package_data={'amiyabot': ['py.typed']}`；配套 `mypy --ignore-missing-imports` 做基线。

**本次不改动。**

---

## 🟡 R-9 · 无弃用机制、无语义化版本承诺、无 CHANGELOG

**证据** `[事实]`

- 弃用提示曾是**被注释掉的 `print()`**：`adapters/tencent/__init__.py`（原 `:10-17`）。非 `warnings.warn`，且当时整体注释 → **完全静默**。
- **该类已于本次移除**：`TencentBotInstance` / `TencentSandboxBotInstance` 已删除（原 `:4,7`），文件现仅剩 1 行 re-export。
- 版本号由 PyPI 自增决定（`setup.py:61-63`），**与改动性质无关**。
- 无 CHANGELOG（`ls CHANGELOG*` 无结果）、无 CONTRIBUTING。

**影响** `[推断]`
- 公开 API（`on_message` 参数、`Chain` 方法、`BotAdapterProtocol` 抽象方法）**无兼容性契约**。
- `[事实]` 使用旧类名（`TencentBotInstance`）的用户将直接得到 **`ImportError`**——因弃用提示从未真正生效（被注释、静默），用户**实际是在移除时才感知**的。这是「无正式弃用机制」的**实例证据**。
- `2.x` 内的 break change 无法从版本号预判，插件生态升级风险高。

**建议** 后续弃用改用 `warnings.warn(..., DeprecationWarning)`（本次移除已印证：静默提示 = 用户无预警）；建立 CHANGELOG；对公开 API 承诺 semver。

**本次已部分处理**（移除弃用类，见 [public-api.md](public-api.md) §4）。

---

## 🟡 R-10 · 3.11–3.13 声明支持但 CI 只跑 3.10

**证据** `[事实]`

| 项 | 值 | 来源 |
|---|---|---|
| `python_requires` | `>=3.10` | `setup.py:112` |
| CI matrix | 仅 `['3.10']` | `.github/workflows/pylint.yml:10` |
| 构建 Python | `3.10` | `.github/workflows/pypi.yml:22` |
| 3.13 条件依赖 | `audioop-lts~=0.2.1; python_version>='3.13'` | `requirements.txt:9` |
| 本机 | `3.13.3` | `python3 -c "import sys; print(sys.version)"` |
| `classifiers` | **无** | `setup.py:99-117` |

**影响** `[推断]`
- 3.13 支持是**声明式**的：`audioop-lts` 的存在证明作者有意支持（`audioop` 在 3.13 被移除），但没有 CI 验证。
- 无 `classifiers` 使 PyPI 页面缺少版本徽章与 license 分类。
- 用户装在不支持的组合上不会得到明确提示。

**建议** 扩展 CI matrix 到 `['3.10','3.11','3.12','3.13']`；补 `classifiers`。

**本次不改动。**

---

---

## 🟠 R-16 · 测试为零；质量门只有 pylint 且只在 PR

**证据** `[事实]`

```
$ ls pytest.ini tox.ini noxfile.py .pre-commit-config.yaml mypy.ini pyrightconfig.json setup.cfg pyproject.toml
（全部 No such file or directory）
$ find . -name "test_*.py" -o -name "*_test.py"
（无结果）
```

`[事实]` CI 唯一的检查步骤是 `pylint amiyabot --rcfile=pylint.conf`（`.github/workflows/pylint.yml:24`），触发条件 `on: [pull_request]`（`:3`）。

`[事实]` 仓库中 `amiyabot/adapters/test/` 是**测试用适配器**，不是测试套件。

**影响** `[推断]`
- 7,277 行核心框架**零自动化验证**；任何重构都无回归保护。
- `pypi.yml` 无质量门（`:24-34`），直接 push 到 master 可跳过 lint 并触发布。
- `black` 不在 CI，格式靠自觉（`scripts/black.sh:1`）。

**建议** 见 [testing-quality.md](testing-quality.md) §7 的优先补测清单；最小成本是把 `black --check` 加进 CI。

**本次不改动**（属 CI/测试，越界）。

---
