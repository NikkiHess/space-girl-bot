"""
Handles interactions with SQLite for the sake of managing per-guild and per-user data
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
                            CREATE TABLE IF NOT EXISTS guilds (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id TEXT UNIQUE NOT NULL
                            );

                            CREATE TABLE IF NOT EXISTS voices (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT UNIQUE NOT NULL
                            );

                            CREATE TABLE IF NOT EXISTS pronunciations (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                guild_id INTEGER NOT NULL,
                                voice_id INTEGER NOT NULL,
                                text TEXT NOT NULL,
                                pronunciation TEXT NOT NULL,
                                FOREIGN KEY (guild_id) REFERENCES guilds (id) ON DELETE CASCADE,
                                FOREIGN KEY (voice_id) REFERENCES voices (id) ON DELETE CASCADE,
                                UNIQUE(guild_id, voice_id, text)
                            );

                            CREATE TABLE IF NOT EXISTS user_settings (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                chosen_voice_id INTEGER 
                            )
                            """)
    
def init_guild(guild_id: int) -> int:
    """
    Initializes the guild into the table if it doesn't already exist.

    :param int guild_id: the id of the guild to insert

    :return int: the database's internal ID for the guild
    """

    with get_conn() as connection:
        cursor = connection.cursor()

        cursor.execute("INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)", (guild_id,))
        cursor.execute("SELECT id FROM guilds WHERE guild_id = ?", (guild_id,))
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