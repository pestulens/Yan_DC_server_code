import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime, time

# 從 JSON 讀取 TOKEN
with open('setting.json', 'r') as f:
    config = json.load(f)
TOKEN = config['DISCORD_TOKEN']

# 設定 intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 替換為你的頻道 ID
GAME_CHANNEL_ID = 1369566072541417523  # 請替換為實際頻道 ID

# Model（模型）：負責遊戲數據和邏輯
class GameModel:
    def __init__(self):
        self.roll_results = {}  # 儲存用戶的擲骰結果
        self.play_count = {}    # 儲存每個玩家的每日遊戲次數，格式: {user_id: {"count": int, "date": date}}

    def roll_dice(self, user_id):
        # 模擬擲骰子，生成 1-6 的數字
        roll = random.randint(1, 6)
        self.roll_results[user_id] = roll
        return roll

    def get_dice_message(self, user_id):
        # 根據骰子結果返回不同文本
        roll = self.roll_results.get(user_id)
        if roll is None:
            return "沒有擲骰記錄！"
        messages = {
            1: "你擲出了 1！看來運氣不太好呢...",
            2: "你擲出了 2！還不錯，但可以更好哦！",
            3: "你擲出了 3！中規中矩，試試再來一次？",
            4: "你擲出了 4！運氣開始變好了！",
            5: "你擲出了 5！很棒的結果！",
            6: "你擲出了 6！太厲害了，完美！"
        }
        return messages.get(roll, "骰子結果出錯了！")

    def clear_data(self, user_id):
        # 清除用戶的擲骰數據
        if user_id in self.roll_results:
            del self.roll_results[user_id]

    def get_play_count(self, user_id):
        # 獲取玩家的每日遊戲次數
        today = datetime.now().date()
        if user_id not in self.play_count or self.play_count[user_id]["date"] != today:
            self.play_count[user_id] = {"count": 0, "date": today}
        return self.play_count[user_id]["count"]

    def increment_play_count(self, user_id):
        # 增加玩家的遊戲次數
        today = datetime.now().date()
        if user_id not in self.play_count or self.play_count[user_id]["date"] != today:
            self.play_count[user_id] = {"count": 0, "date": today}
        self.play_count[user_id]["count"] += 1
        return self.play_count[user_id]["count"]

    def reset_play_count(self):
        # 重置所有玩家的遊戲次數
        today = datetime.now().date()
        for user_id in list(self.play_count.keys()):
            if self.play_count[user_id]["date"] != today:
                del self.play_count[user_id]

# View（視圖）：負責顯示遊戲狀態
class GameView(discord.ui.View):
    def __init__(self, controller):
        super().__init__(timeout=None)
        self.controller = controller

    @discord.ui.button(label="確認", style=discord.ButtonStyle.primary, custom_id="confirm_button")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.show_confirmation(interaction)

    async def send_message(self, channel, message):
        # 發送訊息並返回訊息對象
        return await channel.send(message, view=self)

    async def send_ephemeral(self, interaction, message, view=None):
        # 如果有 view 則傳遞，否則不傳遞
        if view:
            return await interaction.response.send_message(message, ephemeral=True, view=view)
        return await interaction.response.send_message(message, ephemeral=True)

    async def delete_message(self, message):
        # 刪除指定訊息
        if message:
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass  # 訊息可能已過期或無法刪除，忽略

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

# Controller（控制器）：處理用戶輸入，協調 Model 和 View
class GameController:
    def __init__(self, model, view, channel):
        self.model = model
        self.view = view
        self.channel = channel
        self.initial_message = None  # 儲存初始訊息以便刪除
        self.confirm_message = None  # 儲存確認訊息
        self.result_message = None  # 儲存遊戲結果訊息

    async def show_initial_message(self):
        self.initial_message = await self.view.send_message(self.channel, "歡迎體驗老張的骰子遊戲！點擊下方按鈕開始吧！")

    async def show_confirmation(self, interaction):
        self.confirm_message = await self.view.send_ephemeral(interaction, "你確定要執行遊戲嗎？", view=ConfirmView(self))

    async def start_game(self, interaction):
        user_id = interaction.user.id
        play_count = self.model.get_play_count(user_id)
        if play_count >= 3:
            await self.view.send_ephemeral(interaction, "你今天已經玩了 3 次遊戲，請明天再試！")
            return
        roll = self.model.roll_dice(user_id)
        self.model.increment_play_count(user_id)
        message = self.model.get_dice_message(user_id)
        self.result_message = await self.view.send_ephemeral(interaction, message)
        # 2 分鐘後清除訊息
        asyncio.create_task(self.clear_messages_after_delay(user_id, 120))
        # 遊戲結束後清除數據並重置
        await self.reset_game(user_id)

    async def cancel_game(self, interaction):
        user_id = interaction.user.id
        self.result_message = await self.view.send_ephemeral(interaction, "遊戲已取消。")
        # 2 分鐘後清除訊息
        asyncio.create_task(self.clear_messages_after_delay(user_id, 120))
        # 取消後也清除數據並重置
        await self.reset_game(user_id)

    async def clear_messages_after_delay(self, user_id, delay):
        await asyncio.sleep(delay)  # 等待 120 秒（2 分鐘）
        await self.view.delete_message(self.confirm_message)
        await self.view.delete_message(self.result_message)
        self.confirm_message = None
        self.result_message = None

    async def reset_game(self, user_id):
        # 清除數據
        self.model.clear_data(user_id)
        # 刪除初始訊息
        await self.view.delete_message(self.initial_message)
        # 重新發送初始訊息
        await self.show_initial_message()

# 初始化 MVC 組件（移到 on_ready 中）
view = None
controller = None

@bot.event
async def on_ready():
    global view, controller
    print('>>老張復活啦!!!<<')
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
        # 啟動每日重置任務
        bot.loop.create_task(controller.schedule_daily_reset())
    except discord.Forbidden:
        print(f"錯誤：bot 沒有權限在頻道 {GAME_CHANNEL_ID} 中發送訊息，請檢查權限。")
    except Exception as e:
        print(f"發送訊息時發生錯誤：{e}")

# 每日重置方法
async def schedule_daily_reset(self):
    while True:
        now = datetime.now()
        next_reset = datetime.combine(now.date(), time(21, 0))  # 21:00 (晚上 9 點)
        if now.time() > time(21, 0):
            next_reset += timedelta(days=1)  # 如果已經超過 21:00，則重置到明天
        wait_seconds = (next_reset - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        self.model.reset_play_count()
        print(f"已於 {next_reset} 重置所有玩家的遊戲次數。")

# 將 schedule_daily_reset 綁定到 GameController
GameController.schedule_daily_reset = schedule_daily_reset

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

bot.run(TOKEN)