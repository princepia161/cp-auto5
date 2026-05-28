# 🎓 Classplus Auto Uploader Bot

Natking-Auto-Uploader की तरह काम करता है — लेकिन **Appx की जगह Classplus** platform का।

Automatically downloads and uploads Classplus course content (videos, PDFs, YouTube links) to Telegram groups with daily scheduling and smart duplicate prevention.

---

## ✨ Features

- 📹 **Video Auto-Upload** — Classplus videos download & upload to Telegram
- 📄 **PDF Documents** — Auto-download and send PDFs
- 🎥 **YouTube Links** — Send with Watch button
- ⏰ **Daily Auto-Schedule** — Set HH:MM time for daily updates (IST)
- 🔄 **Smart Duplicate Prevention** — Never re-uploads same content
- 📂 **Forum Topic Organization** — Topic-wise organization in supergroups
- 🔑 **Two Login Methods** — Token or OTP (ORGCODE*Mobile)
- 💾 **MongoDB Storage** — Persistent batch & upload tracking
- 🔄 **Crash Recovery** — Resumes incomplete uploads on restart

---

## 🚀 Setup

### Prerequisites
- Python 3.11+
- MongoDB database (free at mongodb.com/atlas)
- Telegram Bot Token (from @BotFather)
- Telegram API ID & Hash (from my.telegram.org)
- ffmpeg & aria2c installed (included in Dockerfile)

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
BOT_TOKEN=your_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
ADMIN_ID=your_telegram_user_id
DB_URL=mongodb+srv://...
DB_NAME=classplus_bot
LOG_CHANNEL=-100XXXXXXXXXX
USERLINK=https://t.me/YourChannel
TUTORIAL_VIDEO=https://t.me/YourChannel
```

### 2. Deploy

**Docker (Recommended):**
```bash
docker build -t cp-bot .
docker run --env-file .env cp-bot
```

**Render.com:**
- Connect this repo
- Set environment variables from render.yaml
- Deploy!

**Heroku:**
```bash
heroku create your-app-name
heroku config:set BOT_TOKEN=... API_ID=... # (set all vars)
git push heroku main
```

---

## 📱 Usage

### Bot Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help |
| `/id` | Get chat ID |
| `/addbatch` | Add a new batch |
| `/restart` | Restart bot (admin only) |
| `/legal` | Legal disclaimer |

### Adding a Batch

1. Click **"➕ Add Batch"** or use `/addbatch`
2. Choose login method:
   - **Token Login**: Paste your Classplus access token directly
   - **OTP Login**: Send `ORGCODE*MobileNumber` (e.g. `ABCD*9876543210`)
3. Select batch from the list
4. Enter target Telegram group ID
5. Set update schedule (HH:MM IST) or `no`
6. Set credit/caption text
7. Set filename prefix (optional)
8. Set thumbnail URL (optional)
9. Confirm — upload starts automatically!

### Getting Classplus Token
- Open Classplus app → capture network request headers
- Look for `x-access-token` header value
- Token format: long JWT string starting with `ey...`

---

## 📁 Project Structure

```
classplus-auto-uploader/
├── config.py              # Configuration (env vars)
├── main.py                # Bot entry point + Flask server
├── logger.py              # Logging setup
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker container
├── render.yaml            # Render.com deployment
├── .env.example           # Environment variable template
│
├── constant/
│   ├── msg.py             # All message strings
│   └── buttom.py          # Keyboard button layouts
│
├── master/
│   ├── database.py        # MongoDB operations (Motor async)
│   ├── helper.py          # Download/upload/thumbnail helpers
│   ├── server.py          # Async HTTP client (httpx)
│   ├── logdb.py           # Log channel dedup helper
│   └── utils.py           # Misc utilities
│
├── modules/
│   ├── cp_master.py       # Classplus login + batch add flow
│   ├── cpdata.py          # Classplus API — fetch all content
│   ├── tasks.py           # Download + upload pipeline
│   ├── manager.py         # Telegram group/topic management
│   ├── scheduler.py       # Daily IST scheduler
│   └── retasks.py         # Crash recovery on restart
│
└── plugins/
    ├── command.py          # /start /help /id /restart /addbatch
    └── callbacks.py        # Inline button handlers
```

---

## 🔧 Classplus API Used

| Endpoint | Purpose |
|----------|---------|
| `GET /v2/orgs/{orgCode}` | Get org details for OTP login |
| `POST /v2/otp/generate` | Send OTP to mobile |
| `POST /v2/users/verify` | Verify OTP, get token |
| `GET /v2/batches/details` | List all batches |
| `GET /v2/course/content/get?courseId={id}` | Get batch folders |
| `GET /v2/course/content/get?courseId={id}&folderId={id}` | Get folder content |
| `GET /cams/uploader/video/jw-signed-url?url={url}` | Get signed video URL |

---

## ⚠️ Important Notes

- Bot must be **admin** in the target group
- For forum topics, the group must have **Topics enabled**
- `LOG_CHANNEL` stores all uploaded files for dedup — bot must be admin there
- All times are **IST (Asia/Kolkata)**
- Requires **ffmpeg** for thumbnails and **aria2c** for fast downloads

---

## 📄 License

MIT License — Educational use only.
