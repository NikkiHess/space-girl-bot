"""
Handles interactions with SQLite for the sake of managing per-server and per-user data
"""

# built-in
import os.path

# PyPi
import sqlite3

DB_PATH = os.path.join("database", "pronunication_dictionary.db")

def init_db():
    """
    Initializes the SQLite database, populating with tables if necessary
    """