# -*- coding: utf-8 -*-

"""Gacha Cog"""

import asyncio
import random
import sys
import traceback
from datetime import datetime, timedelta

import discord
from discord.ext import commands

class Gacha(commands.Cog):
    """Gacha Commands"""

    COINS_DATA = {
        "blue": {
            "emoji": ":blue_circle:",
            "value": 1
        },
        "green": {
            "emoji": ":green_circle:",
            "value": 2
        },
        "yellow": {
            "emoji": ":yellow_circle:",
            "value": 5
        },
        "orange": {
            "emoji": ":orange_circle:",
            "value": 10
        },
        "red": {
            "emoji": ":red_circle:",
            "value": 25
        }
    }
    COINS_LIST = ["blue", "green", "yellow", "orange", "red"]

    X_EMOJI = ":x:"
    CHECKMARK_EMOJI = ":white_check_mark:"

    HOUR_LIMIT_POINTS = 50

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.users_collection = self.bot.db['users']

    async def get_random_coin(self) -> tuple[str, dict]:
        """Returns a random color"""
        num = random.randint(1, 100)

        if 0 < num <= 50:
            name = 'blue'
        elif 50 < num <= 75:
            name = 'green'
        elif 75 < num <= 90:
            name = 'yellow'
        elif 90 < num <= 98:
            name = 'orange'
        else: #if 98 < num <= 100:
            name = 'red'

        return name, self.COINS_DATA[name]

    @commands.command()
    async def coins(self, ctx: commands.Context):
        """Shows the value of the coins"""
        message = ""

        for coin_name in self.COINS_LIST:
            coin = self.COINS_DATA[coin_name]
            message += f"{coin['emoji']} = {coin['value']} points\n"

        await ctx.send(message)

    @staticmethod
    def get_empty_coins_dict():
        """Returns a dictionary with all the coins with quantity of 0 (Zero)"""
        return {
            "blue": 0,
            "green": 0,
            "yellow": 0,
            "orange": 0,
            "red": 0
        }

    @staticmethod
    async def get_next_reset() -> datetime:
        """Returns the datetime of the next roll reset
        Reset occurs hourly at xx:00 UTC"""
        now = datetime.utcnow()
        now += timedelta(hours=1)
        return now.replace(minute=0, second=0, microsecond=0)

    async def create_empty_user(self, _id: int) -> dict:
        """Creates a new empty user in the database"""
        coins = self.get_empty_coins_dict()
        user = {
            '_id': _id,
            'coins_rolled': coins,
            'points': 0,
            'current_cap': 0,
            'next_reset': await self.get_next_reset()
        }
        await self.users_collection.insert_one(user)

        return user

    @commands.command()
    async def roll(self, ctx: commands.Context):
        """Rolls the gacha"""
        message = ""
        points_won = 0
        coins_rolled = {}

        user = await self.users_collection.find_one({'_id': ctx.author.id})
        # If user exists in the DB, validate and update next_reset and cap accordingly
        if user:
            # If reset already passed, calculate new values
            if datetime.utcnow() >= user['next_reset']:
                user['next_reset'] = await self.get_next_reset()
                user['current_cap'] = 0

            if user['current_cap'] >= self.HOUR_LIMIT_POINTS:
                await ctx.send("You can't earn more points for now! Wait for next reset.")
                return
        # If user does not exist, create a new entry in the DB
        else:
            user = await self.create_empty_user(ctx.author.id)

        # 3/4 of the rolls should be an assured won
        assured_coin = await self.get_random_coin()
        assured_loop = random.randint(0, 3)

        for i in range(3):
            coins = []
            diff_coins = set()
            for _ in range(3):
                name, coin = (assured_coin if i == assured_loop else await self.get_random_coin())
                coins.append(coin)
                diff_coins.add(coin["value"])
                message += coin["emoji"] + " "

            if len(diff_coins) == 1:
                points_won += coin['value']
                message += " " + self.CHECKMARK_EMOJI
                coins_rolled.setdefault(name, 0)
                coins_rolled[name] += 1
            else:
                message += " " + self.X_EMOJI
            message += "\n"

        if points_won == 0:
            message += "\nTry again!"
        else:
            total_points = user['points'] + points_won

            for coin_name, rolls in coins_rolled.items():
                user['coins_rolled'][coin_name] += rolls

            await self.users_collection.update_one(
                {'_id': ctx.author.id},
                {
                    "$set": {
                        'coins_rolled': user['coins_rolled'],
                        'points': total_points,
                        'current_cap': user['current_cap'] + points_won,
                        'next_reset': user['next_reset']
                    }
                }
            )

            message += f"\nCongratulations, you won {points_won} points! Total: {total_points}"

        await ctx.send(message)

    @commands.command()
    async def profile(self, ctx: commands.Context, *, member: discord.Member=None):
        """Shows your profile"""
        user = member if member else ctx.author

        embed = discord.Embed(color=0x009999)
        embed.set_author(name=str(user), icon_url=user.avatar_url)

        db_user = await self.bot.db['users'].find_one({'_id': user.id})

        # Get points
        if db_user:
            coins = db_user['coins_rolled']
            points = db_user['points']
        else:
            coins = self.get_empty_coins_dict()
            points = 0

        coins_value = ""
        for coin_name in self.COINS_LIST:
            coins_value += f"{self.COINS_DATA[coin_name]['emoji']}x{coins[coin_name]} "

        embed.add_field(name="Coins Rolled", value=coins_value)
        embed.add_field(name="Points", value=points)

        #Sends the embed
        await ctx.send(embed=embed)

    @profile.error
    async def profile_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handling for profile command"""
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("I could not find that member...")

    #async def give_points(session, points, giver, receiver):
    async def give_points(self, points: int, giver: discord.Member, receiver: discord.Member):
        """Updates the points of the giver and the receiver in the DB"""
        #users_collection = session.client.db['users']
        giver_doc = await self.users_collection.find_one({'_id': giver.id})
        await self.users_collection.update_one(
            {'_id': giver_doc['_id']},
            {
                "$set": {
                    'points': giver_doc['points'] - points
                }
            }
            #, session = session
        )

        receiver_doc = await self.users_collection.find_one({'_id': receiver.id})
        if not receiver_doc:
            receiver_doc = await self.create_empty_user(receiver.id)

        await self.users_collection.update_one(
            {'_id': receiver_doc['_id']},
            {
                "$set": {
                    'points': receiver_doc['points'] + points
                }
            }
            #, session = session
        )

    @commands.command()
    async def give(self, ctx: commands.Context, points: int, member: discord.Member):
        """Gives points to a member"""

        if member.bot:
            await ctx.send("Bots do not play!")
            return
        if ctx.author == member:
            await ctx.send("Why would you give points to yourself?")
            return
        if points <= 0:
            await ctx.send("Maybe try something greater than zero?")
            return

        giver = await self.users_collection.find_one({'_id': ctx.author.id})
        if not giver or (giver['points'] < points):
            await ctx.send("You don't have enough points!")
            return

        def input_check(msg: discord.Message):
            if ctx.author != msg.author:
                return False
            if ctx.channel != msg.channel:
                return False
            if msg.content.lower() in ['y', 'n', 'yes', 'no']:
                return True
            return False

        await ctx.send(f"Are you sure you want to give {points} points to {str(member)}? "
                        "(y/n/yes/no)")

        try:
            user_input = await self.bot.wait_for('message', check=input_check, timeout=10.0)
            user_input = user_input.content.lower()
            if user_input in ['y', 'yes']:
                await self.give_points(points, ctx.author, member)

                # Transaction
                #async with await self.bot.client.start_session() as session:
                #    await session.with_transaction(
                #        lambda s: update_points(s, points, giver, receiver)
                #    )

                await ctx.send(f"{ctx.author.mention} just gave {points} points "
                               f"to {member.mention}")
            elif user_input in ['n', 'no']:
                await ctx.send("Oh, you changed your mind. Ok.")
            else:
                await ctx.send("Invalid answer, try again!")

        except asyncio.TimeoutError:
            return await ctx.send('Took too long. Maybe another time?')

    @give.error
    async def give_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handling for give command"""
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("I could not find that member...")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send(f"Number of points must be a integer number.\n"
                           f"Syntax: {ctx.prefix}give <points> <member>")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        else:
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(error.__traceback__)
            print(f'{error.__class__.__name__}: {error}', file=sys.stderr)

def setup(bot: commands.Bot):
    """Adds cog to the bot"""
    bot.add_cog(Gacha(bot))
