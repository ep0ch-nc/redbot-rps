import random
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

CHOICES = ("rock", "paper", "scissors")
EMOJI = {"rock": "\U0001FAA8", "paper": "\U0001F4C4", "scissors": "✂️"}
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


def decide(player: str, bot_choice: str) -> str:
    if player == bot_choice:
        return "tie"
    return "win" if BEATS[player] == bot_choice else "loss"


class RPSView(discord.ui.View):
    def __init__(self, cog: "RPS", author: discord.abc.User, rounds: int = 1):
        super().__init__(timeout=60)
        self.cog = cog
        self.author = author
        self.rounds = rounds
        self.player_score = 0
        self.bot_score = 0
        self.ties = 0
        self.round_num = 1
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "This is not your game.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(content="Timed out.", view=self)
            except discord.HTTPException:
                pass

    def header(self) -> str:
        if self.rounds == 1:
            return f"**Rock Paper Scissors** — {self.author.display_name}"
        return (
            f"**Rock Paper Scissors (Best of {self.rounds})** — "
            f"{self.author.display_name}\nRound {self.round_num} | "
            f"You {self.player_score} - {self.bot_score} Bot (ties {self.ties})"
        )

    async def play(self, interaction: discord.Interaction, pick: str) -> None:
        bot_choice = random.choice(CHOICES)
        outcome = decide(pick, bot_choice)
        if outcome == "win":
            self.player_score += 1
        elif outcome == "loss":
            self.bot_score += 1
        else:
            self.ties += 1

        await self.cog.record(interaction.user, outcome)

        needed = self.rounds // 2 + 1
        finished = (
            self.rounds == 1
            or self.player_score >= needed
            or self.bot_score >= needed
        )

        round_line = (
            f"{EMOJI[pick]} You: **{pick}**\n"
            f"{EMOJI[bot_choice]} Bot: **{bot_choice}**\n"
            f"→ **{outcome.upper()}**"
        )

        if finished:
            if self.rounds == 1:
                summary = round_line
            else:
                if self.player_score > self.bot_score:
                    final = f"{self.author.display_name} wins the match!"
                elif self.bot_score > self.player_score:
                    final = "Bot wins the match!"
                else:
                    final = "Match tied."
                summary = (
                    f"{round_line}\n\n**Final:** You {self.player_score} - "
                    f"{self.bot_score} Bot (ties {self.ties}) — {final}"
                )
            for child in self.children:
                child.disabled = True
            self.stop()
            await interaction.response.edit_message(
                content=f"{self.header()}\n\n{summary}", view=self
            )
            return

        self.round_num += 1
        await interaction.response.edit_message(
            content=f"{self.header()}\n\n{round_line}", view=self
        )

    @discord.ui.button(label="Rock", emoji="\U0001FAA8", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.play(interaction, "rock")

    @discord.ui.button(label="Paper", emoji="\U0001F4C4", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.play(interaction, "paper")

    @discord.ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.play(interaction, "scissors")


class RPS(commands.Cog):
    """Rock Paper Scissors against the bot."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0x52505301, force_registration=True
        )
        self.config.register_user(wins=0, losses=0, ties=0)

    async def record(self, user: discord.abc.User, outcome: str) -> None:
        key = {"win": "wins", "loss": "losses", "tie": "ties"}[outcome]
        async with self.config.user(user).all() as data:
            data[key] = data.get(key, 0) + 1

    @commands.group(name="rps", invoke_without_command=True)
    async def rps(self, ctx: commands.Context, choice: Optional[str] = None):
        """Play rock paper scissors. No args = buttons. rock/paper/scissors for quick play."""
        if choice is None:
            view = RPSView(self, ctx.author, rounds=1)
            view.message = await ctx.send(
                f"{view.header()}\n\nPick one:", view=view
            )
            return

        pick = choice.lower()
        aliases = {"r": "rock", "p": "paper", "s": "scissors"}
        pick = aliases.get(pick, pick)
        if pick not in CHOICES:
            await ctx.send(
                f"Invalid choice `{choice}`. Use rock, paper, or scissors."
            )
            return

        bot_choice = random.choice(CHOICES)
        outcome = decide(pick, bot_choice)
        await self.record(ctx.author, outcome)
        await ctx.send(
            f"{EMOJI[pick]} You: **{pick}**\n"
            f"{EMOJI[bot_choice]} Bot: **{bot_choice}**\n"
            f"→ **{outcome.upper()}**"
        )

    @rps.command(name="bo")
    async def rps_bo(self, ctx: commands.Context, rounds: int):
        """Best-of-N match with buttons. N must be odd, 3-9."""
        if rounds < 3 or rounds > 9 or rounds % 2 == 0:
            await ctx.send("N must be odd and between 3 and 9.")
            return
        view = RPSView(self, ctx.author, rounds=rounds)
        view.message = await ctx.send(f"{view.header()}\n\nPick one:", view=view)

    @commands.command(name="rpsstats")
    async def rps_stats(
        self, ctx: commands.Context, user: Optional[discord.Member] = None
    ):
        """Show RPS stats for yourself or another user."""
        target = user or ctx.author
        data = await self.config.user(target).all()
        total = data["wins"] + data["losses"] + data["ties"]
        if total == 0:
            await ctx.send(f"{target.display_name} has not played yet.")
            return
        pct = data["wins"] / total * 100
        await ctx.send(
            f"**{target.display_name}** — {data['wins']}W / "
            f"{data['losses']}L / {data['ties']}T "
            f"({pct:.1f}% win rate over {total} games)"
        )

    @commands.command(name="rpsreset")
    async def rps_reset(self, ctx: commands.Context):
        """Wipe your RPS stats."""
        await self.config.user(ctx.author).clear()
        await ctx.send("Your RPS stats were cleared.")

    async def red_delete_data_for_user(
        self, *, requester: str, user_id: int
    ) -> None:
        await self.config.user_from_id(user_id).clear()
