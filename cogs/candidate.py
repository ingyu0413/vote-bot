import asyncio
from datetime import datetime
import discord
from discord.ext import commands
import utils.logger as logger
from utils.db import database
from utils.config import *

db = database()

"""
    CandidateCog: 후보자 관련 명령어를 처리하는 Cog

    - candidate_info: 후보자 등록 정보를 확인하는 명령어 (/후보자 정보)
    - candidate_register: 후보자로 등록하는 명령어 (/후보자 등록)
    - candidate_cancel: 후보자 등록을 취소하는 명령어 (/후보자 사퇴)
    - candidate_config: 후보자 정보(공약 등)을 관리하는 명령어 (/후보자 설정)
"""
class CandidateCog(commands.Cog):
    candidate_group = discord.SlashCommandGroup("후보자", "후보자 관련 명령어입니다.")

    def __init__(self, bot: discord.AutoShardedBot):
        self.bot = bot
        logger.log("CandidateCog 로딩 성공!")

    @candidate_group.command(name="정보", description="후보자 등록 정보를 확인합니다.")
    async def candidate_info(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        is_candidate = False
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

        # 후보자 등록 조건 확인
        joined_date = ctx.author.joined_at
        if (electionmain["start"].date() - joined_date.date()).days >= condition["candidate"]:
            can_signup = True
        
        elasted = (electionmain["start"].date() - joined_date.date()).days

        # 선거인 등록 여부 확인
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        voter_num = 0
        if temp != []:
            is_voter = True
            db.execute("SELECT pk FROM voters WHERE id = ?", (ctx.author.id,))
            voter_num = db.fetchall()[0][0]
        else:
            can_signup = False

        # 이미 후보자로 등록되어 있는지 확인
        db.execute("SELECT id FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        candidate_num = 0
        if temp != []:
            is_candidate = True
            # 후보자로 등록되어 있는 경우 DB에 정보 업데이트
            db.execute("UPDATE candidates SET display_name = ?, nick = ?, avatar_url = ? WHERE id = ?", 
                       (ctx.author.display_name, ctx.author.name, ctx.author.display_avatar.url,ctx.author.id))
            db.execute("SELECT pk FROM candidates WHERE id = ?", (ctx.author.id,))
            candidate_num = db.fetchall()[0][0]

        # 후보자 번호 확인
        candidate_number = 0
        is_resign = False
        if is_candidate:
            db.execute("SELECT number FROM candidates WHERE id = ?", (ctx.author.id,))
            candidate_number = db.fetchall()[0][0]
            db.execute("SELECT resign FROM candidates WHERE id = ?", (ctx.author.id,))
            is_resign = db.fetchall()[0][0] == 1

        embed = discord.Embed(title="후보자 등록 정보", color=discord.Color.blue())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="표시 이름", value=ctx.author.display_name, inline=True)
        embed.add_field(name="닉네임", value=ctx.author.name, inline=True)
        embed.add_field(name="아이디", value=ctx.author.id, inline=True)
        embed.add_field(name="등록 조건", value=f"- {"충족됨"  if can_signup else "충족되지 않음"} ({elasted}일, 선거인 등록 {"O" if is_voter else "X"})", inline=False)
        embed.add_field(name="선거인 등록 상태", value=f"- 등록됨 (등록번호 {voter_num}번)" if is_voter else "- 등록되지 않음", inline=False)
        embed.add_field(name="후보자 등록 상태", value=f"- {"등록됨" if not is_resign else "사퇴함"} (등록번호 {candidate_num}번, 후보자 번호 {"미지정" if candidate_number == 0 else f"{candidate_number}번"})" if is_candidate else "- 등록되지 않음", inline=False)
        await ctx.respond(embed=embed, view=None)

    @candidate_group.command(name="등록", description="후보자로 등록할 수 있습니다.")
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

        # 후보자 등록 기간 확인
        joined_date = ctx.author.joined_at
        if now < candidate["start"] or now > candidate["end"]:
            logger.command_log(ctx, "Not in candidate registration period")
            embed = discord.Embed(title="후보자 등록 기간이 아닙니다.", description=f"후보자 등록 기간은 {candidate['start']} ~ {candidate['end']} 입니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 후보자 등록 조건 확인
        if (electionmain["start"].date() - joined_date.date()).days < condition["candidate"]:
            logger.command_log(ctx, "Not enough days since joined")
            embed = discord.Embed(title="후보자 등록 조건을 충족하지 않습니다.", description=f"선거인은 본선거일 기준 서버에 들어온지 {condition["voter"]}일이 경과해야 합니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp == []:
            logger.command_log(ctx, "Not registered as voter")
            embed = discord.Embed(title="후보자 등록 조건을 충족하지 않습니다.", description="후보자로 등록하기 위해서는 선거인으로 등록되어 있어야 합니다. `/선거인 등록` 명령어를 사용하여 선거인으로 등록하십시오.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        class Button(discord.ui.View):
            def __init__(self, ctx: discord.ApplicationContext):
                super().__init__(timeout=10 + ctx.bot.latency)
                self.ctx = ctx
                self.button_value = None
                self.nickname = None

            @discord.ui.button(label="등록", style=discord.ButtonStyle.green)
            async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "등록"
                view_self = self
                self.timeout = None
                class Modal(discord.ui.Modal):
                    def __init__(self, *args, **kwargs) -> None:
                        super().__init__(*args, **kwargs)
                        self.add_item(discord.ui.InputText(
                            label="[선택] 별명을 입력하여 주십시오. (선거 기간동안 해당 별명으로 표시됩니다)",
                            placeholder="별명 입력 (빈칸으로 두어 기본값 사용)",
                            value=str(interaction.user.display_name),
                            required=False,
                            max_length=32
                        ))

                    async def callback(self, modal_interaction: discord.Interaction):
                        logger.command_log(ctx, f"Modal summited by {modal_interaction.user.name}({modal_interaction.user.id})")
                        view_self.nickname = self.children[0].value
                        await modal_interaction.response.defer()
                        view_self.stop()

                modal = Modal(title="후보자 별명 등록")
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
                
        # 사퇴 확인
        db.execute("SELECT resign FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()
        
        if temp != []:
            if temp[0][0] == 1:
                logger.command_log(ctx, "Already resigned")
                embed = discord.Embed(title="이미 후보자를 사퇴했습니다.", description="사퇴한 다음에 다시 후보자에 재등록할 수 없습니다.", color=discord.Color.red())
                return await ctx.respond(embed=embed, view=None)
        
        # 이미 후보자로 등록되어 있는지 확인
        db.execute("SELECT id FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()
        
        if temp != []:
            logger.command_log(ctx, "Already registered as candidate")
            embed = discord.Embed(title="이미 후보자로 등록되어 있습니다.", description="후보자 사퇴를 원하신다면 `/후보자 사퇴`를 사용하시길 바랍니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        description = "```\n" \
        "1. 후보자로 등록하여 선거에 출마할 수 있습니다.\n" \
        "2. 후보자 등록은 취소할 수 없습니다.\n" \
        "3. 후보자 사퇴 기간에 사퇴할 수 있습니다.\n" \
        "```"
        embed = discord.Embed(title="후보자로 등록하시겠습니까?", description=description, color=discord.Color.blue())
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
            embed = discord.Embed(title="후보자 등록을 취소했습니다.")
            return await ctx.edit(embed=embed, view=None)
        elif view.button_value == "등록":
            logger.command_log(ctx, "Register")
            nickname = view.nickname
            logger.command_log(ctx, f"Nickname inputed \"{nickname}\"")
            if nickname is not None:
                db.execute("INSERT INTO candidates (display_name, nick, avatar_url, id, display_nick, signed_time, joined_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (ctx.author.display_name, ctx.author.name, ctx.author.display_avatar.url, ctx.author.id, nickname, datetime.now(), ctx.author.joined_at))
            else: 
                db.execute("INSERT INTO candidates (display_name, nick, avatar_url, id, signed_time, joined_time) VALUES (?, ?, ?, ?, ?, ?)",
                        (ctx.author.display_name, ctx.author.name, ctx.author.display_avatar.url, ctx.author.id, datetime.now(), ctx.author.joined_at))
            description = "별명, 공약 등을 변경하고 싶다면 `/후보자 설정`을 이용하시길 바랍니다.\n" \
                          "후보자 사퇴를 원하신다면 `/후보자 사퇴` 명령어를 사용하시길 바랍니다."
            embed = discord.Embed(title="후보자 등록이 완료되었습니다.", description=description, color=discord.Color.green())
            return await ctx.edit(embed=embed, view=None)

    @candidate_group.command(name="사퇴", description="후보자를 사퇴합니다.")
    async def candidate_cancel(self, ctx: discord.ApplicationContext):
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

        # 후보자 등록 취소기간 확인
        if now < resigncand["start"] or now > resigncand["end"]:
            logger.command_log(ctx, "Not in resign candidate period")
            embed = discord.Embed(title="후보자 사퇴 신청 기간이 아닙니다.", description=f"후보자 사퇴 신청 기간은 {resigncand['start']} ~ {resigncand['end']} 입니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 후보자인지 확인
        db.execute("SELECT id FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp == []:
            logger.command_log(ctx, "Not registered as candidate")
            embed = discord.Embed(title="후보자로 등록되어 있지 않습니다.", description="후보자 등록을 원하신다면 `/후보자 등록`을 사용하시길 바랍니다.", color=discord.Color.red())
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
                            # value=str(interaction.user.name),
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

        # 사퇴 확인
        db.execute("SELECT resign FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp != []:
            if temp[0][0] == 1:
                logger.command_log(ctx, "Already resigned")
                embed = discord.Embed(title="이미 후보자를 사퇴했습니다.", description=f"{election_name}에 참가해주셔서 감사합니다.", color=discord.Color.red())
                return await ctx.respond(embed=embed, view=None)

        description = "```\n" \
        "1. 후보자 사퇴는 되돌릴 수 없습니다.\n" \
        "2. 후보자 목록에서 삭제되지 않고 투표시에 [사퇴]로 표시됩니다.\n" \
        "```"
        embed = discord.Embed(title="후보자를 사퇴할까요?", description=description, color=discord.Color.blue())
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
            embed = discord.Embed(title="후보자 등록을 유지합니다.")
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
            
            db.execute("UPDATE candidates SET resign = 1 WHERE id = ?", (ctx.author.id,))
            embed = discord.Embed(title="후보자를 사퇴했습니다.", description=f"{election_name}에 참가해주셔서 감사합니다.", color=discord.Color.green())
            return await ctx.edit(embed=embed, view=None)

    @candidate_group.command(name="설정", description="후보자 정보를 설정합니다.")
    async def candidate_config(self, ctx: discord.ApplicationContext):
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
        
        class Modal(discord.ui.Modal):
            display_nickname = None
            pledge = None

            def __init__(self, *args, **kwargs) -> None:
                super().__init__(timeout=600.0, *args, **kwargs)
                db.execute("SELECT display_nick, pledge FROM candidates WHERE id = ?", (ctx.author.id,))
                temp = db.fetchall()
                display_nickname = temp[0][0]
                pledge = temp[0][1]
                self.add_item(discord.ui.InputText(
                    label="별명 설정 (빈칸으로 두어 기본값 사용)",
                    placeholder="선거 기간동안 사용할 별명을 입력하세요.",
                    value=str(display_nickname),
                    required=False,
                    max_length=32
                ))
                self.add_item(discord.ui.InputText(
                    label="공약 설정 (빈칸으로 두어 미설정)",
                    placeholder="공약을 입력하세요.",
                    value=str(pledge),
                    style=discord.InputTextStyle.long,
                    required=False,
                    max_length=1000
                ))

            async def callback(self, modal_interaction: discord.Interaction):
                logger.command_log(ctx, f"Modal summited by {modal_interaction.user.name}({modal_interaction.user.id})")
                display_nickname = self.children[0].value
                pledge = self.children[1].value
                if display_nickname == '':
                    db.execute("UPDATE candidates SET display_nick = '' WHERE id = ?", (ctx.author.id,))
                else:
                    db.execute("UPDATE candidates SET display_nick = ? WHERE id = ?", (display_nickname, ctx.author.id))
                if pledge == '':
                    db.execute("UPDATE candidates SET pledge = '' WHERE id = ?", (ctx.author.id,))
                else:
                    db.execute("UPDATE candidates SET pledge = ? WHERE id = ?", (pledge, ctx.author.id))
                await modal_interaction.response.defer()
                embed = discord.Embed(title="후보자 정보가 업데이트 되었습니다.", color=discord.Color.green())
                embed.add_field(name="별명", value=display_nickname if display_nickname != '' else "기본값 사용", inline=True)
                embed.add_field(name="공약", value=pledge if pledge != '' else "미설정", inline=True)
                embed.set_footer(text=f"후보자 사퇴 신청 기간 종료 {resigncand['end']} 이후부터는 수정하실 수 없습니다.")
                await modal_interaction.followup.send(embed=embed)
                self.stop()

        # 후보자 등록 취소기간 확인
        if now > resigncand["end"]:
            logger.command_log(ctx, "Out of period")
            embed = discord.Embed(title="지금은 변경할 수 없습니다.", description=f"후보자 사퇴 신청 기간 종료 {resigncand['end']} 이후부터는 수정하실 수 없습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        # 후보자인지 확인
        db.execute("SELECT id FROM candidates WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp == []:
            logger.command_log(ctx, "Not registered as candidate")
            embed = discord.Embed(title="후보자로 등록되어 있지 않습니다.", description="후보자 등록을 원하신다면 `/후보자 등록`을 사용하시길 바랍니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)

        modal = Modal(title="후보자 정보 설정")
        await ctx.send_modal(modal)
        result = await modal.wait()
        if not result:
            logger.command_log(ctx, "Timed out")
            embed = discord.Embed(title="시간초과 되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`")
            return await ctx.respond(embed=embed, view=None)

def setup(bot):
    bot.add_cog(CandidateCog(bot))