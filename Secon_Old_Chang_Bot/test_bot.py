import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime, time, timedelta
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

bot = commands.Bot(command_prefix="!", intents=intents)

# 你的頻道 ID
GAME_CHANNEL_ID = 1369566072541417523  #  ID

# Model
class GameModel:
    def __init__(self):
        self.roll_results = {}
        self.play_count = {}
        self.dice_history = {}
        self.log_path = os.path.join("H:\\我的雲端硬碟\\test", "dice_log.json")

    def save_history_to_file(self):
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.dice_history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"寫入紀錄檔時發生錯誤：{e}")

    def roll_dice(self, user_id):
        roll = random.randint(1, 6)
        self.roll_results[user_id] = roll
        if user_id not in self.dice_history:
            self.dice_history[user_id] = []
        self.dice_history[user_id].append(roll)
        if len(self.dice_history[user_id]) > 5:
            self.dice_history[user_id].pop(0)
        self.save_history_to_file()
        return roll

    def get_dice_message(self, user_id):
        roll = self.roll_results.get(user_id)
        if roll is None:
            return "沒有擲骰紀錄！"
        messages = {
            1: "你擲出了 1！看來運氣不太好呢...",
            2: "你擲出了 2！還不錯，但可以更好哦！",
            3: "你擲出了 3！中規中矩，試試再來一次？",
            4: "你擲出了 4！運氣開始變好了！",
            5: "你擲出了 5！很棒的結果！",
            6: "你擲出了 6！太可怕了，完美！",
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
            await self.view.send_ephemeral(interaction, "你今天已經玩了 3 次遊戲，請明天再試！")
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
        bot.loop.create_task(controller.schedule_daily_reset())
    except discord.Forbidden:
        print(f"錯誤：bot 沒有權限在頻道 {GAME_CHANNEL_ID} 中發送訊息，請檢查權限。")
    except Exception as e:
        print(f"發送訊息時發生錯誤：{e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def synccommands(ctx):
    await bot.tree.sync()
    await ctx.send("老張同步中")

@bot.hybrid_command()
async def ping(ctx):
    await ctx.send(f"{round(bot.latency * 1000)} ms")

@bot.hybrid_command(name="檢查老張")
async def check_bot(ctx):
    await ctx.send("老張還活著")

bot.run(TOKEN)
