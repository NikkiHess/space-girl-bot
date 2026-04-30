# my code
from src.db import driver as dbd

def set_user_voice(user_id: int, voice_name: str) -> None:
    """
    Sets a user's default voice to the specified voice name

    :param int user_id: the Discord user ID to set the voice for
    :param str voice_name: the (whitespace-included) name of this voice
    """

    voice_id = dbd.init_voice(voice_name)
    dbd.init_user_settings(user_id) # no need to use internal user ID, just makes things confusing
    
    with dbd.get_conn() as connection:
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
    
    with dbd.get_conn() as connection:
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
                   