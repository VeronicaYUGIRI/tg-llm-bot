# TG LLM Bot

一个 Telegram 群聊机器人,通过 [OpenRouter](https://openrouter.ai) 调用 LLM(默认模型 `anthropic/claude-opus-4.7`),让群里的人可以像在 ChatGPT 群组功能里一样跟 AI 对话。

## 功能

- bot 加入群后能看到所有人的消息(需要在 BotFather 里关闭隐私模式,见下文)
- 默默记录大家聊的内容,**不会自动回复**,只有发送 `/ask` 时才会综合目前积累的聊天记录回复一次
- 每次 bot 回复后面会附一行用量信息:这次用的模型、消耗的 token 数、这次花费、累计花费
- 用 SQLite(`usage.db`)记录每次调用的明细(时间、用户、模型、token 数、花费)
- 累计花费等数据库记录会随 Railway 部署/重启而清空(未配置持久化存储),如不在意可忽略

## 命令列表

| 命令 | 作用 |
|---|---|
| `/ask` | 综合目前缓存的聊天记录,触发一次 AI 回复。也可以 `/ask 一句话` 把这句话也加入后再回复 |
| `/usage` | 查看本群累计调用次数、token 数、花费 |
| `/reset` | 清空本群当前缓存的聊天记录(不影响数据库里的历史流水) |
| `/settings` | 查看本群当前模型、历史消息上限、当前缓存数量、累计用量 |
| `/setmodel <模型ID>` | 修改本群使用的模型,例如 `/setmodel anthropic/claude-opus-4.7` |
| `/setwindow <数字>` | 修改本群缓存的历史消息条数上限,例如 `/setwindow 20` |

## 本地运行

### 1. 安装依赖

```
pip install -r requirements.txt
```

### 2. 配置密钥

复制 `.env.example` 为 `.env`,填入真实的 token / API key:

```
TELEGRAM_BOT_TOKEN=你的telegram bot token
OPENROUTER_API_KEY=你的openrouter api key
OPENROUTER_MODEL=anthropic/claude-opus-4.7
HISTORY_WINDOW_SIZE=20
```

`.env` 文件包含密钥,已加入 `.gitignore`,不会被提交到 GitHub,请不要手动把它传上去。

### 3. 启动

```
python bot.py
```

## 如何获取 Telegram bot token

1. 在 Telegram 中搜索并打开 `@BotFather`(官方认证账号)
2. 发送 `/start`,然后发送 `/newbot`
3. 按提示输入显示名字(任意)和用户名(必须以 `bot` 结尾,且全 Telegram 唯一)
4. 创建成功后,BotFather 会返回一行 `数字:字母数字` 格式的字符串,这就是 token,填入 `.env` 的 `TELEGRAM_BOT_TOKEN`

### 关闭隐私模式(让 bot 能看到群里所有消息)

1. 在 BotFather 里发送 `/setprivacy`
2. 选择你的 bot
3. 选择 `Disable`

如果 bot 已经在群里了,需要先移出群再重新加一次,这个设置才会生效。

## 如何获取 OpenRouter API key

1. 登录 [openrouter.ai](https://openrouter.ai)
2. 右上角头像菜单 → Keys(或直接访问 openrouter.ai/keys)
3. 复制 API key,填入 `.env` 的 `OPENROUTER_API_KEY`
4. 可在 [openrouter.ai/models](https://openrouter.ai/models) 搜索确认想用的模型 ID,填入 `OPENROUTER_MODEL`

## 部署到 Railway

1. 把本仓库推送到 GitHub(私有仓库)
2. 登录 [railway.app](https://railway.app),New Project → Deploy from GitHub repo,选择这个仓库
3. 在 Railway 项目的 Variables 标签页,添加以下环境变量(内容跟本地 `.env` 一致):
   - `TELEGRAM_BOT_TOKEN`
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`
   - `HISTORY_WINDOW_SIZE`
4. Railway 会根据 `Procfile` 自动以 worker 方式启动 `python bot.py`
5. 部署成功后,bot 会一直在线监听群消息,本地终端的 `python bot.py` 就可以关掉了

## 文件说明

- `bot.py` — 主程序,处理 Telegram 消息和命令
- `llm.py` — 封装对 OpenRouter API 的调用
- `db.py` — SQLite 数据库操作(用量记录、群设置)
- `requirements.txt` — Python 依赖列表
- `Procfile` / `runtime.txt` — Railway 部署配置
- `.env.example` — 环境变量模板(不含真实密钥)
