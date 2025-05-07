import discord
from discord.ext import commands
import json

# 從 JSON 讀取 TOKEN
with open('setting.json', 'r') as f:
    config = json.load(f)
TOKEN = config['DISCORD_TOKEN']

# 設定 intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('>>老張復活啦!!!<<')

@bot.command()
@commands.has_permissions(administrator=True)
async def synccommands(ctx):
    await bot.tree.sync()
    await ctx.send('老張同步中')

@bot.hybrid_command()
async def ping(ctx):
    await ctx.send(f'{round(bot.latency * 1000)} ms')

@bot.hybrid_command(name="檢查老張")
async def check_bot(ctx):
    await ctx.send('老張還活著')

# @bot.event
# async def on_member_join(member):
#     print(f'{member} join!')
#     channel = bot.get_channel(1369562169380966470)
#     await channel.send(f'{member} join!')

# @bot.event
# async def on_member_remove(member):
#     print(f'{member} leave!')

bot.run(TOKEN)
