# TG LLM Bot

一个 Telegram 群聊机器人,通过 [OpenRouter](https://openrouter.ai) 调用 LLM(模型可配置),让群里的人可以像在 ChatGPT 群组功能里一样跟 AI 对话。bot 默默记录群里的聊天内容,只有发送 `/ask` 时才会综合目前的聊天记录回复一次。

## 如果你想拥有自己独立的 bot

这份代码**不包含任何密钥**,仓库里看到的只是程序逻辑。如果你想用这份代码搭一个属于你自己的 bot(而不是连到别人已经在跑的那个):

1. 点击 GitHub 页面右上角的 **Fork**,把仓库复制一份到你自己的账号下(或者直接 `git clone` 到本地也行)
2. 去 BotFather **创建一个全新的 bot**,拿到属于你自己的 token(见下文"获取 Telegram bot token")
3. 去 OpenRouter **注册/使用你自己的账号**,拿到你自己的 API key
4. 用你自己的 token 和 key 填写 `.env`(本地)或云端平台的环境变量

只要 token 是你自己的,这就是一个完全独立的 bot,不会跟原作者或其他 fork 的人共享对话历史、共享额度,互不影响。**绝对不要把自己的 token/API key 提交到 GitHub**(`.gitignore` 已经帮你排除了 `.env`,但还是要小心)。

## 准备工作

在开始部署之前,你需要先拿到两个东西:

- **Telegram bot token**:去 [@BotFather](https://t.me/BotFather) 创建一个 bot 拿到,见下文详细步骤
- **OpenRouter API key**:去 [openrouter.ai](https://openrouter.ai) 注册并创建 key,见下文详细步骤

### 获取 Telegram bot token

1. 在 Telegram 中搜索并打开 `@BotFather`(官方认证账号)
2. 发送 `/start`,然后发送 `/newbot`
3. 按提示输入显示名字(任意)和用户名(必须以 `bot` 结尾,且全 Telegram 唯一)
4. 创建成功后,BotFather 会返回一行 `数字:字母数字` 格式的字符串,这就是 token
5. 发送 `/setprivacy`,选择你的 bot,选择 `Disable`——这一步是为了让 bot 能看到群里**所有人**的消息,而不是只有 @它 或回复它的消息。如果 bot 已经被加进群了,需要先移出群再重新加一次才会生效

### 获取 OpenRouter API key

1. 登录 [openrouter.ai](https://openrouter.ai)
2. 右上角头像菜单 → Keys(或直接访问 openrouter.ai/keys)
3. 创建并复制一个 API key
4. 可在 [openrouter.ai/models](https://openrouter.ai/models) 搜索确认想用的模型 ID(比如 `anthropic/claude-opus-4.7`、`deepseek/deepseek-v4-flash`)

## 选择部署方式:本地 vs 云端

| | 本地运行 | 云端部署(Railway / Fly.io) |
|---|---|---|
| 费用 | 完全免费 | 有免费额度,可能需要绑卡验证身份 |
| 前提条件 | 你的电脑必须一直开机、联网,bot 才会一直在线 | 不依赖你的设备,24 小时在线 |
| 适合场景 | 先测试功能、临时使用 | 长期稳定使用,不想一直开着电脑 |
| 操作难度 | 简单,装好依赖直接跑 | 需要注册账号、命令行操作或网页配置 |

两种方式可以共存(开发时先本地测,确认没问题再部署云端),但**不能同时让两份用同一个 bot token 的程序运行**——Telegram 同一个 token 只允许一个地方在监听消息,否则会报错冲突。

## 本地运行

### 1. 安装依赖

```
pip install -r requirements.txt
```

### 2. 配置密钥

复制 `.env.example` 为 `.env`,填入你自己的 token / API key:

```
TELEGRAM_BOT_TOKEN=你的telegram bot token
OPENROUTER_API_KEY=你的openrouter api key
OPENROUTER_MODEL=anthropic/claude-opus-4.7
HISTORY_WINDOW_SIZE=20
ALLOWED_CHAT_IDS=
```

`.env` 文件包含密钥,已加入 `.gitignore`,不会被提交到 GitHub,请不要手动把它传上去。

### 3. 启动

```
python bot.py
```

## 部署到 Railway

1. 把仓库推送到你自己的 GitHub(私有或公开都可以)
2. 登录 [railway.app](https://railway.app),New Project → Deploy from GitHub repo,选择这个仓库
3. 在 Railway 项目的 Variables 标签页,添加以下环境变量(内容跟本地 `.env` 一致,但两边是独立的,各自维护):
   - `TELEGRAM_BOT_TOKEN`
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`
   - `HISTORY_WINDOW_SIZE`
   - `ALLOWED_CHAT_IDS`(强烈建议设置,见下文"限制只允许特定群使用")
4. Railway 会根据 `Procfile` 自动以 worker 方式启动 `python bot.py`
5. 部署成功后,bot 会一直在线监听群消息,本地终端的 `python bot.py` 就可以关掉了
6. 每次修改环境变量或推送新代码触发 redeploy,程序都会重启(内存中未处理的聊天记录会丢失,但 `/setmodel`/`/setwindow` 设置和累计花费通常会保留,除非数据库文件本身被重置)
7. Railway 免费额度是"30 天或 $5,先到先得",到期或额度用完后需要绑卡升级才能继续在线;小流量的私人群聊通常不会很快用完额度

## 部署到 Fly.io

Fly.io 免费额度比 Railway 更长期(不是 30 天试用),但需要装一个命令行工具自己操作,适合不介意用一下命令行的人。**不要同时把 Railway 和 Fly.io 都跑起来**——同一个 Telegram bot token 只能被一个地方监听,两边同时跑会互相冲突报错(`Conflict: terminated by other getUpdates request`)。

1. 注册 [fly.io](https://fly.io) 账号(可能需要信用卡验证身份,免费额度内不会被扣费;新账号有时会被标记为"高风险",需要去 fly.io/high-risk-unlock 走一下验证)
2. 在本地安装 `flyctl` 命令行工具:
   ```
   powershell -c "irm https://fly.io/install.ps1 | iex"
   ```
3. 登录:
   ```
   flyctl auth login
   ```
4. 项目里需要 `Dockerfile`(已包含在本仓库)和 `.dockerignore`(确保 `.env`、`usage.db` 不会被打包进镜像)
5. 初始化项目配置(`--no-deploy` 表示先生成配置,不立即部署):
   ```
   flyctl launch --no-deploy --name 你的应用名 --region nrt --yes
   ```
6. 检查生成的 `fly.toml`:**必须删除默认生成的 `[http_service]` 区块**,因为这个 bot 不是网站、不监听端口,保留这个区块可能导致 Fly.io 在"没有访问流量"时把机器关掉。改成类似:
   ```
   [build]

   [[vm]]
     memory = '256mb'
     cpu_kind = 'shared'
     cpus = 1
   ```
7. 把 `.env` 内容导入成 Fly.io 的 secrets:
   ```
   flyctl secrets import < .env
   ```
8. 部署:
   ```
   flyctl deploy
   ```
9. **重要**:部署后用 `flyctl status` 检查机器数量,确保**只有 1 台**在跑。Fly.io 默认可能会创建一台"备用机"(standby),对这种内存里存状态的单实例程序是有害的(两台机器各自维护一份聊天记录,会导致历史记录看起来"丢失"或不一致)。如果看到 2 台,执行:
   ```
   flyctl scale count 1 --yes
   ```
10. 用 `flyctl logs --no-tail` 查看日志,确认没有 `Conflict` 报错,且 `getUpdates` 持续返回 `200 OK`
11. Fly.io 机器崩溃会自动重启,平时不需要手动管理

## 部署好之后:怎么把 bot 用起来

### 把 bot 加进群

确认前面 BotFather 的隐私模式已经 `Disable`,把 bot 加入你和朋友的群即可。

### 限制只允许特定群使用(防止被外人白嫖)

Telegram 没有"设为私有 bot"的开关,任何人知道 bot 用户名都能把它加进自己的群,消耗你的 OpenRouter 额度。为此加入了白名单机制:

1. 把 bot 加入你自己的群,发送 `/chatid`,记下返回的数字(可能是负数,这是正常的,群聊的 chat_id 通常是负数)
2. 在 `.env`(本地)/ 云端平台的环境变量里设置 `ALLOWED_CHAT_IDS=那个数字`,多个群用逗号分隔,例如 `ALLOWED_CHAT_IDS=-1001234567890,-1009876543210`
3. 设置后,只有白名单里的群,bot 才会记录消息、响应任何命令;其他群里 bot 会完全没反应(不回复、不计费、不记录)
4. 如果 `ALLOWED_CHAT_IDS` 留空,则不限制,bot 会在任何加入的群里生效(不推荐长期这样)

### 命令列表

| 命令 | 作用 |
|---|---|
| `/ask` | 综合目前缓存的聊天记录,触发一次 AI 回复。也可以 `/ask 一句话` 把这句话也加入后再回复 |
| `/usage` | 查看本群累计调用次数、token 数、花费 |
| `/reset` | 清空本群当前缓存的聊天记录(不影响数据库里的历史流水) |
| `/settings` | 查看本群当前模型、历史消息上限、当前缓存数量、累计用量 |
| `/setmodel <模型ID>` | 修改本群使用的模型,例如 `/setmodel anthropic/claude-opus-4.7` |
| `/setwindow <数字>` | 修改本群缓存的历史消息条数上限,例如 `/setwindow 20` |
| `/chatid` | 查看当前群的 chat_id(不受白名单限制,任何群都能用,用来配置 `ALLOWED_CHAT_IDS`) |
| `/dumphistory` | 调试用,原样打印当前内存里缓存的历史记录列表(序号从 1 开始) |

每次 bot 回复后面会附一段斜体用量信息,格式类似:
```
🤖 deepseek/deepseek-v4-flash
本次消耗 74 tokens,花费 $0.0014
累计 1234 tokens,累计花费 $0.0234
```

### 默认值 vs 运行时设置

`.env`(本地)/ 云端平台环境变量里的 `OPENROUTER_MODEL`、`HISTORY_WINDOW_SIZE` 只是**初始默认值**。一旦在群里用过 `/setmodel` 或 `/setwindow`,实际生效的设置会存进 `usage.db`,优先级高于环境变量,且不受程序重启影响(除非数据库文件本身被清空)。改环境变量,只是改"万一数据库里没有设置时,回退用哪个默认值",不会覆盖已经设置好的值。本地和各个云端平台上的环境变量是各自独立的,互不同步,需要分别修改。

### 关于 usage.db

- 用 SQLite(`usage.db`)记录每次调用的明细(时间、用户、模型、token 数、花费)
- 它是二进制文件,不能直接用文本编辑器打开,需要用 [DB Browser for SQLite](https://sqlitebrowser.org/) 之类的工具,或 VSCode 的 SQLite Viewer 插件查看
- 本地重启 `python bot.py` **不会**清空它,数据会一直累积。只有云端平台重新部署时,因为没配置持久化存储卷,容器会是全新的,它才会被清空(不影响本地的数据库文件)

## 文件说明

- `bot.py` — 主程序,处理 Telegram 消息和命令
- `llm.py` — 封装对 OpenRouter API 的调用
- `db.py` — SQLite 数据库操作(用量记录、群设置)
- `requirements.txt` — Python 依赖列表
- `Procfile` / `runtime.txt` — Railway 部署配置
- `Dockerfile` / `.dockerignore` / `fly.toml` — Fly.io 部署配置
- `.env.example` — 环境变量模板(不含真实密钥)
