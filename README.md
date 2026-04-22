# redbot-rps

Challenge-based Rock Paper Scissors cog for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot).

## Install

```
[p]load downloader
[p]repo add redbot-rps https://github.com/ep0ch-nc/redbot-rps
[p]cog install redbot-rps rps
[p]load rps
```

## Flow

1. Challenger: `[p]rps challenge @user` (or `[p]rps challenge bot` for solo testing vs fake CPU)
2. Opponent: `[p]rps accept` (auto for bot)
3. Both DM the bot: `[p]rps pick <r|p|s>`
4. Once both picked, result posts in the original channel.

## Commands

- `[p]rps challenge <@user|bot>` — start challenge
- `[p]rps accept` / `[p]rps decline` — respond to challenge
- `[p]rps cancel` — challenger cancels
- `[p]rps pick <rock|paper|scissors>` — DM only, submit pick
- `[p]rps status` — current channel game state
- `[p]rpsstats [@user]` — W/L/T record
- `[p]rpsreset` — wipe own stats

Aliases: `r`, `p`, `s`. Opponent keywords for CPU: `bot`, `cpu`, `ai`. Games auto-expire after 5 minutes.
