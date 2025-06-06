import hashlib
import asyncio
from datetime import datetime
import random
import string
import dateutil.parser
import discord
from discord.commands import slash_command
from discord.ext import commands
import utils.logger as logger
from utils.db import database
from utils.config import *

db = database()

"""
    ElectionCog: 선거 관련 명령어를 처리하는 Cog

    - election_info: 선거 정보를 확인하는 명령어 (/선거정보)
    - election_candidates: 후보자 정보를 확인할 수 있는 명령어 (/후보)
    - election_secure: 보안 문자열을 확인하는 명령어 (/보안문자)
    - election_run: 투표하는 명령어 (/투표)
"""
class ElectionCog(commands.Cog):
    def __init__(self, bot: discord.AutoShardedBot):
        self.bot = bot
        logger.log("ElectionCog 로딩 성공!")

    @slash_command(name="선거정보", description="현재 선거 정보를 확인합니다.")
    async def election_info(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        # 선거인 명수 및 후보자 명수 확인
        voter_count = 0
        candidate_count = 0
        resigncand_count = 0

        db.execute("SELECT COUNT(*) FROM voters")
        voter_count = db.fetchall()[0][0]
        db.execute("SELECT COUNT(*) FROM candidates")
        candidate_count = db.fetchall()[0][0]
        db.execute("SELECT COUNT(*) FROM candidates WHERE resign = 1")
        resigncand_count = db.fetchall()[0][0]

        now = datetime.now()
        embed = discord.Embed(title=f"{election_name}", color=discord.Color.blue())
        embed.add_field(name="대상", value=f"{election_position} ({election_number}명)", inline=True)
        embed.add_field(name="근거", value=f"{election_rule}", inline=True)
        embed.add_field(name="임기", value=f"{election_term}", inline=False)

        embed.add_field(name="선거인 명수", value=f"{voter_count}명", inline=True)
        embed.add_field(name="후보자 명수", value=f"{candidate_count}명 (사퇴 {resigncand_count}명)", inline=True)

        embed.add_field(name="선거인 등록 기간", value=f"- {voter['start'].strftime('%Y-%m-%d %H:%M')} ~ {voter['end'].strftime('%Y-%m-%d %H:%M')}", inline=False)
        embed.add_field(name="후보자 등록 기간", value=f"- {candidate['start'].strftime('%Y-%m-%d %H:%M')} ~ {candidate['end'].strftime('%Y-%m-%d %H:%M')}", inline=False)
        embed.add_field(name="후보자 사퇴 기간", value=f"- {resigncand['start'].strftime('%Y-%m-%d %H:%M')} ~ {resigncand['end'].strftime('%Y-%m-%d %H:%M')}", inline=False)
        embed.add_field(name="사전 투표 기간", value=f"- {electionpre['start'].strftime('%Y-%m-%d %H:%M')} ~ {electionpre['end'].strftime('%Y-%m-%d %H:%M')}", inline=False)
        embed.add_field(name="본 투표 기간", value=f"- {electionmain['start'].strftime('%Y-%m-%d %H:%M')} ~ {electionmain['end'].strftime('%Y-%m-%d %H:%M')}", inline=False)
        embed.set_footer(text=f"기준: KST (GTC+09:00), 현재 서버 시간: {now.strftime('%Y-%m-%d %H:%M')}")
        await ctx.respond(embed=embed)

    @slash_command(name="후보", description="후보자 정보를 확인합니다.")
    async def election_candidates(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        db.execute("SELECT * FROM candidates ORDER BY number ASC")
        candidates = db.fetchall()
        if candidates[-1][5] == 0:
            db.execute("SELECT * FROM candidates ORDER BY pk ASC")
            candidates = db.fetchall()
        """ 후보자 DB TABLE 
            0. pk
            1. display_name (후보자 별명)
            2. nick (후보자 사용자명)
            3. avatar_url (후보자 아바타 URL)
            4. id (후보자 ID)
            5. number (후보자 번호)
            6. display_nick (후보자 표시 별명)
            7. pledge (후보자 공약)
            8. signed_time (후보자 등록 시간)
            9. joined_time (서버 가입 시간)
            10. resign (후보자 사퇴 여부, 0: 활성, 1: 사퇴)
        """
        emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "*️⃣"]

        class CandidateView(discord.ui.View):
            def __init__(self, bot_: discord.Bot, ctx_: discord.ApplicationContext):
                self.ctx = ctx_
                self.bot = bot_
                self.button_visible = False

                self.page_now = 1
                self.page_max = 2
                self.selected_candidate = None
                super().__init__(timeout=300.0)
                self.add_item(Select(self, self.bot, self.ctx))
                # self.update_items()

            def update_items(self):
                self.clear_items()
                self.add_item(Button_Left(self, disabled=(self.page_now == 1)))
                self.add_item(Button_Middle(self, disabled=False, label=f"{self.page_now}/{self.page_max}"))
                self.add_item(Button_Right(self, disabled=(self.page_now == self.page_max)))
                self.add_item(Select(self, self.bot, self.ctx, 1))

            async def update_page(self, interaction: discord.Interaction):
                self.update_items()
                db.execute("SELECT * FROM candidates WHERE pk = ?", (self.selected_candidate,))
                candidate_info = db.fetchall()[0]
                
                embed = discord.Embed(title="후보자 등록 정보", color=discord.Color.blue())
                embed.set_thumbnail(url=candidate_info[3])
                embed.add_field(name="기호", value=f"{candidate_info[5]}번{"" if candidate_info[10] != 1 else " (사퇴)"}", inline=True)
                embed.add_field(name="이름", value=candidate_info[6] if candidate_info[6] != '' else candidate_info[1], inline=True)
                embed.add_field(name="표시 이름", value=candidate_info[1], inline=True)
                embed.add_field(name="닉네임", value=candidate_info[2], inline=True)
                embed.add_field(name="아이디", value=candidate_info[4], inline=True)
                if self.page_now == 1:
                    db.execute("SELECT name, start, end FROM career WHERE user_id = ? AND type = ?", (candidate_info[4], "elect",))
                    careers = db.fetchall()
                    career_str = "(없음)"
                    if careers != []:
                        career_str = "\n".join([f"{career[0]} [{dateutil.parser.parse(career[1]).strftime('%Y-%m-%d')} ~ {dateutil.parser.parse(career[2]).strftime('%Y-%m-%d')}]" for career in careers])
                    db.execute("SELECT name, start FROM career WHERE user_id = ? AND type = ?", (candidate_info[4], "sentence",))
                    sentences = db.fetchall()
                    sentence_str = "(없음)"
                    if sentences != []:
                        sentence_str = "\n".join([f"{sentence[0]} [{dateutil.parser.parse(sentence[1]).strftime('%Y-%m-%d %H:%M:%S')}]" for sentence in sentences])
                    joined_server = dateutil.parser.parse(candidate_info[9])
                    registered_time = dateutil.parser.parse(candidate_info[8])
                    elasted = (electionmain["start"].date() - joined_server.date()).days
                    embed.add_field(name="서버 접속 시간", value=f"{joined_server.strftime("%Y-%m-%d %H:%M")} (본투표일 기준 {elasted}일)", inline=False)
                    embed.add_field(name="후보자 등록 시간", value=registered_time.strftime("%Y-%m-%d %H:%M"), inline=False)
                    embed.add_field(name="경력 사항", value=f"```md\n{career_str}\n```", inline=False)
                    embed.add_field(name="처벌 기록", value=f"```md\n{sentence_str}\n```", inline=False)
                elif self.page_now == 2:
                    embed.add_field(name="공약", value=f"```md\n{candidate_info[7] if candidate_info[7] != "" else "(없음)"}\n```", inline=False)
                await interaction.response.edit_message(embed=embed, view=self)

            async def interaction_check(self, interaction):
                logger.command_log(ctx, f"View clicked by {interaction.user.name}({interaction.user.id})")
                if interaction.user != self.ctx.author:
                    await interaction.response.send_message("명령어를 직접 실행해서 사용해주시길 바랍니다.", ephemeral=True)
                    self.button_value = None
                    return False
                else:
                    return True

        class Button_Left(discord.ui.Button):
            def __init__(self, view_: CandidateView, disabled: bool = False):
                self.parent_view = view_
                super().__init__(label="<", style=discord.ButtonStyle.primary, disabled=disabled, row=0)

            async def callback(self, interaction: discord.Interaction):
                self.parent_view.page_now -= 1
                if self.parent_view.page_now < 1:
                    self.parent_view.page_now = 1
                await self.parent_view.update_page(interaction)

        class Button_Middle(discord.ui.Button):
            def __init__(self, view_: CandidateView, disabled: bool = False, label: str = "/"):
                self.parent_view = view_
                super().__init__(label=label, style=discord.ButtonStyle.secondary, disabled=disabled, row=0)

            async def callback(self, interaction: discord.Interaction):
                await self.parent_view.update_page(interaction)

        class Button_Right(discord.ui.Button):
            def __init__(self, view_: CandidateView, disabled: bool = False):
                self.parent_view = view_
                super().__init__(label=">", style=discord.ButtonStyle.primary, disabled=disabled, row=0)

            async def callback(self, interaction: discord.Interaction):
                self.parent_view.page_now += 1
                if self.parent_view.page_now > self.parent_view.page_max:
                    self.parent_view.page_now = self.parent_view.page_max
                await self.parent_view.update_page(interaction)

        class Select(discord.ui.Select):
            def __init__(self, view_: CandidateView, bot_: discord.Bot, ctx_: discord.ApplicationContext, row: int = 0):
                self.parent_view = view_
                self.ctx = ctx_
                self.bot = bot_
                options = []
                for a in candidates:
                    options.append(discord.SelectOption(
                        label=f"[{f"기호 {a[5]}" if a[5] != 0 else '미정'}] {a[6] if a[6] != '' else a[1]}{"" if a[10] == 0 else "(사퇴)"}",  # display_nick
                        description=f"{a[2]} ({a[4]})",  # nick, id
                        emoji=emojis[a[5]] if a[5] <= 10 else emojis[11], # number
                        value=str(a[0])  # pk
                    ))
                super().__init__(
                    placeholder="후보자 선택",
                    min_values=1,
                    max_values=1,
                    options=options,
                    row=row
                )

            async def callback(self, interaction: discord.Interaction):
                self.parent_view.selected_candidate = self.values[0]
                await self.parent_view.update_page(interaction)

        embed = discord.Embed(title="후보자 목록", description="후보자를 선택해주세요.", color=discord.Color.blue())
        embed.set_footer(text="후보자 목록은 기호 순서대로 표시됩니다.")
        view = CandidateView(self.bot, ctx)
        await ctx.respond(embed=embed, view=view)
        result = await view.wait()
        if result:
            await ctx.edit(view=None)

    @slash_command(name="보안문자", description="선거 보안 문자열을 확인합니다.")
    async def election_secure(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)

        # 선거인으로 등록되어 있는지 확인
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp == []:
            logger.command_log(ctx, "Not registered as voter")
            embed = discord.Embed(title="선거인으로 등록되어 있지 않습니다.", description="보안 문자열은 선거인으로 등록되어 있어야 발급받을 수 있습니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        # 선거 했는지 확인
        db.execute("SELECT voted FROM secure WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()
        
        if temp != []:
            if temp[0][0] == 1:
                logger.command_log(ctx, "Already voted")
                embed = discord.Embed(title="보안 문자열을 발급할 수 없습니다.", description="선거에 참여한 경우 보안 문자열을 재발급할 수 없습니다.", color=discord.Color.red())
                return await ctx.respond(embed=embed, view=None)
        
        class Button(discord.ui.View):
            def __init__(self, ctx: discord.ApplicationContext):
                super().__init__(timeout=30 + ctx.bot.latency)
                self.ctx = ctx
                self.button_value = None
                self.passphrase = None

            @discord.ui.button(label="본 투표용", style=discord.ButtonStyle.green)
            async def formain(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "본 투표"
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

            @discord.ui.button(label="사전 투표용", style=discord.ButtonStyle.red)
            async def forpre(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "사전 투표"
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

            @discord.ui.button(label="취소", style=discord.ButtonStyle.gray)
            async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "취소"
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
        "1. 보안 문자열이 없으면 선거에 참여하실 수 없습니다.\n" \
        "2. 보안 문자열은 잃어버리면 재발급 받아야하며, 기존 보안 문자열은 무효처리 됩니다.\n" \
        "3. 인증 문자열을 변경할 경우 보안 문자열이 무효화됩니다. 이 경우, 보안 문자열을 재발급 받아야 합니다.\n" \
        "4. 본투표용과 사전투표용이 구분되어 있습니다. 둘 중 하나만 발급받을 수 있습니다.\n" \
        "```"
        embed = discord.Embed(title="보안 문자열 발급", description=description, color=discord.Color.blue())
        view = Button(ctx)
        await ctx.respond(embed=embed, view=view)
        result = await view.wait()
        if result:
            logger.command_log(ctx, "Timed out")
            embed = discord.Embed(title="시간초과 되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`")
            return await ctx.edit(embed=embed, view=None)
        view.stop()
        if view.button_value == "취소":
            logger.command_log(ctx, "User cancelled the operation")
            embed = discord.Embed(title="보안 문자열 발급이 취소되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`", color=discord.Color.red())
            return await ctx.edit(embed=embed, view=None)
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
        
        # 보안 문자열 생성
        securephrase_pre = "PRE"
        while(len(securephrase_pre) < 16):
            securephrase_pre += random.choice(string.ascii_letters + string.digits)

        securephrase_main = "MAIN"
        while(len(securephrase_main) < 16):
            securephrase_main += random.choice(string.ascii_letters + string.digits)

        securephrase = None
        if view.button_value == "본 투표":
            securephrase = securephrase_main
        elif view.button_value == "사전 투표":
            securephrase = securephrase_pre

        hashed_sp_pre = hashlib.sha256(securephrase_pre.encode()).hexdigest()
        hashed_sp_main = hashlib.sha256(securephrase_main.encode()).hexdigest()

        securephrase_pre = None
        securephrase_main = None

        # 보안 문자열 DB에 저장
        db.execute("SELECT id from secure WHERE id = ?", (ctx.author.id,))
        voter_pk = db.fetchall()
        if voter_pk == []:
            db.execute("INSERT INTO secure (id, passphrase, securephrase_pre, securephrase_main) VALUES (?, ?, ?, ?)",
                       (ctx.author.id, passphrase, hashed_sp_pre, hashed_sp_main))
        else:
            db.execute("UPDATE secure SET passphrase = ?, securephrase_pre = ?, securephrase_main = ? WHERE id = ?",
                       (passphrase, hashed_sp_pre, hashed_sp_main, ctx.author.id))

        button_value = view.button_value
        embed = discord.Embed(title="보안 문자열 발급 완료",
                              description="하단의 버튼을 눌러 보안 문자열을 복사하십시오.\n\n" \
                                          "**보안 문자열을 잃어버린 경우 재발급 해야합니다!**\n" \
                                          "본 투표용: 본 투표 기간에 사용\n" \
                                          "사전 투표용: 사전 투표 기간에 사용",
                              color=discord.Color.green())
        
        embed1 = discord.Embed(title="보안 문자열 발급 완료",
                              description="**보안 문자열을 잃어버린 경우 재발급 해야합니다!**\n" \
                                          "본 투표용: 본 투표 기간에 사용\n" \
                                          "사전 투표용: 사전 투표 기간에 사용",
                              color=discord.Color.green())
        
        class Button2(discord.ui.View):
            def __init__(self, ctx: discord.ApplicationContext):
                super().__init__(timeout=60 + ctx.bot.latency)
                self.ctx = ctx

            @discord.ui.button(label="보안 문자열 확인", style=discord.ButtonStyle.primary)
            async def check(self, button: discord.ui.Button, interaction: discord.Interaction):
                view_self = self
                class Modal(discord.ui.Modal):
                    def __init__(self, *args, **kwargs) -> None:
                        super().__init__(*args, **kwargs)
                        self.add_item(discord.ui.InputText(
                            label=f"아래 발급된 보안 문자열을 복사하십시오.",
                            placeholder="보안 문자열",
                            value=str(securephrase),
                            required=True,
                            max_length=32
                        ))

                    async def callback(self, modal_interaction: discord.Interaction):
                        logger.command_log(ctx, f"Modal summited by {modal_interaction.user.name}({modal_interaction.user.id})")
                        await modal_interaction.response.edit_message(embed=embed1, view=None)
                        view_self.stop()

                modal = Modal(title=f"보안 문자열 ({button_value}용)")
                await interaction.response.send_modal(modal)
        
            async def interaction_check(self, interaction):
                logger.command_log(ctx, f"Button clicked by {interaction.user.name}({interaction.user.id})")
                if interaction.user != self.ctx.author:
                    await interaction.response.send_message("명령어를 직접 실행해서 사용해주시길 바랍니다.", ephemeral=True)
                    self.button_value = None
                    return False
                else:
                    return True
        
        view = Button2(ctx)
        await ctx.edit(embed=embed, view=view)
        result = await view.wait()
        if result:
            return await ctx.edit(embed=embed1, view=None)

    @slash_command(name="투표", description="투표를 합니다.")
    async def election_run(self, ctx: discord.ApplicationContext):
        logger.command_log(ctx)
        now = datetime.now()

        # # (임시) 유저 확인
        # if ctx.author.id != 523981270611525633:
        #     logger.command_log(ctx, "TESTING")
        #     embed = discord.Embed(title="이 명령어는 미완성입니다.", description="아직 기능을 구현 중입니다.", color=discord.Color.red())
        #     return await ctx.respond(embed=embed, view=None)

        # 서버 체크
        if ctx.guild is not None:
            logger.command_log(ctx, "Not DM command")
            embed = discord.Embed(title="DM에서 명령어를 실행하여 주십시오.", description=f"보안을 위해서 이 명령어는 DM에서 실행해야 합니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        # 투표 기간 확인
        vote_time = None
        if now >= electionmain["start"] and now <= electionmain["end"]:
            vote_time = "본 투표"
        elif now >= electionpre["start"] and now <= electionpre["end"]:
            vote_time = "사전 투표"
        else:
            logger.command_log(ctx, "Not voting time")    
            embed = discord.Embed(title="투표 기간이 아닙니다.",
                                  description=f"투표는 투표 기간 내에만 가능합니다.\n\n" \
                                              f"사전 투표 기간: {electionpre['start'].strftime('%Y-%m-%d %H:%M')} ~ {electionpre['end'].strftime('%Y-%m-%d %H:%M')}" \
                                              f"\n본 투표 기간: {electionmain['start'].strftime('%Y-%m-%d %H:%M')} ~ {electionmain['end'].strftime('%Y-%m-%d %H:%M')}",
                                  color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        # 선거인 등록 여부 확인
        db.execute("SELECT id FROM voters WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()

        if temp == []:
            logger.command_log(ctx, "Not registered as voter")
            embed = discord.Embed(title="선거인으로 등록되어 있지 않습니다.", description="투표는 선거인으로 등록되어 있어야 가능합니다.", color=discord.Color.red())
            return await ctx.respond(embed=embed, view=None)
        
        # 투표 여부 확인
        db.execute("SELECT voted FROM secure WHERE id = ?", (ctx.author.id,))
        temp = db.fetchall()
        if temp != []:
            if temp[0][0] == 1:
                logger.command_log(ctx, "Already voted")
                embed = discord.Embed(title="이미 투표를 했습니다.", description=f"{election_name}에 참가해주셔서 감사합니다.", color=discord.Color.red())
                return await ctx.respond(embed=embed, view=None)

        class Button(discord.ui.View):
            def __init__(self, ctx: discord.ApplicationContext):
                super().__init__(timeout=10 + ctx.bot.latency)
                self.ctx = ctx
                self.button_value = None
                self.passphrase = None
                self.securephrase = None

            @discord.ui.button(label="투표하기", style=discord.ButtonStyle.green)
            async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.button_value = "투표"
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
                        self.add_item(discord.ui.InputText(
                            label="보안 문자열을 입력해주세요.",
                            placeholder="보안 문자열 입력",
                            # value=str(interaction.user.name),
                            required=True,
                            max_length=32
                        ))

                    async def callback(self, modal_interaction: discord.Interaction):
                        logger.command_log(ctx, f"Modal summited by {modal_interaction.user.name}({modal_interaction.user.id})")
                        view_self.passphrase = self.children[0].value
                        view_self.securephrase = hashlib.sha256(self.children[1].value.encode()).hexdigest()
                        await modal_interaction.response.defer()
                        view_self.stop()

                modal = Modal(title="인증 문자열, 보안 문자열 입력")
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

        description = "지금 당장 바로 투표에 참여하실 수 있습니다.\n\n" \
                      "```\n" \
                      "1. 투표에 참여한 이후에는 다시 투표하실 수 없습니다.\n" \
                      "2. 인증 문자열, 보안 문자열이 있어야 투표에 참여하실 수 있습니다.\n" \
                      "3. 투표 과정 중 문제가 발생한 경우에는 반드시 관리자를 호출하여야 합니다.\n" \
                      "```"
        embed = discord.Embed(title=f"지금은 {vote_time} 기간입니다!", description=description, color=discord.Color.blue())
        view = Button(ctx)
        await ctx.respond(embed=embed, view=view)
        result = await view.wait()
        if result:
            logger.command_log(ctx, "Timed out")
            embed = discord.Embed(title="시간초과 되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`")
            return await ctx.edit(embed=embed, view=None)
        view.stop()
        if view.button_value == "취소":
            logger.command_log(ctx, "Cancel Vote")
            embed = discord.Embed(title="투표를 취소했습니다.")
            return await ctx.edit(embed=embed, view=None)
        elif view.button_value == "투표":
            logger.command_log(ctx, "Vote requested")
            passphrase = view.passphrase
            securephrase = view.securephrase

            embed1 = discord.Embed(title="인증 문자열 또는 보안 문자열이 일치하지 않습니다.", description="올바른 인증 문자열 또는 보안 문자열을 입력해 주십시오.", color=discord.Color.red())
            embed2 = discord.Embed(title="보안 문자열이 유효하지 않습니다.",
                                   description="인증 문자열이 바뀌였거나, 보안 문자열을 발급받은 적이 없는 경우 발생할 수 있습니다.\n`/보안문자`를 통해서 보안 문자열을 재발급 해주십시오.",
                                   color=discord.Color.red())

            # 인증 문자열 검증
            db.execute("SELECT passphrase FROM secure WHERE id = ?", (ctx.author.id,))
            temp = db.fetchall()
            if temp == []:
                logger.command_log(ctx, "Securephrase not found")
                return await ctx.edit(embed=embed2, view=None)
            if temp[0][0] != passphrase:
                logger.command_log(ctx, "Passphrase mismatch")
                return await ctx.edit(embed=embed1, view=None)
            
            # 보안 문자열 검증
            db.execute("SELECT securephrase_pre, securephrase_main FROM secure WHERE id = ?", (ctx.author.id,))
            temp = db.fetchall()
            try:
                securephrase_pre = temp[0][0]
                securephrase_main = temp[0][1]
            except IndexError:
                logger.command_log(ctx, "Securephrase not found")
                return await ctx.edit(embed=embed2, view=None)
            if vote_time == "본 투표":
                if securephrase == securephrase_pre:
                    logger.command_log(ctx, "securephrase_pre used for main vote")
                    return await ctx.edit(embed=embed1, view=None)
                elif securephrase != securephrase_main:
                    logger.command_log(ctx, "securephrase_main mismatch")
                    return await ctx.edit(embed=embed1, view=None)
            elif vote_time == "사전 투표":
                if securephrase == securephrase_main:
                    logger.command_log(ctx, "securephrase_main used for pre vote")
                    return await ctx.edit(embed=embed1, view=None)
                elif securephrase != securephrase_pre:
                    logger.command_log(ctx, "securephrase_pre mismatch")
                    return await ctx.edit(embed=embed1, view=None)

            # 인증 문자열 유효성 검증
            db.execute("SELECT passphrase FROM voters WHERE id = ?", (ctx.author.id,))
            temp1 = db.fetchall()
            db.execute("SELECT passphrase FROM secure WHERE id = ?", (ctx.author.id,))
            temp2 = db.fetchall()
            if temp1 == [] or temp2 == [] or temp1[0][0] != temp2[0][0]:
                logger.command_log(ctx, "Passphrase mismatch")
                return await ctx.edit(embed=embed2, view=None)
            
            db.execute("SELECT * FROM candidates ORDER BY number ASC")
            candidates = db.fetchall()
            if candidates[-1][5] == 0:
                db.execute("SELECT * FROM candidates ORDER BY pk ASC")
                candidates = db.fetchall()
            """ 후보자 DB TABLE 
                0. pk
                1. display_name (후보자 별명)
                2. nick (후보자 사용자명)
                3. avatar_url (후보자 아바타 URL)
                4. id (후보자 ID)
                5. number (후보자 번호)
                6. display_nick (후보자 표시 별명)
                7. pledge (후보자 공약)
                8. signed_time (후보자 등록 시간)
                9. joined_time (서버 가입 시간)
                10. resign (후보자 사퇴 여부, 0: 활성, 1: 사퇴)
            """
            emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "*️⃣"]

            class CandidateView(discord.ui.View):
                def __init__(self, bot_: discord.Bot, ctx_: discord.ApplicationContext):
                    self.ctx = ctx_
                    self.bot = bot_
                    self.confirm = False
                    self.voted = False

                    self.selected_candidate = None
                    super().__init__(timeout=300.0)
                    self.add_item(Select(self, self.bot, self.ctx))
                    # self.update_items()

                def update_items(self):
                    self.clear_items()
                    self.add_item(Button_Vote(self))
                    self.add_item(Button_Cancel(self))
                    self.add_item(Select(self, self.bot, self.ctx, 1))

                def update_items2(self):
                    self.clear_items()
                    self.add_item(Button_Vote(self))
                    self.add_item(Button_Cancel(self))

                async def update_page(self, interaction: discord.Interaction):
                    if self.confirm:
                        self.update_items2()
                    else:
                        self.update_items()
                    db.execute("SELECT * FROM candidates WHERE pk = ?", (self.selected_candidate,))
                    candidate_info = db.fetchall()[0]
                    
                    embed = discord.Embed(title="후보자 등록 정보", color=discord.Color.blue())
                    embed.set_thumbnail(url=candidate_info[3])
                    embed.add_field(name="기호", value=f"{candidate_info[5]}번{"" if candidate_info[10] != 1 else " (사퇴)"}", inline=True)
                    embed.add_field(name="이름", value=candidate_info[6] if candidate_info[6] != '' else candidate_info[1], inline=True)
                    embed.add_field(name="표시 이름", value=candidate_info[1], inline=True)
                    embed.add_field(name="닉네임", value=candidate_info[2], inline=True)
                    embed.add_field(name="아이디", value=candidate_info[4], inline=True)
                    db.execute("SELECT name, start, end FROM career WHERE user_id = ? AND type = ?", (candidate_info[4], "elect",))
                    careers = db.fetchall()
                    career_str = "(없음)"
                    if careers != []:
                        career_str = "\n".join([f"{career[0]} [{dateutil.parser.parse(career[1]).strftime('%Y-%m-%d %H:%M:%S')} ~ {dateutil.parser.parse(career[2]).strftime('%Y-%m-%d %H:%M:%S')}]" for career in careers])
                    db.execute("SELECT name, start FROM career WHERE user_id = ? AND type = ?", (candidate_info[4], "sentence",))
                    sentence = db.fetchall()
                    sentence_str = "(없음)"
                    if sentence != []:
                        sentence_str = "\n".join([f"{career[0]} [{dateutil.parser.parse(career[1]).strftime('%Y-%m-%d %H:%M:%S')}]" for career in careers])
                    joined_server = dateutil.parser.parse(candidate_info[9])
                    registered_time = dateutil.parser.parse(candidate_info[8])
                    elasted = (electionmain["start"].date() - joined_server.date()).days
                    embed.add_field(name="서버 접속 시간", value=f"{joined_server.strftime("%Y-%m-%d %H:%M")} (본투표일 기준 {elasted}일)", inline=False)
                    embed.add_field(name="후보자 등록 시간", value=registered_time.strftime("%Y-%m-%d %H:%M"), inline=False)
                    embed.add_field(name="경력 사항", value=f"```md\n{career_str}\n```", inline=False)
                    embed.add_field(name="처벌 기록", value=f"```md\n{sentence_str}\n```", inline=False)
                    if self.confirm:
                        embed.set_footer(text="정말 이 후보에게 투표하시겠습니까? 투표는 취소할 수 없습니다!")
                    else:
                        embed.set_footer(text=None)
                    await interaction.response.edit_message(embed=embed, view=self)

                async def interaction_check(self, interaction):
                    logger.command_log(ctx, f"View clicked by {interaction.user.name}({interaction.user.id})")
                    if interaction.user != self.ctx.author:
                        await interaction.response.send_message("명령어를 직접 실행해서 사용해주시길 바랍니다.", ephemeral=True)
                        self.button_value = None
                        return False
                    else:
                        return True

            class Button_Vote(discord.ui.Button):
                def __init__(self, view_: CandidateView):
                    self.parent_view = view_
                    super().__init__(label="투표하기", style=discord.ButtonStyle.primary, row=0)

                async def callback(self, interaction: discord.Interaction):
                    if self.parent_view.confirm == False:
                        self.parent_view.confirm = True
                        await self.parent_view.update_page(interaction)
                    elif self.parent_view.confirm == True:
                        logger.command_log(ctx, "Voted")
                        # embed = discord.Embed(title="투표를 진행중입니다...", description="오류가 발생하거나 멈춘 경우 반드시 관리자에게 문의해주시길 바랍니다.", color=discord.Color.yellow())
                        # await interaction.response.edit_message(embed=embed, view=None)
                        now = datetime.now()
                        db.execute("UPDATE secure SET voted = 1, votetime = ?, used_securephrase = ? WHERE id = ?", (now, securephrase, ctx.author.id,))
                        db.execute("SELECT id FROM candidates WHERE pk = ?", (self.parent_view.selected_candidate,))
                        candidate_id = db.fetchall()
                        db.execute("INSERT INTO votes (candidate_id, timestamp) VALUES (?, ?)", (candidate_id[0][0], now))
                        self.parent_view.voted = True
                        embed = discord.Embed(title="투표가 완료되었습니다.", description=f"{election_name}에 참가해주셔서 감사합니다.", color=discord.Color.green())
                        return await interaction.response.edit_message(embed=embed, view=None)

            class Button_Cancel(discord.ui.Button):
                def __init__(self, view_: CandidateView):
                    self.parent_view = view_
                    super().__init__(label="취소", style=discord.ButtonStyle.secondary, row=0)

                async def callback(self, interaction: discord.Interaction):
                    if self.parent_view.confirm == True:
                        self.parent_view.confirm = False
                        await self.parent_view.update_page(interaction)
                    elif self.parent_view.confirm == False:
                        logger.command_log(ctx, "Cancel Vote")
                        embed = discord.Embed(title="투표를 취소했습니다.")
                        await interaction.response.edit_message(embed=embed, view=None)

            class Select(discord.ui.Select):
                def __init__(self, view_: CandidateView, bot_: discord.Bot, ctx_: discord.ApplicationContext, row: int = 0):
                    self.parent_view = view_
                    self.ctx = ctx_
                    self.bot = bot_
                    options = []
                    for a in candidates:
                        options.append(discord.SelectOption(
                            label=f"[{f"기호 {a[5]}" if a[5] != 0 else '미정'}] {a[6] if a[6] != '' else a[1]}{"" if a[10] == 0 else "(사퇴)"}",  # display_nick
                            description=f"{a[2]} ({a[4]})",  # nick, id
                            emoji=emojis[a[5]] if a[5] <= 10 else emojis[11], # number
                            value=str(a[0])  # pk
                        ))
                    super().__init__(
                        placeholder="후보자 선택",
                        min_values=1,
                        max_values=1,
                        options=options,
                        row=row
                    )

                async def callback(self, interaction: discord.Interaction):
                    self.parent_view.selected_candidate = self.values[0]
                    await self.parent_view.update_page(interaction)

            embed = discord.Embed(title="투표", description="후보자를 선택해주세요.", color=discord.Color.blue())
            embed.set_footer(text="후보자 목록은 기호 순서대로 표시됩니다.")
            view = CandidateView(self.bot, ctx)
            await ctx.respond(embed=embed, view=view)
            result = await view.wait()
            if result:
                logger.command_log(ctx, "Timed out")
                embed = discord.Embed(title="시간초과 되었습니다.", description="`명령어를 다시 실행하여 사용해 주시길 바랍니다.`")
                return await ctx.edit(embed=embed, view=None)

def setup(bot):
    bot.add_cog(ElectionCog(bot))