"""
Handles interactions with SQLite for the sake of managing per-server and per-user data
"""

# built-in
import os.path

# PyPi
import sqlite3

DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True) # create database folder if doesn't exist
DB_PATH = os.path.join(DB_DIR, "pronunication_dictionary.db")

CONNECTION = sqlite3.connect(DB_PATH, check_same_thread=False)
CURSOR = CONNECTION.cursor()

def init_db() -> None:
    """
    Initializes the SQLite database, populating with tables if necessary
    """

    CURSOR.executescript("""
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

    ## Args:
    - `guild_id` (int): the id of the guild/server to insert

    ## Returns:
    - the database's internal ID for the server
    """

    CURSOR.execute("INSERT OR IGNORE INTO servers (guild_id) VALUES (?)", (guild_id,))
    CURSOR.execute("SELECT id FROM servers WHERE guild_id = ?", (guild_id,))
    return CURSOR.fetchone()[0]

def init_voice(voice_name: str) -> int | None:
    """
    Initializes the voice into the table if it doesn't already exist.

    ## Args:
    - `voice_name` (int): the name of the voice to insert

    ## Returns:
    - the database's internal ID for the voice
    """

    CURSOR.execute("INSERT OR IGNORE INTO voices (name) VALUES (?)", (voice_name,))
    CURSOR.execute("SELECT id FROM voices WHERE name = ?", (voice_name,))
    
    row = CURSOR.fetchone()
    return row[0] if row else None

def init_user_settings(user_id: int) -> int:
    """
    Initializes the user (id) into user_settings

    ## Args:
    - `user_id` (int): the Discord user id to insert

    ## Returns:
    - the database's internal ID for the user (settings)
    """

    CURSOR.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
    CURSOR.execute("SELECT id FROM user_settings WHERE user_id = ?", (user_id,))
    return CURSOR.fetchone()[0]

def add_pronunciation(guild_id: int, voice_name: str, text: str, pronunciation: str) -> None:
    """
    Adds a pronunciation translation to the server/voice.

    ## Args:
    - `guild_id` (int): the guild ID to insert the translation into
    - `voice_name` (str): the voice name to insert the translation into
    - `text` (str): the text to translate
    - `pronunciation` (str): the pronunciation to translate to
    """

    server_id = init_server(guild_id)
    voice_id = init_voice(voice_name)

    CURSOR.execute("""
                       INSERT OR REPLACE INTO translations (server_id, voice_id, text, pronunciation)
                       VALUES (?, ?, ?, ?)
                   """, (server_id, voice_id, text, pronunciation))
    CONNECTION.commit()

def get_pronunciation(guild_id: int, voice_name: str, text: str) -> str:
    """
    Retrieves the translation for the text - used by a voice within a server.

    ## Args:
    - `guild_id` (int): the guild ID to get the translation from
    - `voice_name` (str): the voice name to get the translation from
    - `text` (str): the text to retrieve the translation for

    ## Returns:
    - result[0] if result else None
    """

    CURSOR.execute("""
                      SELECT translation.pronunciation
                      FROM translations translation
                      JOIN servers server ON translation.server_id = server.id
                      JOIN voices voice ON translation.voice_id = voice.id
                      WHERE server.guild_id = ? AND voice.name = ? AND translation.text = ?
                   """, (guild_id, voice_name, text))
    result = CURSOR.fetchone()
    return result[0] if result else None

def remove_pronunciation(guild_id: int, voice_name: str, text: str) -> bool:
    """
    Removes a pronunciation translation from the server/voice.

    ## Args:
    - `guild_id` (int): the guild ID to remove the translation from
    - `voice_name` (str): the voice name to remove the translation from
    - `text` (str): the text whose translation should be removed

    ## Returns:
    - True if a translation was removed, False if none existed
    """

    CURSOR.execute("""
                      DELETE FROM translations
                      WHERE server_id = (
                          SELECT s.id FROM servers s WHERE s.guild_id = ?
                      )
                      AND voice_id = (
                          SELECT v.id FROM voices v WHERE v.name = ?
                      )
                      AND text = ?
                   """, (guild_id, voice_name, text))

    changes = CONNECTION.total_changes
    CONNECTION.commit()

    return changes > 0

def list_pronunciations(guild_id: int, voice_name: str) -> dict[str, str]:
    """
    Removes a pronunciation translation from the server/voice.

    ## Args:
    - `guild_id` (int): the guild ID to remove the translation from
    - `voice_name` (str): the voice name to list pronunciations for

    ## Returns:
    - `dictionary` (dict[str, str]): the pronunciations found in the db
    """

    # get the server
    # get the voice's pronunciations within that server as a dict
    # return

    # grab server id based on guild_id
    server_row = CURSOR.execute(
        f"SELECT id FROM servers WHERE guild_id = ? LIMIT 1", (guild_id,)
    ).fetchone()
    # no server? no pronunciations.
    if not server_row: return {}
    # otherwise we can grab the server id from col 0 of this row
    server_id = server_row[0]

    # now get the voice
    voice_row = CURSOR.execute(
        "SELECT id FROM voices WHERE name = ? LIMIT 1",
        (voice_name,)
    ).fetchone()
    # no voice? no pronunciations.
    if not voice_row: return {}
    # else grab voice id from row
    voice_id = voice_row[0]

    # get pronunciations as a dict
    pronunciation_rows = CURSOR.execute(
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

    ## Args:
    - `user_id` (int): the Discord user ID to set the voice for
    - `voice_name` (str): the (external, no underscores) name of the voice
    """

    voice_id = init_voice(voice_name)
    init_user_settings(user_id) # no need to use internal user ID, just makes things confusing

    CURSOR.execute("""
                      UPDATE user_settings
                      SET chosen_voice_id = ?
                      WHERE user_id = ?
                   """, (voice_id, user_id))
    CONNECTION.commit()

def get_user_voice(user_id: int) -> str | None:
    """
    Gets a user's default voice

    ## Args:
    - `user_id` (int): the Discord user ID to get the default voice for

    ## Returns:
    - `voice_name` (str | None): the name of the user's default voice (could be nothing)
    """

    # get internal voice id
    CURSOR.execute("""
                      SELECT chosen_voice_id
                      FROM user_settings
                      WHERE user_id = ?
                   """, (user_id,))
    
    row = CURSOR.fetchone()

    # row could be uninitialized or voice_name could be None
    if not row or row[0] is None:
        return None
    
    # translate voice id to voice name
    CURSOR.execute("SELECT name FROM voices WHERE id = ?", (row[0],))
    voice = CURSOR.fetchone()

    # voice could be None
    return voice[0] if voice else None
                   