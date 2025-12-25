"""
Associates all TTS Vibes voices with their API names
"""

from enum import Enum

class TTSVibesVoice(Enum):
    # FOR BUG WHERE NO SWEAR WORDS ALLOWED, DUPLICATE THE LAST LETTER

    # Normal
    Commentator = "tt-en_male_jomboy"
    Cupid = "tt-en_male_cupid"
    Funny = "tt-en_male_funny"
    Ghost_Host = "tt-en_male_ghosthost"
    Grandma = "tt-en_female_grandma"
    Jessie = "tt-en_us_002"
    Joey = "tt-en_us_006"
    Lord_Cringe = "tt-en_male_ukneighbor"
    Madam_Leota = "tt-en_female_madam_leota"
    Marcus = "tt-en_male_narration"
    Pirate = "tt-en_male_pirate"
    Santa = "tt-en_male_santa_effect"
    Trevor = "tt-en_male_trevor"

    # IP
    C3PO = "tt-en_us_c3po"
    Ghostface = "tt-en_us_ghostface"
    Grinch = "tt-en_male_grinch"
    Rocket = "tt-en_us_rocket"
    Stitch = "tt-en_us_stitch"

    # BUG: no swear words allowed. bypass.
    NO_SWEARING_LIST = [Ghost_Host, Madam_Leota, Pirate, C3PO, Rocket, Stitch]
