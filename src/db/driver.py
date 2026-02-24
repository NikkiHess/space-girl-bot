"""
Handles interactions with SQLite for the sake of managing per-server and per-user data
"""

# built-in
import os.path

# PyPi
import sqlite3

DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True) # create database folder if doesn't exist
DB_PATH = os.path.join(DB_DIR, "spacegirl.db")

def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db() -> None:
    """
    Initializes the SQLite database, populating with tables if necessary
    """

    with get_conn() as connection:
        cursor = connection.cursor()

        cursor.executescript("""
                            CREATE TABLE IF NOT EXISTS servers (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id TEXT UNIQUE NOT NULL
                            );

                            CREATE TABLE IF NOT EXISTS voices (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT UNIQUE NOT NULL
                            );

                            CREATE TABLE IF NOT EXISTS translations (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                server_id INTEGER NOT NULL,
                                voice_id INTEGER NOT NULL,
                                text TEXT NOT NULL,
                                pronunciation TEXT NOT NULL,
                                FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE,
                                FOREIGN KEY (voice_id) REFERENCES voices (id) ON DELETE CASCADE,
                                UNIQUE(server_id, voice_id, text)
                            );

                            CREATE TABLE IF NOT EXISTS user_settings (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                chosen_voice_id INTEGER 
                            )
                            """)
    
def init_server(guild_id: int) -> int:
    """
    Initializes the server into the table if it doesn't already exist.

    :param int guild_id: the id of the guild/server to insert

    :return int: the database's internal ID for the server
    """

    with get_conn() as connection:
        cursor = connection.cursor()

        cursor.execute("INSERT OR IGNORE INTO servers (guild_id) VALUES (?)", (guild_id,))
        cursor.execute("SELECT id FROM servers WHERE guild_id = ?", (guild_id,))
        return cursor.fetchone()[0]

def init_voice(voice_name: str) -> int | None:
    """
    Initializes the voice into the table if it doesn't already exist.

    :param str voice_name: the name of the voice to insert into the table
    
    :return int: the database's internal ID for the new voice
    """

    with get_conn() as connection:
        cursor = connection.cursor()

        cursor.execute("INSERT OR IGNORE INTO voices (name) VALUES (?)", (voice_name,))
        cursor.execute("SELECT id FROM voices WHERE name = ?", (voice_name,))
        
        row = cursor.fetchone()
        return row[0] if row else None

def init_user_settings(user_id: int) -> int:
    """
    Initializes the user (id) into user_settings

    :param int user_id: the Discord user id to insert into the table

    :return int: the database's internal ID for the user('s settings)
    """

    with get_conn() as connection:
        cursor = connection.cursor()
        
        cursor.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
        cursor.execute("SELECT id FROM user_settings WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]

def add_pronunciation(guild_id: int, voice_name: str, text: str, pronunciation: str) -> None:
    """
    Adds a pronunciation translation to the server/voice.

    :param int guild_id: the guild ID to insert the translation into, -1 will modify the bot's global dictionary
    :param str voice_name: the voice name to insert the translation into, "All Voices" will modify the global voice dictionary
    :param str text: the text to pronounce differently
    :param str pronunciation: the pronunciation from that text
    """

    server_id = init_server(guild_id)
    voice_id = init_voice(voice_name)

    with get_conn() as connection:
        cursor = connection.cursor()
            
        cursor.execute("""
                        INSERT OR REPLACE INTO translations (server_id, voice_id, text, pronunciation)
                        VALUES (?, ?, ?, ?)
                    """, (server_id, voice_id, text, pronunciation))
        connection.commit()

def get_pronunciation(guild_id: int, voice_name: str, text: str) -> str | None:
    """
    Retrieves the translation for the text - used by a voice.

    :param int guild_id: the guild ID to get the translation from, -1 will check the bot's global dictionary
    :param str voice_name: the voice name to get the pronunciation from, "All Voices" will check global voice dictionary
    :param str text: the text to retrieve the pronunciation for

    :returns str | None: the translation if it exists, otherwise None
    """

    with get_conn() as connection:
        cursor = connection.cursor()
            
        cursor.execute(f"""
                        SELECT translation.pronunciation
                        FROM translations translation
                        JOIN servers server ON translation.server_id = server.id
                        JOIN voices voice ON translation.voice_id = voice.id
                        WHERE server.guild_id = ? AND voice.name = ? AND translation.text = ?
                    """, (guild_id, voice_name, text))
        result = cursor.fetchone()
        return result[0] if result else None

def remove_pronunciation(guild_id: int, voice_name: str, text: str) -> bool:
    """
    Removes a pronunciation translation from the server/voice.

    :param int guild_id: the guild ID to remove the translation from, -1 will modify the bot's global dictionary
    :param str voice_name: the voice name to remove the translation from, "All Voices" will modify global voice dictionary
    :param str text the text whose pronunciation should be removed

    :return bool: True if a pronunciation translation was removed, False if none existed to begin with
    """

    with get_conn() as connection:
        cursor = connection.cursor()
            
        cursor.execute("""
                        DELETE FROM translations
                        WHERE server_id = (
                            SELECT s.id FROM servers s WHERE s.guild_id = ?
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
    Removes a pronunciation translation from the server/voice.

    :param int guild_id: the guild ID to remove the translation from, -1 will modify the bot's global dictionary
    :param str voice_name: the voice name to list pronunciations for, "All Voices" will modify the global voice dictionary

    :return dict[str, str]: the pronunciations found in the database
    """

    # get the server
    # get the voice's pronunciations within that server as a dict
    # return

    with get_conn() as connection:
        cursor = connection.cursor()

        # grab server id based on guild_id
        server_row = cursor.execute(
            f"SELECT id FROM servers WHERE guild_id = ? LIMIT 1", (guild_id,)
        ).fetchone()
        # no server? no pronunciations.
        if not server_row: return {}
        # otherwise we can grab the server id from col 0 of this row
        server_id = server_row[0]

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
            SELECT text, pronunciation FROM translations WHERE server_id = ? AND voice_id = ?
            """,
            (server_id, voice_id)
        ).fetchall()

        # map and return
        return {text: pronunciation for text, pronunciation in pronunciation_rows}

def set_user_voice(user_id: int, voice_name: str) -> None:
    """
    Sets a user's default voice to the specified voice name

    :param int user_id: the Discord user ID to set the voice for
    :param str voice_name: the (whitespace-included) name of this voice
    """

    voice_id = init_voice(voice_name)
    init_user_settings(user_id) # no need to use internal user ID, just makes things confusing
    
    with get_conn() as connection:
        cursor = connection.cursor()

        cursor.execute("""
                        UPDATE user_settings
                        SET chosen_voice_id = ?
                        WHERE user_id = ?
                    """, (voice_id, user_id))
        connection.commit()

def get_user_voice(user_id: int) -> str | None:
    """
    Gets a user's default voice

    :param int user_id: the Discord user ID to get the voice for

    :return str | None: the name of the user's default voice, None if not set
    """
    
    with get_conn() as connection:
        cursor = connection.cursor()

        # get internal voice id
        cursor.execute("""
                        SELECT chosen_voice_id
                        FROM user_settings
                        WHERE user_id = ?
                    """, (user_id,))
        
        row = cursor.fetchone()

        # row could be uninitialized or voice_name could be None
        if not row or row[0] is None:
            return None
        
        # translate voice id to voice name
        cursor.execute("SELECT name FROM voices WHERE id = ?", (row[0],))
        voice = cursor.fetchone()

        # voice could be None
        return voice[0] if voice else None
                   