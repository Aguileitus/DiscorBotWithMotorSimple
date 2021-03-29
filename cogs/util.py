# -*- coding: utf-8 -*-
"""Utility cog"""

from discord.ext import commands

class Util(commands.Cog):
    """Utility commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Shows the latency"""
        await ctx.send(f'Pong! {round(self.bot.latency * 1000)}ms')

def setup(bot):
    """Adds cog to the bot"""
    bot.add_cog(Util(bot))
