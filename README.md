# redbot-rps

Slash-command RPS with challenges + fake CPU opponent for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot).

## Install

```
[p]load downloader
[p]repo add redbot-rps https://github.com/ep0ch-nc/redbot-rps
[p]cog install redbot-rps rps
[p]load rps
```

## Enable slash commands

Red requires the owner to enable and sync slash commands:

```
[p]slash enable rps
[p]slash enable rpsstats
[p]slash enable rpsreset
[p]slash sync
```

Global sync can take up to an hour. For instant testing, run `[p]slash sync` which syncs globally; or use `[p]slash sync <guild_id>` if Red exposes it.

## Flow

- Challenger runs `/rps challenge user:@someone` or `/rps solo` for fake CPU
- Opponent responds with `/rps accept` or `/rps decline`
- Both submit `/rps pick choice:rock|paper|scissors` (ephemeral, private)
- Reveal posts publicly in the channel

## Commands

- `/rps challenge user:@mention` — challenge a user
- `/rps solo` — challenge the fake CPU instantly
- `/rps accept` / `/rps decline` — answer challenge
- `/rps cancel` — abort own game
- `/rps pick choice:<rock|paper|scissors>` — ephemeral pick
- `/rps status` — current state
- `/rpsstats [user]` — W/L/T record
- `/rpsreset` — wipe own stats

All commands also work with prefix (`[p]rps challenge @x`). Games auto-expire after 5 minutes.
