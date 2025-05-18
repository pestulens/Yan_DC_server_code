import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import asyncio
from datetime import datetime, time
import os

# 從 JSON 讀取 TOKEN
base_dir = os.path.dirname(os.path.abspath(__file__))
setting_path = os.path.join(base_dir, 'setting.json')

with open(setting_path, 'r', encoding='utf-8') as f:
    setting = json.load(f)
TOKEN = setting["DISCORD_TOKEN"]

# 設定 intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # 啟用成員意圖

bot = commands.Bot(command_prefix="!", intents=intents)

# 頻道和伺服器 ID
GAME_CHANNEL_ID = 1369566072541417523
GUILD_ID = discord.Object(1369566072541417523)

# Model（模型）：負責遊戲數據和邏輯
class GameModel:
    def __init__(self):
        self.roll_results = {}  # 儲存用戶的擲骰結果
        self.play_count = {}  # 儲存每個玩家的每日遊戲次數，格式: {user_id: {"count": int, "date": date}}

    def roll_dice(self, user_id):
        roll = random.randint(1, 6)
        self.roll_results[user_id] = roll
        return roll

    def get_dice_message(self, user_id):
        roll = self.roll_results.get(user_id)
        if roll is None:
            return "沒有擲骰記錄！"
        messages = {
            1: "你擲出了 1！看來運氣不太好呢...",
            2: "你擲出了 2！還不錯，但可以更好哦！",
            3: "你擲出了 3！中規中矩，試試再來一次？",
            4: "你擲出了 4！運氣開始變好了！",
            5: "你擲出了 5！很棒的結果！",
            6: "你擲出了 6！太厲害了，完美！",
        }
        return messages.get(roll, "骰子結果出錯了！")

    def clear_data(self, user_id):
        if user_id in self.roll_results:
            del self.roll_results[user_id]

    def get_play_count(self, user_id):
        today = datetime.now().date()
        if user_id not in self.play_count or self.play_count[user_id]["date"] != today:
            self.play_count[user_id] = {"count": 0, "date": today}
        return self.play_count[user_id]["count"]

    def increment_play_count(self, user_id):
        today = datetime.now().date()
        if user_id not in self.play_count or self.play_count[user_id]["date"] != today:
            self.play_count[user_id] = {"count": 0, "date": today}
        self.play_count[user_id]["count"] += 1
        return self.play_count[user_id]["count"]

    def reset_play_count(self):
        today = datetime.now().date()
        for user_id in list(self.play_count.keys()):
            if self.play_count[user_id]["date"] != today:
                del self.play_count[user_id]

# View（視圖）：負責顯示骰子遊戲狀態
class GameView(discord.ui.View):
    def __init__(self, controller):
        super().__init__(timeout=None)
        self.controller = controller

    @discord.ui.button(label="確認", style=discord.ButtonStyle.primary, custom_id="confirm_button")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.show_confirmation(interaction)

    async def send_message(self, channel, message):
        return await channel.send(message, view=self)

    async def send_ephemeral(self, interaction, message, view=None):
        if view:
            return await interaction.response.send_message(message, ephemeral=True, view=view)
        return await interaction.response.send_message(message, ephemeral=True)

    async def delete_message(self, message):
        if message:
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass

# 確認視圖：包含「是」和「否」按鈕
class ConfirmView(discord.ui.View):
    def __init__(self, controller):
        super().__init__(timeout=60)
        self.controller = controller

    @discord.ui.button(label="是", style=discord.ButtonStyle.green, custom_id="confirm_yes")
    async def confirm_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.start_game(interaction)

    @discord.ui.button(label="否", style=discord.ButtonStyle.red, custom_id="confirm_no")
    async def confirm_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.cancel_game(interaction)

# Index 視圖：來自第二份程式碼的主選單
class Index(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="去工作", style=discord.ButtonStyle.primary, custom_id='1')
    async def button_work(self, button, interaction):
        await interaction.response.send_message(view=Work(), ephemeral=True)

    @discord.ui.button(label="個人狀態", style=discord.ButtonStyle.primary, custom_id='2')
    async def button_state(self, button, interaction):
        await interaction.response.send_message("state", ephemeral=True)

    @discord.ui.button(label="請安", style=discord.ButtonStyle.primary, custom_id='3')
    async def button_morning(self, button, interaction):
        await interaction.response.send_message("早奄", ephemeral=True)

# Work 視圖：來自第二份程式碼的工作選單
class Work(discord.ui.View):
    @discord.ui.button(label="校場", style=discord.ButtonStyle.primary, row=0)
    async def button_field(self, button, interaction):
        await interaction.response.send_message(view=FieldEvent(), ephemeral=True)

    @discord.ui.button(label="太學", style=discord.ButtonStyle.primary, row=0)
    async def button_college(self, button, interaction):
        await interaction.response.send_message("太學", ephemeral=True)

    @discord.ui.button(label="科學院", style=discord.ButtonStyle.primary, row=0)
    async def button_sciences(self, button, interaction):
        await interaction.response.send_message("科學院", ephemeral=True)

    @discord.ui.button(label="樂府", style=discord.ButtonStyle.primary, row=0)
    async def button_balladss(self, button, interaction):
        await interaction.response.send_message("樂府", ephemeral=True)

    @discord.ui.button(label="兵營", style=discord.ButtonStyle.success, row=1)
    async def button_military(self, button, interaction):
        await interaction.response.send_message("兵營", ephemeral=True)

    @discord.ui.button(label="市集", style=discord.ButtonStyle.success, row=1)
    async defАвтоматически переведено з китайської (традиційної) на українську:
button_market(self, button, interaction):
    await interaction.response.send_message("市集", ephemeral=True)

@discord.ui.button(label="匠人坊", style=discord.ButtonStyle.success, row=1)
async def button_workshop(self, button, interaction):
    await interaction.response.send_message("匠人坊", ephemeral=True)

@discord.ui.button(label="茶館", style=discord.ButtonStyle.success, row=1)
async def button_teahouse(self, button, interaction):
    await interaction.response.send_message("茶館", ephemeral=True)

@discord.ui.button(label="兵工廠", style=discord.ButtonStyle.danger, row=2)
async def button_arsenal(self, button, interaction):
    await interaction.response.send_message("兵工廠", ephemeral=True)

@discord.ui.button(label="接待所", style=discord.ButtonStyle.danger, row=2)
async def button_reception(self, button, interaction):
    await interaction.response.send_message("接待所", ephemeral=True)

@discord.ui.button(label="加工所", style=discord.ButtonStyle.danger, row=2)
async def button_factory(self, button, interaction):
    await interaction.response.send_message("加工所", ephemeral=True)

@discord.ui.button(label="博物院", style=discord.ButtonStyle.danger, row=2)
async def button_museum(self, button, interaction):
    await interaction.response.send_message("博物院", ephemeral=True)

@discord.ui.button(label="海港", style=discord.ButtonStyle.secondary, row=3)
async def button_dock(self, button, interaction):
    number = random.randint(1, 16)
    switch = {
        1: "拜師學藝\n你探訪一處幽僻深山",
        2: "野營受寒\n你探訪一處幽僻深山",
        3: "遭遇搶劫\n你探訪一處幽僻深山",
        4: "討價還價\n你探訪一處幽僻深山",
        5: "海關扣留\n你探訪一處幽僻深山",
        6: "粗心大意\n你探訪一處幽僻深山",
        7: "小鎮導覽\n你探訪一處幽僻深山",
        8: "火災警報\n你探訪一處幽僻深山",
        9: "山林修練\n你探訪一處幽僻深山",
        10: "觀摩商店街\n你探訪一處幽僻深山",
        11: "輪船遊歷\n你探訪一處幽僻深山",
        12: "料理祕方\n你探訪一處幽僻深山",
        13: "先發制人\n你探訪一處幽僻深山",
        14: "先發制人\n你探訪一處幽僻深山",
        15: "先發制人\n你探訪一處幽僻深山",
        16: "先發制人\n你探訪一處幽僻深山",
    }
    dock_description = switch[number]
    dockclose = discord.Embed(title="[海港特殊事件-結算]", description=dock_description)
    await interaction.response.send_message(embed=dockclose, ephemeral=True)

# FieldEvent 視圖：來自第二份程式碼的校場事件
class FieldEvent(discord.ui.View):
    @discord.ui.button(label="選項一", style=discord.ButtonStyle.primary)
    async def choose_one(self, button, interaction):
        dockclose = discord.Embed(title="[校場特殊事件-結算]", description="拜師學藝")
        await interaction.response.send_message(embed=dockclose, ephemeral=True)

    @discord.ui.button(label="選項二", style=discord.ButtonStyle.primary)
    async def choose_two(self, button, interaction):
        dockclose = discord.Embed(title="[校場特殊事件-結算]", description="拜師學藝")
        await interaction.response.send_message(embed=dockclose, ephemeral=True)

# Controller（控制器）：處理用戶輸入，協調 Model 和 View
class GameController:
    def __init__(self, model, view, channel):
        self.model = model
        self.view = view
        self.channel = channel
        self.initial_message = None
        self.confirm_message = None
        self.result_message = None

    async def show_initial_message(self):
        self.initial_message = await self.view.send_message(
            self.channel, "歡迎體驗老張的骰子遊戲！點擊下方按鈕開始吧！"
        )

    async def show_confirmation(self, interaction):
        self.confirm_message = await self.view.send_ephemeral(
            interaction, "你確定要執行遊戲嗎？", view=ConfirmView(self)
        )

    async def start_game(self, interaction):
        user_id = interaction.user.id
        play_count = self.model.get_play_count(user_id)
        if play_count >= 3:
            await self.view.send_ephemeral(
                interaction, "你今天已經玩了 3 次遊戲，請明天再試！"
            )
            return
        roll = self.model.roll_dice(user_id)
        self.model.increment_play_count(user_id)
        message = self.model.get_dice_message(user_id)
        self.result_message = await self.view.send_ephemeral(interaction, message)
        asyncio.create_task(self.clear_messages_after_delay(user_id, 120))
        await self.reset_game(user_id)

    async def cancel_game(self, interaction):
        user_id = interaction.user.id
        self.result_message = await self.view.send_ephemeral(interaction, "遊戲已取消。")
        asyncio.create_task(self.clear_messages_after_delay(user_id, 120))
        await self.reset_game(user_id)

    async def clear_messages_after_delay(self, user_id, delay):
        await asyncio.sleep(delay)
        await self.view.delete_message(self.confirm_message)
        await self.view.delete_message(self.result_message)
        self.confirm_message = None
        self.result_message = None

    async def reset_game(self, user_id):
        self.model.clear_data(user_id)
        await self.view.delete_message(self.initial_message)
        await self.show_initial_message()

    async def schedule_daily_reset(self):
        while True:
            now = datetime.now()
            next_reset = datetime.combine(now.date(), time(21, 0))
            if now.time() > time(21, 0):
                next_reset += timedelta(days=1)
            wait_seconds = (next_reset - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            self.model.reset_play_count()
            print(f"已於 {next_reset} 重置所有玩家的遊戲次數。")

# 初始化 MVC 組件
view = None
controller = None

@bot.event
async def on_ready():
    global view, controller
    print(">>老張復活啦!!!<<")
    model = GameModel()
    channel = bot.get_channel(GAME_CHANNEL_ID)
    if channel is None:
        print(f"錯誤：無法找到 ID 為 {GAME_CHANNEL_ID} 的頻道，請檢查頻道 ID 或 bot 權限。")
        return
    view = GameView(None)
    controller = GameController(model, view, channel)
    view.controller = controller
    try:
        await controller.show_initial_message()
        bot.add_view(view)
        bot.add_view(Index())  # 添加 Index 視圖
        bot.loop.create_task(controller.schedule_daily_reset())
    except discord.Forbidden:
        print(f"錯誤：bot 沒有權限在頻道 {GAME_CHANNEL_ID} 中發送訊息，請檢查權限。")
    except Exception as e:
        print(f"發送訊息時發生錯誤：{e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def synccommands(ctx):
    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        await ctx.send(f"老張同步完成！已同步 {len(synced)} 個命令。")
    except Exception as e:
        await ctx.send(f"同步失敗：{e}")

@bot.hybrid_command()
async def ping(ctx):
    await ctx.send(f"{round(bot.latency * 1000)} ms")

@bot.hybrid_command(name="檢查老張")
async def check_bot(ctx):
    await ctx.send("老張還活著")

@bot.tree.command(name="summon", description="召喚 Chang Jr", guild=GUILD_ID)
async def summonCJ(interaction: discord.Interaction):
    await interaction.response.send_message(view=Index(), ephemeral=True)

bot.run(TOKEN)