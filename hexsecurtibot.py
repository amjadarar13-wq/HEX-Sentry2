import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread

# ---------- 1. إنشاء سيرفر ويب مصغر للبقاء نادهاً (Keep Alive) ----------
app = Flask('')

@app.route('/')
def home():
    return "HEX Security Bot is Online!"

def run_web_server():
    # تشغيل سيرفر الويب على المنفذ المناسب لـ Render
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

WHITELIST_ROLE_ID = None  # ID الرتبة المسموح لها بالتعديل
LOG_CHANNEL_ID = None      # ID قناة السجلات

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول بنجاح باسم: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 تم مزامنة {len(synced)} من أوامر السلاش.")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء مزامنة الأوامر: {e}")

# ---------- مساعدة: التحقق والحظر ----------
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

# ---------- أحداث الحماية (Events) ----------

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
            await check_and_punish(after.guild, entry.user, f"التعديل على القناة/صلاحياتها: {after.name}")
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

# ---------- أوامر السلاش (Slash Commands) ----------

@bot.tree.command(name="set_role", description="تحديد الرتبة المسموح لها بالتعديل فقط")
@app_commands.checks.has_permissions(administrator=True)
async def set_role(interaction: discord.Interaction, role: discord.Role):
    global WHITELIST_ROLE_ID
    WHITELIST_ROLE_ID = role.id
    await interaction.response.send_message(f"✅ تمت الإفادة وتحديد الرتبة المسموحة: {role.mention}", ephemeral=True)

@bot.tree.command(name="set_log", description="تحديد قناة السجلات (Logs) فقط")
@app_commands.checks.has_permissions(administrator=True)
async def set_log(interaction: discord.Interaction, log_channel: discord.TextChannel):
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = log_channel.id
    await interaction.response.send_message(f"✅ تمت الإفادة وتحديد قناة السجلات: {log_channel.mention}", ephemeral=True)

@bot.tree.command(name="remove_role", description="إلغاء وإزالة رتبة الحماية الحالية")
@app_commands.checks.has_permissions(administrator=True)
async def remove_role(interaction: discord.Interaction):
    global WHITELIST_ROLE_ID
    if WHITELIST_ROLE_ID:
        WHITELIST_ROLE_ID = None
        await interaction.response.send_message("🗑️ تم إلغاء رتبة الحماية بنجاح.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ لا توجد رتبة حماية مفعلة أساساً.", ephemeral=True)

@bot.tree.command(name="protection_status", description="عرض حالة نظام الحماية الحالي")
@app_commands.checks.has_permissions(administrator=True)
async def protection_status(interaction: discord.Interaction):
    role_mention = f"<@&{WHITELIST_ROLE_ID}>" if WHITELIST_ROLE_ID else "غير محددة"
    log_mention = f"<#{LOG_CHANNEL_ID}>" if LOG_CHANNEL_ID else "غير محددة"

    embed = discord.Embed(title="🛡️ حالة نظام الحماية", color=discord.Color.blue())
    embed.add_field(name="الرتبة المحمية", value=role_mention, inline=False)
    embed.add_field(name="قناة السجلات", value=log_mention, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------- 3. التشغيل النهائي ----------
keep_alive()  # تشغيل السيرفر الخفيف لإبقائه مستيقظاً عبر UptimeRobot

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("⚠️ تحذير: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة!")