import discord
from discord.commands import slash_command
from discord.ext import commands, tasks
import utils.logger as logger
from utils.db import database
from utils.config import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import json
import random
from datetime import datetime, timedelta
from itertools import cycle

with open("config.json", "r") as f:
    config = json.load(f)
    token = config["token"]

ACTIVITIES = ["테스트"]

activity = cycle(ACTIVITIES)
intents = discord.Intents.default()

db = database()
boot_time = datetime.now()

class Vote_Bot(discord.AutoShardedBot):
    def __init__(self):
        logger.log("--# 로딩을 시작할게요!")
        super().__init__(
            help_command=None,
            intents=intents,
            debug_guilds=None,
        )
        self.load_extension("cogs.voter")
        self.load_extension("cogs.candidate")
        self.load_extension("cogs.election")
        self.add_cog(CommandsCog(self))
        self.add_cog(CycleCog(self))
    
    async def on_ready(self):
        logger.log("--# 로딩이 완료되었어요!")
        logger.log(f"봇 이름: {self.user.name}")
        logger.log(f"봇 아이디: {self.user.id}")
        logger.log(f"봇 서버 수: {len(self.guilds)}")
        await self.change_presence(status=discord.Status.online)

"""
    CommandsCog: 기본 기능 관련 Cog

    - on_message: 봇이 멘션되었을 때 반응하는 이벤트 리스너 (핑 반환)
    - on_command_error: 명령어 실행 중 오류가 발생했을 때 처리하는 이벤트 리스너
"""
class CommandsCog(commands.Cog):
    def __init__(self, bot: discord.AutoShardedBot):
        self.bot = bot
        logger.log("CommandsCog 로딩 성공!")

    @slash_command(name="정보", description="작동중인 봇의 정보를 확인합니다.")
    async def info(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="봇 정보", color=discord.Color.blue())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="봇 이름", value=self.bot.user.name, inline=True)
        embed.add_field(name="봇 아이디", value=self.bot.user.id, inline=True)
        embed.add_field(name="서버 수", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="핑", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        description = "```markdown\n" \
                      "- /정보: 봇 정보를 확인할 수 있습니다.\n" \
                      "\n## 선거인 관련 명령어\n" \
                      "- /선거인 정보: 선거인 등록 정보를 확인할 수 있습니다.\n" \
                      "- /선거인 등록: 선거인으로 등록할 수 있습니다. (선거인 등록 기간 내에만 사용 가능)\n" \
                      "- /선거인 취소: 선거인 등록을 취소합니다. (선거인 등록 기간 내에만 사용 가능)\n" \
                      "\n## 후보자 관련 명령어\n" \
                      "- /후보자 정보: 후보자 등록 정보를 확인할 수 있습니다.\n" \
                      "- /후보자 등록: 후보자로 등록할 수 있습니다. (후보자 등록 기간 내에만 사용 가능)\n" \
                      "- /후보자 사퇴: 후보자 등록을 취소합니다. (후보자 등록 기간 내에만 사용 가능)\n" \
                      "- /후보자 설정: 후보자 정보를 관리할 수 있습니다. (별명, 공약)\n" \
                      "\n## 선거 관련 명령어\n" \
                      "- /선거정보: 현재 진행 중인 선거 정보를 확인할 수 있습니다.\n" \
                      "- /후보: 현재 등록된 후보자 정보를 확인할 수 있습니다.\n" \
                      "- /보안문자: 보안 문자열을 발급받을 수 있습니다.\n" \
                      "- /투표: 현재 진행 중인 선거에 투표할 수 있습니다. (투표 기간 내에만 사용 가능)\n" \
                      "```"
        embed.add_field(name="명령어 목록", value=description, inline=False)
        embed.set_footer(text=f"봇 시작 시간: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}, 서버 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.content.startswith(f"<@{self.bot.user.id}>"):
            logger.mention_log(msg)
            a = ""
            try:
                a = msg.content.split()[1]
            except IndexError:
                pass

            if a == "":
                response = f"ping: {round(self.bot.latency * 1000)}ms"
                return await msg.channel.send(response)
            if msg.author.id == 523981270611525633:
                if a == "번호부여":
                    logger.log("후보자 번호 부여되었습니다.")
                    # DB의 candidate 테이블에서 모든 후보자의 ID를 가져와서 번호를 부여
                    db.execute("SELECT id FROM candidates")
                    candidates = db.fetchall()
                    if candidates == []:
                        return await msg.channel.send("후보자가 없습니다.")
                    random.shuffle(candidates)
                    for i, candidate in enumerate(candidates, start=1):
                        db.execute("UPDATE candidates SET number = ? WHERE id = ?", (i, candidate[0]))
                    embed = discord.Embed(title="후보자 번호 부여 완료", description="모든 후보자에게 번호가 부여되었습니다.", color=discord.Color.green())
                    return await msg.reply(embed=embed)
            
    @commands.Cog.listener()
    async def on_command_error(self, ctx: discord.ApplicationContext, error):
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(title="명령어를 찾을 수 없습니다.", description="올바른 명령어를 입력해 주세요.", color=discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            if ctx.guild is None:
                logger.error_log(f"/{ctx.command} by {ctx.author.name}({ctx.author.id}) at DM\n{error}")
            else:
                logger.error_log(f"/{ctx.command} by {ctx.author.name}({ctx.author.id}) at {ctx.channel.name}({ctx.channel.id}) in {ctx.guild.name}({ctx.guild.id})\n{error}")
            embed = discord.Embed(title="오류 발생", description="명령어 실행 중 오류가 발생했습니다.", color=discord.Color.red())
            embed.add_field(name="Error", value=f"```{str(error)}```", inline=False)
            await ctx.respond(embed=embed, ephemeral=True)

"""
    CycleCog: 스케쥴러
"""
class CycleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_activity.start()
        logger.log("CycleCog 로딩 성공!")

    @commands.Cog.listener()
    async def on_ready(self):
        self.sched = AsyncIOScheduler()

        # 매 정각마다 turnout 함수 실행
        self.sched.add_job(self.turnout, 'cron', minute=0, hour='*')
        self.sched.start()
        logger.log("AsyncIOScheduler 시작됨")

    @tasks.loop(seconds=30)
    async def change_activity(self):
        playing = next(activity).format(len(self.bot.guilds))
        await self.bot.change_presence(activity=discord.Game(name=playing))

    async def turnout(self):
        now = datetime.now()
        if now > electionmain["end"] + timedelta(hours=1):
            return
        db.execute("SELECT COUNT(*) FROM secure WHERE voted = 1")
        voted_count = db.fetchall()[0][0]
        db.execute("SELECT COUNT(*) FROM voters")
        total_count = db.fetchall()[0][0]
        if total_count == 0:
            turnout_percentage = 0.0
        else:
            turnout_percentage = (voted_count / total_count) * 100
        db.execute("INSERT INTO turnout (percentage, voted_count, total_count, timestamp) VALUES (?, ?, ?, ?)", (turnout_percentage, voted_count, total_count, now))
        logger.log(f"Turnout recorded: {turnout_percentage:.2f}%")

try:
    votebot = Vote_Bot()
    votebot.run(token=token)
finally:
    logger.log("--# 봇이 종료되었어요!")