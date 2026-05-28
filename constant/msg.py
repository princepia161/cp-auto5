START = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  🎓 CLASSPLUS AUTO UPLOADER
╰━━━━━━━━━━━━━━━━━━╯</b>

👋 Hello {}, Welcome!

I am a powerful bot that automatically manages and uploads course content from <b>Classplus</b> platform to your Telegram groups.

📌 <b>What I Can Do:</b>
• 📹 Auto-download & upload videos
• 📄 Upload PDF documents
• 🎥 Send YouTube links with thumbnails
• ⏰ Schedule daily auto-updates
• 🔄 Smart duplicate prevention
• 📊 Forum topic-wise organization

🔗 <b>Support:</b> {}
"""

HELP = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  📚 HOW TO USE
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>Bot Commands:</b>

• /start — Start the bot
• /help — Show this message
• /id — Get chat ID
• /restart — Restart if stuck
• /legal — Legal disclaimer

<b>Batch Management (Inline Buttons):</b>
• ➕ Add Batch — Add a new Classplus batch
• 📊 My Batches — View all your batches
• ⚙️ Manage Batch — View batch details
• 🗑️ Delete Batch — Remove a batch

<b>Adding a Batch:</b>
1. Click "Add Batch"
2. Login with Classplus token or OTP
3. Select your batch
4. Choose target Telegram group
5. Set schedule time (HH:MM)
6. Done! Auto-upload starts

🔗 {}
"""

DISCLAIMER = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ⚖️ LEGAL DISCLAIMER
╰━━━━━━━━━━━━━━━━━━╯</b>

<i>Please read this disclaimer carefully before using this bot.

This bot is designed for educational purposes only. The developers are not responsible for any misuse of this bot. By using this bot, you agree that:

1. You will use it only for personal learning purposes.
2. You will not distribute or sell any content obtained through this bot.
3. You acknowledge that content piracy is illegal.
4. The bot developers hold no liability for user actions.

⚠️ Use at your own risk.</i>
"""

APP = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  🔑 CLASSPLUS LOGIN
╰━━━━━━━━━━━━━━━━━━╯</b>

Choose your login method:

<b>Option 1 — Token Login</b>
Paste your Classplus access token directly.

<b>Option 2 — OTP Login</b>
Login with <code>ORGCODE*Mobile</code>
Example: <code>ABCD*9876543210</code>
"""

LOGIN_PROMPT_TOKEN = """
<b>📱 CLASSPLUS TOKEN LOGIN</b>

Send your Classplus <b>access token</b>:

<i>How to get token: Open Classplus app → Settings → Get token from app logs or intercepted requests.</i>
"""

LOGIN_PROMPT_OTP = """
<b>📱 CLASSPLUS OTP LOGIN</b>

Send your details in this format:
<code>ORGCODE*MobileNumber</code>

Example:
<code>ABCD*9876543210</code>

<i>ORGCODE is the organization/institute code on Classplus.</i>
"""

OTP_SENT = """
<b>📲 OTP Sent!</b>

OTP has been sent to your registered mobile number.
Please enter the <b>6-digit OTP</b>:
"""

LOGIN_SUCCESS = """
<b>✅ Login Successful!</b>

Welcome to Classplus Auto Uploader.

Your token has been saved securely.
Now let's set up your batch! ⬇️
"""

LOGIN_FAILED = """
<b>❌ Login Failed!</b>

Please check your credentials and try again.
Error: {}
"""

BATCH_LIST = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  📚 YOUR BATCHES
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>Select the Batch ID you want to add:</b>
(Enter the batch ID number from the list)

{}
"""

BATCH_SELECTION = "<b>Please enter the Batch ID from the list above that you want to set for auto-upload ⬆️</b>"

BATCH_ALREADY_EXISTS = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ❌ BATCH EXISTS
╰━━━━━━━━━━━━━━━━━━╯</b>

This batch is already in my database!
Use <b>Manage Batch</b> to view its details.
"""

BATCH_DELETED = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  🗑️ BATCH DELETED
╰━━━━━━━━━━━━━━━━━━╯</b>

Batch deleted successfully from database!
All associated data has been removed.
"""

BATCH_NOT_FOUND = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ❌ NOT FOUND
╰━━━━━━━━━━━━━━━━━━╯</b>

Batch not found in my database.
"""

BATCH_STATUS = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  📊 BATCH STATUS
╰━━━━━━━━━━━━━━━━━━╯</b>

🆔 <b>ID:</b> {}
📝 <b>Name:</b> {}
📊 <b>Status:</b> {}
📄 <b>PDFs Uploaded:</b> {}
🎥 <b>Videos Uploaded:</b> {}
⏰ <b>Schedule:</b> {} IST daily

<b>╰━━━━━━━━━━━━━━━━━━╯</b>
"""

BATCH_UPDATED = "✅ Batch Updated Successfully!"

GROUP_SETUP = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  👥 GROUP SETUP
╰━━━━━━━━━━━━━━━━━━╯</b>

Send the <b>Group ID</b> where I should upload content.

<i>How to get Group ID:
• Add me to your group
• Send /id in that group
• Copy the negative number (e.g. -1001234567890)</i>
"""

GROUP_ERROR = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ❌ GROUP ERROR
╰━━━━━━━━━━━━━━━━━━╯</b>

Invalid group or insufficient permissions!

Please verify:
1. Group ID is correct
2. Bot is an admin in the group
3. Bot has message & media permissions
"""

TIME_SETUP = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ⏰ SCHEDULE TIME
╰━━━━━━━━━━━━━━━━━━╯</b>

Enter the time for daily auto-update in <b>HH:MM</b> format (IST):

Examples:
• <code>08:00</code> — 8 AM
• <code>14:30</code> — 2:30 PM
• <code>22:00</code> — 10 PM

Or send <code>no</code> to skip scheduling (manual only).
"""

CREDIT_OPTIONS = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  💬 CREDIT/CAPTION
╰━━━━━━━━━━━━━━━━━━╯</b>

Enter a credit/caption to add to each upload:

Examples:
• <code>@YourChannel</code>
• <code>Admin | @YourChannel</code>
• Send <code>no</code> for no credit
"""

FILENAME_OPTIONS = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  📝 FILENAME PREFIX
╰━━━━━━━━━━━━━━━━━━╯</b>

Enter a prefix to add to file names:

Example: <code>Physics Class</code>
Or send <code>no</code> to skip.
"""

THUMB_OPTIONS = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  🖼️ THUMBNAIL
╰━━━━━━━━━━━━━━━━━━╯</b>

Send a <b>thumbnail image URL</b> for videos:

Example: <code>https://telegra.ph/file/abc.jpg</code>
Or send <code>no</code> to use auto-generated thumbnails.
"""

CONFIRM_CONFIG = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  📋 CONFIRMATION
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>📚 Batch Name:</b> {}
<b>🆔 Batch ID:</b> {}
<b>👥 Group ID:</b> {}
<b>⏰ Schedule:</b> {} IST
<b>💬 Credit:</b> {}

<b>Start processing this batch?</b>
"""

COLLECTING_DATA = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  🔄 COLLECTING DATA
╰━━━━━━━━━━━━━━━━━━╯</b>

Fetching course content from Classplus...
Please wait, this may take a few minutes depending on batch size.
"""

DAILY_UPDATE_COMPLETED = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ✅ DAILY UPDATE DONE
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>🆔 Batch ID:</b> {}
<b>📝 Batch Name:</b> {}
<b>📄 New PDFs:</b> {}
<b>🎥 New Videos:</b> {}

Daily check complete!
"""

NO_NEW_CLASSES = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ℹ️ NO NEW CONTENT
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>📝 Batch:</b> {}

No new classes found today. All content is up to date!
"""

RECOVERING_BATCH = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  🔄 RECOVERING BATCH
╰━━━━━━━━━━━━━━━━━━╯</b>

Resuming incomplete upload for: <b>{}</b>

Please wait...
"""

ERROR_UPLOADING = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ⚠️ UPLOAD FAILED
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>📝 Name:</b> <code>{}</code>
<b>🔗 URL:</b> <code>{}</code>
<b>❌ Error:</b> <code>{}</code>
"""

VIDEO_CAPTION_V2 = """<b>📹 {}</b>

📚 <b>Course:</b> {}
📂 <b>Topic:</b> {}
📅 <b>Date:</b> {}
💬 {}"""

PDF_CAPTION_V2 = """<b>📄 {}</b>

📚 <b>Course:</b> {}
📂 <b>Topic:</b> {}
📅 <b>Date:</b> {}
💬 {}"""

YT_VIDEO_CAPTION = """<b>🎥 YouTube Video</b>"""

GENERAL_ERROR = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  ⚠️ ERROR
╰━━━━━━━━━━━━━━━━━━╯</b>

Something went wrong. Please try again later.
"""

OTP_VERIFIED = """
<b>✅ OTP Verified!</b>

Login successful. 
"""

MODE_SELECTION = """
<b>╭━━━━━━━━━━━━━━━━━━╮
┃  📋 SELECT MODE
╰━━━━━━━━━━━━━━━━━━╯</b>

<b>📚 Batch:</b> {batch_name}

Choose what you want to do:

<b>📄 Get .txt File</b>
Get all video/PDF links as a downloadable text file instantly — no upload needed!

<b>📤 Upload to Telegram Group</b>
Download & upload all content directly to your Telegram group with scheduling support.
"""
