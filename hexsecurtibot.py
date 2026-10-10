import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from flask import Flask, render_template_string, request, redirect, url_for
from threading import Thread

# ---------- 1. إعداد سيرفر الويب ولوحة التحكم (Flask) ----------
app = Flask(__name__)

# متغيرات الحالة العامة (تتحدث من البوت أو من الموقع)
BOT_STATUS = {
    "whitelist_role": "غير محددة",
    "log_channel": "غير محددة",
    "status": "متصل وحماية نشطة 🛡️"
}

# قالب صفحة الويب الداخلية (HTML & CSS)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HEX Security - لوحة التحكم</title>
    <style>
        body {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: Tahoma, sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            background-color: #1e293b;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 450px;
        }
        h2 { text-align: center; color: #38bdf8; margin-bottom: 20px; }
        .info-box {
            background: #0f172a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-right: 4px solid #38bdf8;
        }
        .info-box p { margin: 8px 0; font-size: 14px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; font-size: 14px; }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            background: #0f172a;
            border: 1px solid #475569;
            border-radius: 6px;
            color: white;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 11px;
            background-color: #0284c7;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background-color: #0369a1; }
        .footer { text-align: center; margin-top: 15px; font-size: 12px; color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🛡️ لوحة تحكم HEX Security</h2>
        
        <div class="info-box">
            <p><strong>حالة البوت:</strong> {{ status.status }}</p>
            <p><strong>الرتبة المحمية حالياً:</strong> {{ status.whitelist_role }}</p>
            <p><strong>قناة السجلات حالياً:</strong> {{ status.log_channel }}</p>
        </div>

        <form method="POST">
            <label for="role_id">تحديد ID الرتبة المسموحة:</label>
            <input type="text" id="role_id" name="role_id" placeholder="مثال: 123456789012345678">

            <label for="log_id">تحديد ID قناة السجلات (Logs):</label>
            <input type="text" id="log_id" name="log_id" placeholder="مثال: 123456789012345678">

            <button type="submit">حفظ وتحديث الإعدادات</button>
        </form>

        <div class="footer">HEX Community © 2026</div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    global WHITELIST_ROLE_ID, LOG_CHANNEL_ID
    if request.method == 'POST':
        r_id = request.form.get('role_id')
        l_id = request.form.get('log_id')
        
        if r_id and r_id.isdigit():
            WHITELIST_ROLE_ID = int(r_id)
            BOT_STATUS["whitelist_role"] = f"ID: {WHITELIST_ROLE_ID}"
            
        if l_id and l_id.isdigit():
            LOG_CHANNEL_ID = int(l_id)
            BOT_STATUS["log_channel"] = f"ID: {LOG_CHANNEL_ID}"
            
        return redirect(url_for('home'))
        
    return render_template_string(HTML_TEMPLATE, status=BOT_STATUS)

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ---------- 2. إعدادات بوت الديسكورد ----------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

WHITELIST_ROLE_ID = None
LOG_CHANNEL_ID = None

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول بنجاح باسم: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 تم مزامنة {len(synced)} من أوامر السلاش.")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء مزامنة الأوامر: {e}")

# ---------- التحقق والحظر ----------
async def check_and_punish(guild: discord.Guild, user: discord.Member, action_name: str):
    if user is None or user.bot or user == guild.owner:
        return

    has_role = False
    if WHITELIST_ROLE_ID:
        has_role = any(role.id == WHITELIST_ROLE_ID for role in user.roles)

    if not has_role:
        try:
            await guild.ban(user, reason=f"نظام الحماية: إحداث تغيير غير مصرح به ({action_name})")
            
            if LOG_CHANNEL_ID:
                log_channel = guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 تم اكتشاف مخالفة وحظر العضو!",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="العضو المخالف", value=f"{user.mention} (`{user.id}`)", inline=False)
                    embed.add_field(name="الإجراء المحظور", value=action_name, inline=False)
                    embed.set_footer(text="نظام الحماية التلقائي - HEX")
                    await log_channel.send(embed=embed)
        except Exception as e:
            print(f"❌ حدث خطأ أثناء الحظر: {e}")

# ---------- الأحداث (Events) ----------
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    await asyncio.sleep(0.5)
    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
        await check_and_punish(channel.guild, entry.user, f"إنشاء قناة: {channel.name}")
        break

@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    await asyncio.sleep(0.5)
    async for entry in after.guild.audit_logs(limit=1):
        if entry.action in [discord.AuditLogAction.channel_update, discord.AuditLogAction.overwrite_create, discord.AuditLogAction.overwrite_update, discord.AuditLogAction.overwrite_delete]:
            await check_and_punish(after.guild, entry.user, f"التعديل على القناة: {after.name}")
            break

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    await asyncio.sleep(0.5)
    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
        await check_and_punish(channel.guild, entry.user, f"حذف قناة: {channel.name}")
        break

@bot.event
async def on_guild_role_create(role: discord.Role):
    await asyncio.sleep(0.5)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
        await check_and_punish(role.guild, entry.user, f"إنشاء رتبة: {role.name}")
        break

@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    await asyncio.sleep(0.5)
    async for entry in after.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
        await check_and_punish(after.guild, entry.user, f"التعديل على رتبة: {after.name}")
        break

@bot.event
async def on_guild_role_delete(role: discord.Role):
    await asyncio.sleep(0.5)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
        await check_and_punish(role.guild, entry.user, f"حذف رتبة: {role.name}")
        break

# ---------- 3. التشغيل النهائي ----------
keep_alive()  # تشغيل سيرفر الويب ولوحة التحكم

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("⚠️ تحذير: لم يتم العثور على DISCORD_TOKEN")