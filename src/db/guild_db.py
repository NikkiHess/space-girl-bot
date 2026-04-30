# my code
from src.db import driver as dbd

def add_pronunciation(guild_id: int, voice_name: str, text: str, pronunciation: str) -> None:
    """
    Adds a pronunciation to the guild/voice.

    :param int guild_id: the guild ID to insert the pronunciation into, -1 will modify the bot's global dictionary
    :param str voice_name: the voice name to insert the pronunciation into, "All Voices" will modify the global voice dictionary
    :param str text: the text to pronounce differently
    :param str pronunciation: the pronunciation from that text
    """

    guild_id = dbd.init_guild(guild_id)
    voice_id = dbd.init_voice(voice_name)

    with dbd.get_conn() as connection:
        cursor = connection.cursor()
            
        cursor.execute("""
                        INSERT OR REPLACE INTO pronunciations (guild_id, voice_id, text, pronunciation)
                        VALUES (?, ?, ?, ?)
                    """, (guild_id, voice_id, text, pronunciation))
        connection.commit()

def get_pronunciation(guild_id: int, voice_name: str, text: str) -> str | None:
    """
    Retrieves the pronunciation for the text - used by a voice.

    :param int guild_id: the guild ID to get the pronunciation from, -1 will check the bot's global dictionary
    :param str voice_name: the voice name to get the pronunciation from, "All Voices" will check global voice dictionary
    :param str text: the text to retrieve the pronunciation for

    :returns str | None: the pronunciation if it exists, otherwise None
    """
    with dbd.get_conn() as connection:
        cursor = connection.cursor()
            
        cursor.execute(f"""
                        SELECT pronunciation.pronunciation
                        FROM pronunciations pronunciation
                        JOIN guilds guild ON pronunciation.guild_id = guild.id
                        JOIN voices voice ON pronunciation.voice_id = voice.id
                        WHERE guild.guild_id = ? AND voice.name = ? AND pronunciation.text = ?
                    """, (guild_id, voice_name, text))
        result = cursor.fetchone()
        return result[0] if result else None

def remove_pronunciation(guild_id: int, voice_name: str, text: str) -> bool:
    """
    Removes a pronunciation from the guild/voice.

    :param int guild_id: the guild ID to remove the pronunciation from, -1 will modify the bot's global dictionary
    :param str voice_name: the voice name to remove the pronunciation from, "All Voices" will modify global voice dictionary
    :param str text the text whose pronunciation should be removed

    :return bool: True if a pronunciation was removed, False if none existed to begin with
    """

    with dbd.get_conn() as connection:
        cursor = connection.cursor()
            
        cursor.execute("""
                        DELETE FROM pronunciations
                        WHERE guild_id = (
                            SELECT s.id FROM guilds s WHERE s.guild_id = ?
                        )
                        AND voice_id = (
                            SELECT v.id FROM voices v WHERE v.name = ?
                        )
                        AND text = ?
                    """, (guild_id, voice_name, text))

        changes = connection.total_changes
        connection.commit()

        return changes > 0

def list_pronunciations(guild_id: int, voice_name: str) -> dict[str, str]:
    """
    Removes a pronunciation pronunciation from the guild/voice.

    :param int guild_id: the guild ID to remove the pronunciation from, -1 will modify the bot's global dictionary
    :param str voice_name: the voice name to list pronunciations for, "All Voices" will modify the global voice dictionary

    :return dict[str, str]: the pronunciations found in the database
    """
    with dbd.get_conn() as connection:
        cursor = connection.cursor()

        # grab internal guild id based on the Discord guild_id
        guild_row = cursor.execute(
            f"SELECT id FROM guilds WHERE guild_id = ? LIMIT 1", (guild_id,)
        ).fetchone()
        # no guild? no pronunciations.
        if not guild_row: return {}
        # otherwise we can grab the guild id from col 0 of this row
        guild_id = guild_row[0]

        # now get the voice
        voice_row = cursor.execute(
            "SELECT id FROM voices WHERE name = ? LIMIT 1",
            (voice_name,)
        ).fetchone()
        # no voice? no pronunciations.
        if not voice_row: return {}
        # else grab voice id from row
        voice_id = voice_row[0]

        # get pronunciations as a dict
        pronunciation_rows = cursor.execute(
            """
            SELECT text, pronunciation FROM pronunciations WHERE guild_id = ? AND voice_id = ?
            """,
            (guild_id, voice_id)
        ).fetchall()

        # map and return
        return {text: pronunciation for text, pronunciation in pronunciation_rows}