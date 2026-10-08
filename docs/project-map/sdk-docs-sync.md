# SDK 文档同步映射（sdk-docs-sync）

> 本文件回答一个问题：**改了 `amiyabot/` 里的代码，该同步哪份 SDK 用户文档？**
> 证据约定：`[事实]` / `[推断]` / `[建议]`。路径均相对本仓库根目录。

## 1. 这是什么

`[事实]` `docs/Amiya-Bot-docs/` 是本仓库的 **git 子模块**（`.gitmodules`），指向独立仓库 `git@github.com:AmiyaBot/Amiya-Bot-docs.git`。

| 项 | 值 |
|---|---|
| 用途 | **面向用户的 SDK 文档**（插件开发者 / 使用者） |
| 技术栈 | VitePress（`package.json:11-13`） |
| 本地预览 | `cd docs/Amiya-Bot-docs && npm install && npm run docs:dev`（端口 8080） |
| 构建 | `npm run docs:build` |
| 内容根 | `docs/Amiya-Bot-docs/docs/` |
| 发布分支 | 远端有 `gh-pages`（`[事实]` `git ls-remote` 含 `refs/heads/gh-pages`） |
| 许可 | 代码 MIT；文档 CC BY-NC-SA 4.0（`docs/Amiya-Bot-docs/README.md`） |

`[事实]` **与 `docs/project-map/` 的区别**：project-map 是维护者/AI 用的项目地图（架构、风险、打包），**不对外**；SDK 文档是用户教程。二者内容不应互相复制——**用户教程一律进 SDK 文档**。

## 2. ⚠️ 子模块操作要点

`[事实]` 子模块是**独立仓库**，在子目录内的改动**不会**随本仓库 `git add` 一起提交。

```bash
# 首次克隆本仓库后，子模块目录是空的，需初始化
git submodule update --init --recursive

# 更新子模块到远端最新
cd docs/Amiya-Bot-docs && git pull origin master

# 提交顺序（重要）
cd docs/Amiya-Bot-docs && git add -A && git commit -m "docs: ..." && git push
cd ../.. && git add docs/Amiya-Bot-docs && git commit -m "chore: 更新 SDK 文档子模块指针"
```

`[建议]` 先提交子模块、再提交指针，可避免别人 clone 后拿到「指向不存在 commit」的指针。

`[事实]` 当前锁定的 commit 见 `git submodule status`（写入时为 `6b2d2be`，`heads/master`）。

## 3. 代码 → 文档映射表

`[事实]` 以下映射由「代码中的公开 API」与「文档章节标题/示例导入路径」比对得出。

### 3.1 `builtin/messageChain/`（`Chain` DSL）

| 代码 | 文档 |
|---|---|
| `Chain` 构造与 `.text()` | `basic/chainBuild/text.md` |
| `.at()` / `.at_all()` | `basic/chainBuild/at.md` / `basic/chainBuild/atAll.md` |
| `.image()` | `basic/chainBuild/image.md` |
| `.voice()` | `basic/chainBuild/voice.md` |
| `.video()` | `basic/chainBuild/video.md` |
| `.face()` | `basic/chainBuild/face.md` |
| `.tag()` | `basic/chainBuild/tag.md` |
| `.html()` | `basic/chainBuild/html.md` |
| `.markdown()` | `basic/chainBuild/markdown.md` |
| `.markdown_template()` | `basic/chainBuild/mdTemplate.md` |
| `.embed()` | `basic/chainBuild/embed.md` |
| `.ark()` | `basic/chainBuild/ark.md` |
| `.extend()` | `basic/chainBuild/extend.md` |
| `.text_image()` | `basic/chainBuild/textImage.md` |
| 合并转发（Mirai/CQHttp） | `basic/chainBuild/forward.md` |
| `ChainBuilder` 子类化 | `advanced/chainBuilder.md` |
| `InlineKeyboard` | `basic/chainBuild/mdTemplate.md` |

### 3.2 `factory/` + `handler/`（注册与生命周期）

| 代码 | 文档 |
|---|---|
| `@bot.on_message()` | `basic/messageHandler.md` |
| `@bot.on_event()` | `basic/handleEvents.md` |
| `@bot.on_exception()` | `basic/handleException.md` |
| 7 个生命周期钩子 | `advanced/lifeCycle.md` |
| `GroupConfig` / `set_group_config` | `basic/messageHandler.md` |
| `set_prefix_keywords` | `basic/index.md` |
| `PluginInstance` 及插件生命周期 | `plugin/amiyaBotPluginInstance.md`、`plugin/life.md` |
| `BotInstance.load_plugin` | `advanced/loadPlugins.md`、`plugin/create.md` |

### 3.3 `builtin/message/`（消息与等待事件）

| 代码 | 文档 |
|---|---|
| `Message` 字段（`text`/`user_id`/`is_direct`…） | `basic/recvMessage.md` |
| `Message.send()` | `basic/sendMessage.md` |
| `Message.recall()` | `basic/recallMessage.md` |
| `Message.wait()` / `wait_channel()` | `basic/continuityMessage.md` |
| `Event` / `EventList` | `basic/handleEvents.md` |
| 主动消息（`send_message`） | `basic/sendActiveMessage.md` |
| `MultipleAccounts` | `basic/multipleAccounts.md` |

### 3.4 `adapters/`

| 代码 | 文档 |
|---|---|
| `QQGuildBotInstance` | `adapters/qqChannel.md` |
| `qq_guild_shards` | `adapters/qqChannel.md` |
| `QQGroupBotInstance` | `adapters/qqGroup.md` |
| `QQGlobalBotInstance` | `adapters/qqGlobal.md` |
| `KOOKBotInstance` | `adapters/kook.md` |
| `MiraiBotInstance` / `mirai_api_http` | `adapters/mah.md` |
| `CQHttpBotInstance` / `cq_http` | `adapters/gocq.md` |
| `OneBot11Instance` / `onebot11` | `adapters/onebot11.md` |
| `OneBot12Instance` / `onebot12` | `adapters/onebot12.md` |
| `ComWeChatBotInstance` / `com_wechat` | `adapters/comwechat.md` |
| `TestInstance` / `test_instance` | `basic/testInstance.md` |
| 新增适配器（契约） | `adapters/index.md` |

### 3.5 `builtin/lib/` + `database/` + `network/`

| 代码 | 文档 |
|---|---|
| `event_bus` | `advanced/eventBus.md` |
| `@bot.timed_task` / `TasksControl` | `advanced/timedTask.md` |
| `basic_browser_service` / `BrowserLaunchConfig` | `advanced/playwright.md` |
| `ChainConfig.max_length` 等启动参数 | `advanced/startupParameter.md` |
| `database`（`connect_database`/`@table`） | `tools/databaseSupport.md` |
| `network.download` 等 | `tools/httpRequests.md`、`tools/httpSupport.md`、`old/httpSupport.md` |
| 日志 | `advanced/logger.md` |
| 阻塞 IO 说明 | `advanced/blockingIO.md` |

### 3.6 面向部署（一般**不需要**随代码改）

`[事实]` `docs/guide/deploy/**` 是安装部署文档（docker/exe/mysql/各平台实例接入），只在**部署方式或依赖变化**时更新，常规 API 改动不涉及。

## 4. 同步规则

| 场景 | 是否同步 SDK 文档 |
|---|---|
| 新增公开 API（类/函数/装饰器参数） | ✅ **必须** |
| 修改公开 API 签名或行为 | ✅ **必须** |
| 破坏性变更（移除类、改默认值） | ✅ **必须**，且需在文档标注**迁移方式** |
| 新增适配器 | ✅ **必须**（`adapters/` 加一页 + `index.md`） |
| 纯内部重构（不改签名与外部行为） | ❌ 不必 |
| 修 bug 但不改变文档描述的行为 | ❌ 不必（除非文档描述本身有误） |
| 打包/CI/依赖变更 | ⚠️ 视情况（部署文档在 `guide/deploy/`） |

`[建议]` 判断捷径：**「用户按文档写的代码，改完之后还能跑吗？」** 不能 → 必须同步。

## 5. 本项目已发生的实例（对照参考）

`[事实]` 已删除 `TencentBotInstance` / `TencentSandboxBotInstance`（`adapters/tencent/__init__.py`）。

`[事实]` **本次无需同步 SDK 文档**：`grep -rn "TencentBotInstance|TencentSandbox" docs/Amiya-Bot-docs/` **无任何命中**——文档从未提及这两个旧名，且 `adapters/qqChannel.md` 已使用新路径 `amiyabot.adapters.tencent.qqGuild`。

`[推断]` 这是一次「**代码有破坏性变更、但文档恰好无需改**」的情况，属于例外：因为该弃用类从未进入用户文档。**不要**因此认为「删除公开类不用改文档」——本次只是恰好没被记录。

## 6. 相关文档

- 公共 API 全貌 → [public-api.md](public-api.md)
- 模块分册 → [modules/](README.md#模块分册)
- 两套文档分工 → [AGENTS.md](../../AGENTS.md)
