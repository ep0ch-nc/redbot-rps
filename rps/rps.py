import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional

import discord
from discord import app_commands
from redbot.core import Config, commands
from redbot.core.bot import Red

CHOICES = ("rock", "paper", "scissors")
PickChoice = Literal["rock", "paper", "scissors"]
EMOJI = {"rock": "\U0001FAA8", "paper": "\U0001F4C4", "scissors": "✂️"}
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
BOT_ID = 0
BOT_NAME = "CPU"
GAME_TIMEOUT = 300


def decide(a: str, b: str) -> str:
    if a == b:
        return "tie"
    return "a" if BEATS[a] == b else "b"


@dataclass
class Game:
    channel_id: int
    challenger_id: int
    opponent_id: int
    state: str = "pending"
    picks: Dict[int, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    challenger_name: str = ""
    opponent_name: str = ""

    @property
    def vs_bot(self) -> bool:
        return self.opponent_id == BOT_ID

    def both_picked(self) -> bool:
        if self.vs_bot:
            return self.challenger_id in self.picks
        return self.challenger_id in self.picks and self.opponent_id in self.picks


class RPS(commands.Cog):
    """Slash-based Rock Paper Scissors with challenges."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0x52505303, force_registration=True
        )
        self.config.register_user(wins=0, losses=0, ties=0)
        self.games: Dict[int, Game] = {}
        self.player_channel: Dict[int, int] = {}
        self._timeout_tasks: Dict[int, asyncio.Task] = {}

    def cog_unload(self) -> None:
        for task in self._timeout_tasks.values():
            task.cancel()

    def _remove_game(self, game: Game) -> None:
        self.games.pop(game.channel_id, None)
        self.player_channel.pop(game.challenger_id, None)
        if not game.vs_bot:
            self.player_channel.pop(game.opponent_id, None)
        task = self._timeout_tasks.pop(game.channel_id, None)
        if task:
            task.cancel()

    def _get_game_for_user(self, user_id: int) -> Optional[Game]:
        channel_id = self.player_channel.get(user_id)
        if channel_id is None:
            return None
        return self.games.get(channel_id)

    async def _record(self, user_id: int, outcome: str) -> None:
        if user_id == BOT_ID:
            return
        key = {"win": "wins", "loss": "losses", "tie": "ties"}[outcome]
        async with self.config.user_from_id(user_id).all() as data:
            data[key] = data.get(key, 0) + 1

    async def _timeout_watcher(self, game: Game) -> None:
        try:
            await asyncio.sleep(GAME_TIMEOUT)
        except asyncio.CancelledError:
            return
        if self.games.get(game.channel_id) is not game or game.state == "done":
            return
        self._remove_game(game)
        channel = self.bot.get_channel(game.channel_id)
        if channel:
            try:
                await channel.send("RPS game timed out.")
            except discord.HTTPException:
                pass

    def _start_timer(self, game: Game) -> None:
        task = asyncio.create_task(self._timeout_watcher(game))
        self._timeout_tasks[game.channel_id] = task

    @commands.hybrid_group(name="rps", invoke_without_command=True)
    async def rps(self, ctx: commands.Context):
        """Rock Paper Scissors. Subcommands: challenge, solo, accept, decline, cancel, pick, status."""
        await ctx.send_help()

    @rps.command(name="challenge")
    @app_commands.describe(user="The user you want to challenge.")
    @commands.guild_only()
    async def rps_challenge(self, ctx: commands.Context, user: discord.Member):
        """Challenge another user to RPS."""
        if user.bot:
            await ctx.send(
                "Can't challenge real bots. Use `/rps solo` to play the fake CPU.",
                ephemeral=True,
            )
            return
        if user.id == ctx.author.id:
            await ctx.send(
                "Can't challenge yourself. Use `/rps solo` for solo play.",
                ephemeral=True,
            )
            return
        await self._start_game(ctx, user)

    @rps.command(name="solo")
    @commands.guild_only()
    async def rps_solo(self, ctx: commands.Context):
        """Start a solo game against the fake CPU opponent."""
        await self._start_game(ctx, None)

    async def _start_game(
        self, ctx: commands.Context, opponent: Optional[discord.Member]
    ) -> None:
        if ctx.channel.id in self.games:
            await ctx.send(
                "A game is already active in this channel.",
                ephemeral=True,
            )
            return
        if ctx.author.id in self.player_channel:
            await ctx.send(
                "You already have an active game elsewhere.", ephemeral=True
            )
            return
        if opponent is not None and opponent.id in self.player_channel:
            await ctx.send(
                f"{opponent.display_name} is already in a game.",
                ephemeral=True,
            )
            return

        vs_bot = opponent is None
        opp_id = BOT_ID if vs_bot else opponent.id
        opp_name = BOT_NAME if vs_bot else opponent.display_name

        game = Game(
            channel_id=ctx.channel.id,
            challenger_id=ctx.author.id,
            opponent_id=opp_id,
            state="picking" if vs_bot else "pending",
            challenger_name=ctx.author.display_name,
            opponent_name=opp_name,
        )
        self.games[ctx.channel.id] = game
        self.player_channel[ctx.author.id] = ctx.channel.id
        if not vs_bot:
            self.player_channel[opp_id] = ctx.channel.id

        if vs_bot:
            game.picks[BOT_ID] = random.choice(CHOICES)
            await ctx.send(
                f"**RPS:** {ctx.author.mention} vs **{BOT_NAME}**\n"
                f"CPU locked its pick. Run `/rps pick` to play."
            )
        else:
            await ctx.send(
                f"**RPS Challenge:** {ctx.author.mention} challenges {opponent.mention}.\n"
                f"{opponent.mention} respond with `/rps accept` or `/rps decline` within 5 minutes."
            )
        self._start_timer(game)

    @rps.command(name="accept")
    @commands.guild_only()
    async def rps_accept(self, ctx: commands.Context):
        """Accept a challenge targeting you in this channel."""
        game = self.games.get(ctx.channel.id)
        if (
            not game
            or game.state != "pending"
            or game.opponent_id != ctx.author.id
        ):
            await ctx.send(
                "No challenge for you to accept here.", ephemeral=True
            )
            return
        game.state = "picking"
        await ctx.send(
            "Challenge accepted. Both players run `/rps pick` to submit privately."
        )

    @rps.command(name="decline")
    @commands.guild_only()
    async def rps_decline(self, ctx: commands.Context):
        """Decline a pending challenge targeting you."""
        game = self.games.get(ctx.channel.id)
        if (
            not game
            or game.state != "pending"
            or game.opponent_id != ctx.author.id
        ):
            await ctx.send(
                "No challenge for you to decline here.", ephemeral=True
            )
            return
        self._remove_game(game)
        await ctx.send(f"{ctx.author.display_name} declined the challenge.")

    @rps.command(name="cancel")
    async def rps_cancel(self, ctx: commands.Context):
        """Challenger cancels their current game."""
        game = self._get_game_for_user(ctx.author.id)
        if not game or game.challenger_id != ctx.author.id:
            await ctx.send("You have no game to cancel.", ephemeral=True)
            return
        self._remove_game(game)
        await ctx.send("Game canceled.")

    @rps.command(name="pick")
    @app_commands.describe(choice="Your pick.")
    async def rps_pick(self, ctx: commands.Context, choice: PickChoice):
        """Submit your pick. Response is private."""
        game = self._get_game_for_user(ctx.author.id)
        if not game:
            await ctx.send("You have no active RPS game.", ephemeral=True)
            return
        if game.state != "picking":
            await ctx.send(
                "Game is not in picking state yet.", ephemeral=True
            )
            return
        if ctx.author.id in game.picks:
            await ctx.send(
                "You already picked. Wait for opponent.", ephemeral=True
            )
            return

        # Prefix in guild: delete the user's message so opponent can't see it.
        if ctx.interaction is None and ctx.guild is not None:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass

        game.picks[ctx.author.id] = choice

        reply = f"Locked in: **{choice}** {EMOJI[choice]}"
        if ctx.interaction is not None:
            await ctx.send(reply, ephemeral=True)
        else:
            try:
                await ctx.author.send(reply)
            except discord.Forbidden:
                pass

        if game.both_picked():
            await self._reveal(game)

    async def _reveal(self, game: Game) -> None:
        game.state = "done"
        channel = self.bot.get_channel(game.channel_id)
        if channel is None:
            self._remove_game(game)
            return

        a_id, b_id = game.challenger_id, game.opponent_id
        a_pick, b_pick = game.picks[a_id], game.picks[b_id]
        a_name, b_name = game.challenger_name, game.opponent_name

        winner = decide(a_pick, b_pick)
        if winner == "tie":
            result = "**Tie!**"
            await self._record(a_id, "tie")
            if not game.vs_bot:
                await self._record(b_id, "tie")
        elif winner == "a":
            result = f"**{a_name} wins!**"
            await self._record(a_id, "win")
            if not game.vs_bot:
                await self._record(b_id, "loss")
        else:
            result = f"**{b_name} wins!**"
            await self._record(a_id, "loss")
            if not game.vs_bot:
                await self._record(b_id, "win")

        try:
            await channel.send(
                f"**RPS Reveal:**\n"
                f"{EMOJI[a_pick]} {a_name}: **{a_pick}**\n"
                f"{EMOJI[b_pick]} {b_name}: **{b_pick}**\n"
                f"{result}"
            )
        except discord.HTTPException:
            pass
        self._remove_game(game)

    @rps.command(name="status")
    async def rps_status(self, ctx: commands.Context):
        """Show current game state in this channel, or your game if running."""
        game = None
        if ctx.guild is not None:
            game = self.games.get(ctx.channel.id)
        if game is None:
            game = self._get_game_for_user(ctx.author.id)
        if not game:
            await ctx.send("No active game.", ephemeral=True)
            return
        picked = []
        if game.challenger_id in game.picks:
            picked.append(game.challenger_name)
        if game.opponent_id in game.picks:
            picked.append(game.opponent_name)
        elapsed = int(time.time() - game.created_at)
        await ctx.send(
            f"State: **{game.state}** | {game.challenger_name} vs {game.opponent_name}\n"
            f"Picked: {', '.join(picked) if picked else 'nobody'} | "
            f"elapsed {elapsed}s / {GAME_TIMEOUT}s",
            ephemeral=True,
        )

    @commands.hybrid_command(name="rpsstats")
    @app_commands.describe(user="User to look up (defaults to yourself).")
    async def rps_stats(
        self,
        ctx: commands.Context,
        user: Optional[discord.Member] = None,
    ):
        """Show RPS stats."""
        target = user or ctx.author
        data = await self.config.user(target).all()
        total = data["wins"] + data["losses"] + data["ties"]
        if total == 0:
            await ctx.send(
                f"{target.display_name} has not played yet.", ephemeral=True
            )
            return
        pct = data["wins"] / total * 100
        await ctx.send(
            f"**{target.display_name}** — {data['wins']}W / "
            f"{data['losses']}L / {data['ties']}T "
            f"({pct:.1f}% win rate over {total} games)"
        )

    @commands.hybrid_command(name="rpsreset")
    async def rps_reset(self, ctx: commands.Context):
        """Wipe your RPS stats."""
        await self.config.user(ctx.author).clear()
        await ctx.send("Your RPS stats were cleared.", ephemeral=True)

    async def red_delete_data_for_user(
        self, *, requester: str, user_id: int
    ) -> None:
        await self.config.user_from_id(user_id).clear()
