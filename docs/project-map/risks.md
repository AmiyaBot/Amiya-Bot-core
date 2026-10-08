# 风险与雷区（risks）

> 证据约定：`[事实]` / `[推断]` / `[建议]` / `[不确定]`。所有结论附 `文件:行` 或命令输出。
> **本文档只描述风险，不做任何代码/配置改动。**

## 0. 风险总览（按严重程度）

`[事实]` 共 21 条风险。本文件保留 🔴/🟠 高风险，🟡/🟢 已拆到分册（见「详见」列）。
`[事实]` R-20 经复核已撤回（判定为有意行为），保留编号并标注「已撤回」，便于对照历史结论。

| ID | 风险 | 严重度 | 类别 | 详见 |
|---|---|---|---|---|
| R-3 | push 到 master 即自动发布正式 PyPI | 🔴 高 | 发布安全 | 本文件 |
| R-5 | `@table` 自动 `drop_column` 静默删列丢数据 | 🔴 高 | 数据安全 | 本文件 |
| R-1 | 版本号构建期联网 + 自增，与改动无关 | 🔴 高 | 版本/发布 | 本文件 |
| R-2 | 无 `__version__`，运行时无法感知版本 | 🟠 中高 | 版本 | 本文件 |
| R-15 | `headers` property 内同步 `requests`（已知设计约束，缓存判定使其低频） | 🟡 中 | 性能/设计妥协 | 本文件 |
| R-6 | 重连无界、无退避；QQ 频道递归 `create_task` 泄漏 | 🟠 中高 | 稳定性 | 本文件 |
| ~~R-20~~ | ~~`verify()` 原地改写 `self.keywords`~~ → **已撤回，非缺陷** | — | 已澄清 | 本文件 |
| R-4 | `data_files` 重复落盘 + 展平；`MANIFEST.in` 失效 | 🟡 中 | 打包 | [packaging](risks-packaging.md) |
| R-12 | 隐式依赖未声明（websockets/requests/certifi/pydantic/wheel） | 🟡 中 | 依赖 | [packaging](risks-packaging.md) |
| R-14 | playwright 急切导入，强制安装浏览器库 | 🟡 中 | 依赖/体积 | [packaging](risks-packaging.md) |
| R-17 | `test` 适配器随包发布，`0.0.0.0` 下无鉴权 | 🟡 中 | 安全面 | [packaging](risks-packaging.md) |
| R-7 | 无 `py.typed`，下游类型推断被静默忽略 | 🟡 中 | 类型 | [api](risks-api.md) |
| R-9 | 无弃用机制、无语义化版本承诺、无 CHANGELOG | 🟡 中 | API 兼容 | [api](risks-api.md) |
| R-10 | 3.11–3.13 声明支持但 CI 只跑 3.10 | 🟡 中 | 兼容性 | [api](risks-api.md) |
| R-16 | 测试为零；质量门只有 pylint 且只在 PR | 🟠 中高 | 质量 | [api](risks-api.md) |
| R-8 | `BotAdapterProtocol` 非真 ABC，抽象方法不强制 | 🟢 低中 | API 正确性 | [low](risks-low.md) |
| R-13 | 依赖声明漂移（amiyautils 本地 0.0.4 / 线上 0.0.5） | 🟢 低中 | 依赖 | [low](risks-low.md) |
| R-11 | `setup.py` 构建时**写回** `requirements.txt` | 🟢 低 | 副作用 | [low](risks-low.md) |
| R-18 | 硬编码 URL，无代理/自建域名支持 | 🟢 低 | 可配置性 | [low](risks-low.md) |
| R-19 | `choice_handlers` 深拷贝 × N + 无并列保护 | 🟢 低 | 性能/确定性 | [low](risks-low.md) |
| R-21 | `signal.signal` 在 import 时执行（模块级副作用） | 🟢 低中 | 副作用 | [low](risks-low.md) |
| R-22 | 无 `SIGTERM` 处理，容器场景不优雅关停 | 🟢 低 | 稳定性 | [low](risks-low.md) |

---

## 🔴 R-3 · push 到 master 即自动发布正式 PyPI

**证据** `[事实]`

```yaml
# .github/workflows/pypi.yml
on:
    push:
        branches:
            - master          # :3-6  ← push 即触发
...
    environment: release      # :12
    permissions:
        id-token: write       # :13-14
...
        run: python setup.py bdist_wheel --auto-increment-version   # :31
        uses: pypa/gh-action-pypi-publish@release/v1               # :34
```

`[事实]` 当前分支即 `master`（`git rev-parse --abbrev-ref HEAD`）。

**影响** `[推断]`
- 任何直接 push 到 master（含 merge PR）都会**自动构建并发布一个新版本到正式 PyPI**。
- PyPI 版本号**不可删除、不可覆盖、不可重用**，误发版是永久后果。
- 版本号由 PyPI 最新版自增决定（`setup.py:61-63`），因此误发的版本会**永久占用一个版本号**。
- 配合「质量门只在 PR」（R-16），直接 push 连 pylint 都跳过。

**建议**
1. 把 `on: push` 改为 `on: release: types: [published]` 或 `workflow_dispatch`，让发版成为**显式动作**。
2. 若保留 push 触发，至少加 `paths:` 过滤或加一个「版本已变更」的前置检查。
3. 先接 TestPyPI 做一次预演（当前无 TestPyPI 环节）。

**本次不改动**（属 CI 配置，越界）。

---

## 🔴 R-5 · `@table` 自动 `drop_column` 静默删列丢数据

**证据** `[事实]` `amiyabot/database/__init__.py:63-90`：

```python
def table(cls: ModelClass) -> Any:
    ...
    model_columns = [f for f, n in cls.__dict__.items() ...]   # :74
    table_columns = [n[0] for n in description]                # :75
    migrate_list = []
    # 取 AB 差集增加字段
    for f in set(model_columns) - set(table_columns):
        migrate_list.append(migrator.add_column(table_name, f, getattr(cls, f)))   # :81
    # 取 BA 差集删除字段
    for f in set(table_columns) - set(model_columns):
        migrate_list.append(migrator.drop_column(table_name, f))                   # :85
    if migrate_list:
        migrate(*tuple(migrate_list))                          # :88
```

**影响** `[推断]`
- 装饰器在**每次启动**运行（`create_table()` + 差集比对）。
- 只要模型里**改名或删除**一个字段，`table_columns - model_columns` 就非空 → 启动即 `DROP COLUMN` → **该列数据永久丢失，无备份、无确认、无日志**。
- 反向地，新增字段会 `ADD COLUMN`。这在「快节奏改插件」时很方便，但代价是**无法安全地重构 schema**。
- 插件作者一旦改字段名，所有用户升级后数据静默消失。

**建议**
1. 至少把 `drop_column` 改为**显式 opt-in**（如 `@table(auto_drop=False)` 默认关闭）并打印醒目警告。
2. 生产环境改为使用正式迁移工具（peewee-migrate / Alembic）。
3. 在 `risks` 之外，文档层面已提示：**改 peewee 模型的字段名 = 删列**。

**本次不改动**（属源代码，越界）。

---

## 🔴 R-1 · 版本号构建期联网 + 自增，与改动无关

**证据** `[事实]` `setup.py:17-25`：

```python
def get_new_version():
    pypi = json.loads(request.urlopen('https://pypi.python.org/pypi/amiyabot/json').read())  # :18
    v_list = {ver_num(v): v for v in pypi['releases'].keys()}                                # :19
    s_list = sorted(v_list)
    latest = v_list[s_list[-1]]
    return f'{latest}'
```

配合 `setup.py:61-65`（自增并覆盖 `distribution.metadata.version`）。

**影响** `[推断]`
- 版本号**不表达改动性质**：patch 还是 major 纯由「PyPI 上一个版本 +1」决定（`setup.py:30-44`）。
- 构建**必须联网**到 PyPI；离线/镜像环境构建失败。
- `ver_num()`（`setup.py:10-14`）把 `'2.1.0'`→`210`，但 `'1.10.0'`→`1100`，排序正确；然而 `'0.2.0'`→`20`，`'1.0.0'`→`100`——`<1000` 时 ×10 的规则在 `'10.0.0'`→`1000`（不乘）与 `'99.9.9'` 等边界上语义混乱。`[不确定]` 未穷举验证该换算的单调性；`[建议]` 至少补单测（见 [testing-quality.md](testing-quality.md) §7）。
- 无 git tag（`git tag` 为空），发布与提交无对应。

**建议** 引入静态版本（`__version__` 或 `pyproject.toml`）+ git tag，构建期不再联网。

**本次不改动。**

---

## 🟠 R-2 · 无 `__version__`，运行时无法感知版本

**证据** `[事实]`

```
$ grep -rn "__version__" --include="*.py" amiyabot/
（无输出）
```

`[事实]` `setup.py:101` 的 `version='0.1.0'` 被 `:65` 覆盖；实测 wheel METADATA 为 `Version: 2.1.0`。

**影响** `[推断]`
- `import amiyabot; amiyabot.__version__` → `AttributeError`。
- 插件/框架无法在运行时做版本判断或兼容分支。
- 用户报 bug 时无法从代码自报版本，只能靠 `pip show`。

**建议** 增加 `__version__`，来源可用 `importlib.metadata.version('amiyabot')` 并带 fallback。

**本次不改动。**

---

## 🟡 R-15 · `headers` property 内同步 `requests`（**已知设计约束，不改动**）

**证据** `[事实]` `amiyabot/adapters/tencent/qqGroup/api.py:17-45`：

```python
@property
def headers(self):                                      # :18
    if not self.access_token or self.expires_time - time.time() <= 60:   # :19  ← 缓存判定
        try:
            res = requests.post(                        # :21  ← 同步调用
                url='https://bots.qq.com/app/getAppAccessToken',
                ..., timeout=3,                          # :32  ← 超时上限
            )
            data = json.loads(res.text)
            self.access_token = data['access_token']     # :36  写入缓存
            self.expires_time = int(time.time()) + int(data['expires_in'])   # :37
        except Exception as e:
            log.error(e, desc='accessToken requests error:')   # :39-40  静默吞掉
    return {'Authorization': f'QQBot {self.access_token}', ...}   # :42-45
```

**实际触发频率** `[事实]`（此项经项目作者确认，并已由代码复核）：

- `:19` 的守卫使得请求**并非每次调用都执行**：仅当 `access_token` 为空（首次）或剩余有效期 **≤ 60 秒**时才会发请求；其余情况直接走 `:42` 返回缓存值。
- token 有效期由响应 `expires_in` 决定（`:37`），通常为小时级，因此**实际请求频率很低**。
- `:32` 的 `timeout=3` 是**超时上限**，不是实际耗时；正常请求远快于此。

**影响** `[事实]`/`[推断]`
- 请求发生时同步调用会占用事件循环；但频率低、耗时短，**实际影响有限**。
- `[事实]` property 内做带副作用的网络 I/O（写 `access_token`/`expires_time`，`:36-37`），违反「property 应无副作用、可重复读取」的惯例——**设计妥协**，非疏漏。
- `[事实]` `except Exception`（`:39`）吞掉失败后仍返回 `'QQBot '`（**空 token**）的 Authorization 头（`:43`），故障表现为下游 401 而非明确报错。

**为何不能改成异步（重要约束）** `[事实]` `headers` 是适配器层的**统一同步契约**，被 **15 处**读取点依赖（`kook/api.py:24,32,40,67`；`qqGuild/api.py:40,48,54,62`；`onebot/v11/api.py:19,27,35`；`onebot/v12/api.py:26`；`adapters/__init__.py:154`），由 `@property` 与实例属性两种机制实现（共 8 处定义点，清单见 [modules/adapters.md](modules/adapters.md) §2.4）。

`[推断]` 若单独把 `qqGroup` 的 `headers` 改为 `async def`，同一名字在 5 个适配器中语义分裂（协程 vs dict）。任何按 `adapter.api.headers` 的统一写法——**包括第三方插件**——都会在 QQ 群适配器上拿到 coroutine 并报错 → **大面积用户故障**。该契约**不可单方面改动**，完整约束见 [modules/adapters.md](modules/adapters.md) §2.4。

**决策记录** `[事实]` 经项目作者决策：**保持现状，不改动代码**。理由为「请求并非每次执行，且请求耗时很短，暂不考虑改动」。本条因此从 🟠 中高降级为 🟡 中，性质由「缺陷」改为「**已知设计约束**」。

`[建议]` 若将来确需消除事件循环占用，**唯一不破坏契约**的方向是：仍保留 `headers` 为**无副作用的同步 property**（仅读缓存），把 token 刷新移到后台异步任务（可复用 `TasksControl.add_timed_task`，`builtin/lib/timedTask/__init__.py:27`）提前刷新。**本次未采用**（会让 token 到期时存在短暂旧值窗口）。

**本次不改动。**

---

## 🟠 R-6 · 重连无界 / 无退避 / 递归任务泄漏

**证据** `[事实]` 五个适配器均为无限 10 秒重连：

| 适配器 | 位置 |
|---|---|
| KOOK | `adapters/kook/__init__.py:46-48` |
| Mirai | `adapters/mirai/__init__.py:55-57` |
| OneBot 11 | `adapters/onebot/v11/__init__.py:60-62` |
| OneBot 12 | `adapters/onebot/v12/__init__.py:60-62` |
| ComWeChat | `adapters/comwechat/__init__.py:23-25` |

`[事实]` QQ 频道有上限（`:141` `while self.keep_run and self.model.reconnect_limit > 0`），但网关获取失败时递归起任务：

```python
# adapters/tencent/qqGuild/__init__.py:73-77
except Exception as e:
    log.error(...)
    await asyncio.sleep(10)
    asyncio.create_task(self.start(handler))     # :76  ← 无上限自调用
```

**影响** `[推断]`
- 服务端长期不可用时，无限重试**无退避**，10 秒一次的固定节奏可能持续冲击服务端（限流/封禁风险）。
- `:76` 的 `create_task` 递归**不等待、无深度限制**，长期失败会持续新增 task 而不回收，属潜在任务/内存泄漏。
- 重试期间无「已放弃」状态，调用方无法感知永久失败。

**建议** 引入指数退避 + 上限 + 显式失败回调；把 `:76` 改为 `await` 或受控循环。

**本次不改动。**

---

## 🟡 中severity风险分册

`[事实]` 为满足「单文件 ≤300 行」约束，以下两组中severity条目已拆出：

| 分册 | 收录 |
|---|---|
| [risks-packaging.md](risks-packaging.md) | R-4 打包重复落盘 / R-12 隐式依赖 / R-14 playwright 急切导入 / R-17 `test` 适配器暴露面 |
| [risks-api.md](risks-api.md) | R-7 无 `py.typed` / R-9 无弃用与语义化版本 / R-10 CI Python 版本覆盖不足 |
| [risks-low.md](risks-low.md) | 🟢 低severity：R-8 / R-11 / R-13 / R-18 / R-19 / R-21 / R-22 + 「确认不成立的担忧」附录 |

## ✅ R-20 · `verify()` 原地改写 `self.keywords` —— **经复核为有意行为，非缺陷**

**原判定（已撤回）** `[事实]` 本次审计最初把 `amiyabot/factory/implemented.py:86-91` 的 `self.keywords = equal_filter` 判为「跨消息状态污染」。**经项目作者说明与代码复核，该判定错误，已撤回。**

```python
# implemented.py:86-91
if need_check_prefix and not flag and not isinstance(self.keywords, Equal):
    equal_filter = [n for n in self.keywords if isinstance(n, Equal)] if isinstance(self.keywords, list) else []
    if equal_filter:
        self.keywords = equal_filter        # :89  ← 收窄为 Equal 子集，供 :113 消费
    else:
        return result
...
return self.__check(result, data, self.keywords)   # :113  依赖 :89 写入的结果
```

**为何该写入是必要的** `[事实]` 三条：

1. `:113` 的 `self.__check(result, data, self.keywords)` 读取的正是 `:89` 写入的值——**该赋值被下游依赖**，不是副作用。
2. `:84-85` 的注释说明了意图：前缀未通过时，转而校验列表中的 `Equal` 项。若 `:89` 不写回，`:113` 就会拿到未收窄的完整列表，该分支失去意义。
3. `grep -n "self.keywords"` 仅命中 `:86, :87, :89, :113`——除注册时的赋值（`factory/__init__.py:110`）外，**没有任何其他代码读或写它**，故不存在对外的可观察污染。

**附带发现：命中关键字回传契约缺文档** `[事实]` 该写入是「收窄后供 `__check` 消费」，而 `__check` 会把**命中的关键字**写入 `Verify.keypoint`（`check_str`/`check_equal` 返回第 3 元素为关键字，`builtin/message/__init__.py:172,177`；`check_reg` 返回正则分组，`:183-187`；经 `implemented.py:22` → `structure.py:154-162` 赋值），并由 `data.verify`（`handler/messageHandler.py:152`）暴露给用户函数。

`[建议]` 即注册函数可用 `data.verify.keypoint` 取到命中的关键字 —— **但这套语义在仓库中无任何文字记载**（`on_message` docstring 仅称「触发关键字」，`factory/__init__.py:88`；`keypoint` 无仓库内消费方，`grep -rn "keypoint"` 仅命中 `structure.py:141,144,158`）。即：**机制由返回值形状佐证，而非由规范证明**。

**建议** `[建议]` 这不是代码缺陷，而是**文档缺口**。建议在 `on_message` docstring 或官方文档中写明 `data.verify.keypoint` 的语义（命中的关键字；正则时为分组列表），使这套设计可被发现。**本次不改动**（属源代码/上游文档，越界）。完整链路表见 [modules/factory-and-plugins.md](modules/factory-and-plugins.md) §6.1。

---

## 🟢 低severity风险 → 见 [risks-low.md](risks-low.md)

`[事实]` 为避免单文件过长（>300 行约束），以下低 / 低中severity条目已拆到 [risks-low.md](risks-low.md)：

| ID | 风险 |
|---|---|
| R-8 | `BotAdapterProtocol` 非真 ABC，抽象方法不强制 |
| R-13 | 依赖声明漂移（amiyautils 本地 0.0.4 / 线上 0.0.5） |
| R-11 | `setup.py` 构建时**写回** `requirements.txt` |
| R-18 | 硬编码 URL，无代理/自建域名支持 |
| R-19 | `choice_handlers` 深拷贝 × N + 无并列保护 |
| R-21 | `signal.signal` 在 import 时执行（模块级副作用） |
| R-22 | 无 `SIGTERM` 处理，容器场景不优雅关停 |

同文件还包含「确认不成立的担忧」附录（如实修正静态推断）。

---

## 相关文档

- 打包与版本细节 → [packaging-release.md](packaging-release.md)
- 依赖风险 → [dependencies.md](dependencies.md)
- 测试缺口 → [testing-quality.md](testing-quality.md)
- 架构与调用链 → [architecture.md](architecture.md)
- 低severity续篇 → [risks-low.md](risks-low.md)
