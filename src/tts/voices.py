"""
Associates all voices voices with their API names
"""
from enum import Enum

class TikTokVoice(Enum):
    # TODO/BUG: for voices where no swearing is allowed, just duplicate the last letter to bypass

    # Normal
    Commentator = "en_male_jomboy"
    Cupid = "en_male_cupid"
    Funny = "en_male_funny"
    Ghost_Host = "en_male_ghosthost"
    Grandma = "en_female_grandma"
    Jessie = "en_us_002"
    Joey = "en_us_006"
    UK = "en_uk_003"
    Lord_Cringe = "en_male_ukneighbor"
    Madam_Leota = "en_female_madam_leota"
    Marcus = "en_male_narration"
    Pirate = "en_male_pirate"
    Santa = "en_male_santa_effect"
    Trevor = "en_male_trevor"

    # IP
    C3PO = "en_us_c3po"
    Ghostface = "en_us_ghostface"
    Grinch = "en_male_grinch"
    Rocket = "en_us_rocket"
    Stitch = "en_us_stitch"
    Deadpool = "en_male_deadpool"

    # BUG: no swear words allowed. bypass.
    NO_SWEARING_LIST = [Ghost_Host, Madam_Leota, Pirate, C3PO, Rocket, Stitch]

