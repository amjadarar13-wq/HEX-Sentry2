import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread

# ---------- 1. سيرفر البقاء (Keep-Alive) لتشغيل 24/7 ----------
app = Flask('')

@app.route('/')
def home():
    return "HEX Security Bot is Online and Running 24/7! 🛡️"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ---------- 2. إعدادات بوت الديسكورد الأساسية ----------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# متغيرات الرتب والقنوات (يمكنك تعديلها لاحقاً أو برمجتها بأوامر سلاش)
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

# ---------- نظام التحقق والحماية ----------
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

# ---------- مراقبة الأحداث (Events) ----------
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    await asyncio.sleep(0.5)
    async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
        await check_and_punish(channel.guild, entry.user, f"إنشاء قناة: {channel.name}")
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
async def on_guild_role_delete(role: discord.Role):
    await asyncio.sleep(0.5)
    async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
        await check_and_punish(role.guild, entry.user, f"حذف رتبة: {role.name}")
        break

# ---------- 3. التشغيل النهائي ----------
keep_alive()  # تشغيل السيرفر الخفيف لإبقائه مستيقظاً عبر UptimeRobot

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("⚠️ تحذير: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة!")