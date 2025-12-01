
# built-in
import random

# pycord
import discord
from discord import AppEmoji

# my modules
from .logging_utils import timestamp_print as tsprint

APP_EMOJI_CACHE = None

async def get_app_emoji(bot: discord.Bot) -> list[AppEmoji]:
    """
    Gets a convenient list of all the bot's application emoji

    ## Args:
    - `bot` (discord.Bot): the bot (app) to list app emoji for

    ## Returns:
    - `emoji_list` (list[AppEmoji]): a list of AppEmoji objects
    """
    global APP_EMOJI_CACHE

    # just get the cache if we have it, way faster
    if APP_EMOJI_CACHE: return APP_EMOJI_CACHE

    raw = await bot._connection.http.get_all_application_emojis(bot.application_id)
    emoji_list = [bot._connection.maybe_store_app_emoji(bot.application_id, d) for d in raw["items"]]
    APP_EMOJI_CACHE = emoji_list # store list on first hit
    return emoji_list

async def get_random_app_emoji(bot: discord.Bot, search: str) -> AppEmoji:
    """
    Returns a random application emoji by search

    ## Args:
    - `bot` (discord.Bot): the bot (app) to search within
    - `search` (str): the string to search for within the emoji list

    ## Returns:
    - `random_selection` (AppEmoji): the randomly-selected AppEmoji
    """
    emoji_list = await get_app_emoji(bot)
    emoji_list = [emoji for emoji in emoji_list if search.lower() in emoji.name.lower()] # filter the list

    if len(emoji_list) > 0:
        random_selection = random.choice(emoji_list)
        return random_selection
    else:
        tsprint(f"No app emoji found containing {search} (case-insensitive)")
        return None