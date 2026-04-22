from .rps import RPS


async def setup(bot):
    await bot.add_cog(RPS(bot))
