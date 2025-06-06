import asyncio
from datetime import datetime
import discord
from discord.ext import commands
import utils.logger as logger
from utils.db import database
from utils.config import *

db = database()

"""
    VoterCog: 선거인 관련 명령어를 처리하는 Cog

    - voter_info: 선거인 등록 정보를 확인하는 명령어 (/선거인 정보)
    - voter_register: 선거인으로 등록하는 명령어 (/선거인 등록)
    - voter_cancel: 선거인 등록을 취소하는 명령어 (/선거인 취소)
"""
class VoterCog(commands.Cog):
    voter_group = discord.SlashCommandGroup("선거인", "선거인 관련 명령어입니다.")

    def __init__(self, bot: discord.AutoShardedBot):
        self.bot = bot
        logger.log("VoterCog 로딩 성공!")

    @voter_group.command(name="정보", description="선거인 등록 정보를 확인합니다.")
    async def voter_info(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        is_voter = False
        can_signup = False

        # DM 체크
        if ctx.guild is None:
            logger.command_log(ctx, "DM command")
            embed = discord.Embed(title="DM에서 실행할 수 없습니다.", description=f"이 명령어는 {election_server_name}에서만 사용할 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 서버 ID 체크
        if ctx.guild.id != election_server_id:
            logger.command_log(ctx, "Wrong server ID")
            embed = discord.Embed(title="다른 서버에서 실행할 수 없습니다.", description=f"이 명령어는 {election_server_name}에서만 사용할 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 선거인 등록 조건 확인
        joined_date = ctx.author.joined_at
        if (electionmain["start"].date() - joined_date.date()).days >= condition["voter"]:
            can_signup = True
        
        elasted = (electionmain["start"].date() - joined_date.date()).days

        # 이미 선거인으로 등록되어 있는지 확인
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        voter_num = 0
        if temp != []:
            is_voter = True
            # 선거인으로 등록되어 있는 경우 DB에 정보 업데이트
            db.execute("UPDATE voters SET display_name = ?, nick = ? WHERE id = ?", 
                       (ctx.author.display_name, ctx.author.name, ctx.author.id))
            db.execute("SELECT pk FROM voters WHERE id = ?", (ctx.author.id,))
            voter_num = db.fetchall()[0][0]

        embed = discord.Embed(title="선거인 등록 정보", color=discord.Color.blue())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="표시 이름", value=ctx.author.display_name, inline=True)
        embed.add_field(name="닉네임", value=ctx.author.name, inline=True)
        embed.add_field(name="아이디", value=ctx.author.id, inline=True)
        embed.add_field(name="등록 조건", value=f"- {"충족됨" if can_signup else "- 충족되지 않음"} ({elasted}일)", inline=False)
        embed.add_field(name="등록 상태", value=f"- 등록됨 (등록번호 {voter_num}번)" if is_voter else "- 등록되지 않음", inline=False)
        await ctx.respond(embed=embed, view=None)

    @voter_group.command(name="등록", description="선거인으로 등록할 수 있습니다.")
    async def voter_register(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        now = datetime.now()

        # DM 체크
        if ctx.guild is None:
            logger.command_log(ctx, "DM command")
            embed = discord.Embed(title="DM에서 실행할 수 없습니다.", description=f"이 명령어는 {election_server_name}에서만 사용할 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 서버 ID 체크
        if ctx.guild.id != election_server_id:
            logger.command_log(ctx, "Wrong server ID")
            embed = discord.Embed(title="다른 서버에서 실행할 수 없습니다.", description=f"이 명령어는 {election_server_name}에서만 사용할 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 선거인 등록 기간 확인
        joined_date = ctx.author.joined_at
        if now < voter["start"] or now > voter["end"]:
            logger.command_log(ctx, "Not in voter registration period")
            embed = discord.Embed(title="선거인 등록 기간이 아닙니다.", description=f"선거인 등록 기간은 {voter['start']} ~ {voter['end']} 입니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 선거인 등록 조건 확인
        if (electionmain["start"].date() - joined_date.date()).days < condition["voter"]:
            logger.command_log(ctx, "Not enough days since joined")
            embed = discord.Embed(title="선거인 등록 조건을 충족하지 않습니다.", description=f"선거인은 본선거일 기준 서버에 들어온지 {condition["voter"]}일이 경과해야 합니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        class Button(discord.ui.View):
            def __init__(self, ctx: discord.ApplicationContext):
                super().__init__(timeout=10 + ctx.bot.latency)
                self.ctx = ctx
                self.button_value = None
                self.passphrase = None

            @discord.ui.button(label="등록", style=discord.ButtonStyle.green)
            async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "등록"
                view_self = self
                self.timeout = None
                class Modal(discord.ui.Modal):
                    def __init__(self, *args, **kwargs) -> None:
                        super().__init__(*args, **kwargs)
                        self.add_item(discord.ui.InputText(
                            label="인증 문자열을 신규 입력해주세요. (추후 본인 인증을 위해 사용됩니다)",
                            placeholder="인증 문자열 입력",
                            value=str(interaction.user.name),
                            required=True,
                            max_length=32
                        ))

                    async def callback(self, modal_interaction: discord.Interaction):
                        logger.command_log(ctx, f"Modal summited by {modal_interaction.user.name}({modal_interaction.user.id})")
                        view_self.passphrase = self.children[0].value
                        await modal_interaction.response.defer()
                        view_self.stop()

                modal = Modal(title="선거인 등록")
                await interaction.response.send_modal(modal)
                await asyncio.sleep(180.0)
                self.timeout = 10 + ctx.bot.latency

            @discord.ui.button(label="취소", style=discord.ButtonStyle.red)
            async def cancel(self, button: discord.ui.Button, interation: discord.Interaction):
                self.button_value = "취소"
                self.stop()
                await interation.response.defer()
        
            async def interaction_check(self, interaction):
                logger.command_log(ctx, f"Button clicked by {interaction.user.name}({interaction.user.id})")
                if interaction.user != self.ctx.author:
                    await interaction.response.send_message("명령어를 직접 실행해서 사용해주시길 바랍니다.", ephemeral=True)
                    self.button_value = None
                    return False
                else:
                    return True

        # 이미 선거인으로 등록되어 있는지 확인
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()
        
        if temp != []:
            logger.command_log(ctx, "Already registered as voter")
            embed = discord.Embed(title="이미 선거인으로 등록되어 있습니다.", description="선거인 등록 취소를 원하신다면 `/선거인 취소`를 사용하시길 바랍니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        description = "```\n" \
        "1. 선거인으로 등록하지 않으면 선거에 참여하실 수 없습니다.\n" \
        "2. 선거인 등록 기간 중 언제나 선거인 등록을 취소할 수 있습니다.\n" \
        "```"
        embed = discord.Embed(title="선거인으로 등록할까요?", description=description, color=discord.Color.blue())
        view = Button(ctx)
        await ctx.respond(embed=embed, view=view)
        result = await view.wait()
        if result:
            logger.command_log(ctx, "Timed out")
            embed = discord.Embed(title="시간초과 되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`")
            return await ctx.edit(embed=embed, view=None)
        view.stop()
        if view.button_value == "취소":
            logger.command_log(ctx, "Cancelled")
            embed = discord.Embed(title="선거인 등록을 취소했습니다.")
            return await ctx.edit(embed=embed, view=None)
        elif view.button_value == "등록":
            logger.command_log(ctx, "Register")
            passphrase = view.passphrase
            logger.command_log(ctx, f"Passphrase inputed \"{passphrase}\"")
            db.execute("INSERT INTO voters (display_name, nick, id, passphrase) VALUES (?, ?, ?, ?)", 
                       (ctx.author.display_name, ctx.author.name, ctx.author.id, passphrase))
            embed = discord.Embed(title="선거인 등록이 완료되었습니다.", description="선거인 등록을 취소하고 싶으시다면 `/선거인 취소`를 사용하시길 바랍니다.", color=discord.Color.green())
            return await ctx.edit(embed=embed, view=None)
        
    @voter_group.command(name="취소", description="선거인 등록을 취소합니다.")
    async def voter_cancel(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        now = datetime.now()

        # DM 체크
        if ctx.guild is None:
            logger.command_log(ctx, "DM command")
            embed = discord.Embed(title="DM에서 실행할 수 없습니다.", description=f"이 명령어는 {election_server_name}에서만 사용할 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 서버 ID 체크
        if ctx.guild.id != election_server_id:
            logger.command_log(ctx, "Wrong server ID")
            embed = discord.Embed(title="다른 서버에서 실행할 수 없습니다.", description=f"이 명령어는 {election_server_name}에서만 사용할 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 선거인 등록 기간 확인
        if now < voter["start"] or now > voter["end"]:
            logger.command_log(ctx, "Not in voter registration period")
            embed = discord.Embed(title="선거인 등록 기간이 아닙니다.", description=f"선거인 등록 기간은 {voter['start']} ~ {voter['end']} 입니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 이미 선거인으로 등록되어 있는지 확인
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp == []:
            logger.command_log(ctx, "Not registered as voter")
            embed = discord.Embed(title="선거인으로 등록되어 있지 않습니다.", description="선거인 등록을 원하신다면 `/선거인 등록`을 사용하시길 바랍니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        # 후보자 등록 확인
        db.execute("SELECT id FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp != []:
            logger.command_log(ctx, "Registered as candidate")
            embed = discord.Embed(title="후보자로 등록되어 있습니다.", description="후보자로 등록이 되어있는 경우 선거인 등록을 취소할 수 없습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        class Button(discord.ui.View):
            def __init__(self, ctx: discord.ApplicationContext):
                super().__init__(timeout=10 + ctx.bot.latency)
                self.ctx = ctx
                self.button_value = None
                self.passphrase = None

            @discord.ui.button(label="취소", style=discord.ButtonStyle.green)
            async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "취소"
                view_self = self
                self.timeout = None
                class Modal(discord.ui.Modal):
                    def __init__(self, *args, **kwargs) -> None:
                        super().__init__(*args, **kwargs)
                        self.add_item(discord.ui.InputText(
                            label="인증 문자열을 입력해주세요.",
                            placeholder="인증 문자열 입력",
                            value=str(interaction.user.name),
                            required=True,
                            max_length=32
                        ))

                    async def callback(self, modal_interaction: discord.Interaction):
                        logger.command_log(ctx, f"Modal summited by {modal_interaction.user.name}({modal_interaction.user.id})")
                        view_self.passphrase = self.children[0].value
                        await modal_interaction.response.defer()
                        view_self.stop()

                modal = Modal(title="인증 문자열 입력")
                await interaction.response.send_modal(modal)
                await asyncio.sleep(180.0)
                self.timeout = 10 + ctx.bot.latency

            @discord.ui.button(label="등록 유지", style=discord.ButtonStyle.red)
            async def no(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "유지"
                self.stop()
                await interaction.response.defer()
        
            async def interaction_check(self, interaction):
                logger.command_log(ctx, f"Button clicked by {interaction.user.name}({interaction.user.id})")
                if interaction.user != self.ctx.author:
                    await interaction.response.send_message("명령어를 직접 실행해서 사용해주시길 바랍니다.", ephemeral=True)
                    self.button_value = None
                    return False
                else:
                    return True

        description = "```\n" \
        "1. 선거인 등록을 취소하면 선거에 참여할 수 없습니다.\n" \
        "2. 선거인 등록 기간 언제든지 다시 선거인에 등록할 수 있습니다.\n" \
        "```"
        embed = discord.Embed(title="선거인 등록을 취소할까요?", description=description, color=discord.Color.blue())
        view = Button(ctx)
        await ctx.respond(embed=embed, view=view)
        result = await view.wait()
        if result:
            logger.command_log(ctx, "Timed out")
            embed = discord.Embed(title="시간초과 되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`")
            return await ctx.edit(embed=embed, view=None)
        view.stop()
        if view.button_value == "유지":
            logger.command_log(ctx, "Keep registration")
            embed = discord.Embed(title="선거인 등록을 유지합니다.")
            return await ctx.edit(embed=embed, view=None)
        elif view.button_value == "취소":
            logger.command_log(ctx, "Cancel registration")
            passphrase = view.passphrase
            logger.command_log(ctx, f"Passphrase inputed \"{passphrase}\"")
            # 인증 문자열 확인
            db.execute("SELECT passphrase FROM voters WHERE id = ?", (ctx.author.id,))
            temp = db.fetchall()
            logger.command_log(ctx, f"Passphrase check \"{temp}\"")
            if temp == [] or temp[0][0] != passphrase:
                logger.command_log(ctx, "Invalid passphrase")
                embed = discord.Embed(title="인증 문자열이 일치하지 않습니다.", description="올바른 인증 문자열을 입력해 주세요.", color=discord.Color.red())
                return await ctx.edit(embed=embed, view=None)
            
            db.execute("DELETE FROM voters WHERE id = ?", (ctx.author.id,))
            embed = discord.Embed(title="선거인 등록을 취소했습니다.", description="선거인 등록을 다시 하고 싶으시다면 `/선거인 등록`을 사용하시길 바랍니다.", color=discord.Color.green())
            return await ctx.edit(embed=embed, view=None)
        
def setup(bot):
    bot.add_cog(VoterCog(bot))