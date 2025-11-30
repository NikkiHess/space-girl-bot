from enum import Enum

class TTSVibesVoice(Enum):
    # FOR BUG WHERE NO SWEAR WORDS ALLOWED, DUPLICATE THE LAST LETTER

    # Normal
    Marcus = "tt-en_male_narration"
    Jessie = "tt-en_us_002"
    Joey = "tt-en_us_006"
    Trevor = "tt-en_male_trevor"
    Cupid = "tt-en_male_cupid"
    Commentator = "tt-en_male_jomboy"
    Ghost_Host = "tt-en_male_ghosthost" # BUG: no swear words allowed
    Grandma = "tt-en_female_grandma"
    Lord_Cringe = "tt-en_male_ukneighbor"
    Madam_Leota = "tt-en_female_madam_leota" # BUG: no swear words allowed
    Pirate = "tt-en_male_pirate" # BUG: no swear words allowed
    Santa = "tt-en_male_santa_effect"
    Funny = "tt-en_male_funny"
    
    # IP
    Grinch = "tt-en_male_grinch"
    C3PO = "tt-en_us_c3po" # BUG: no swear words allowed
    Ghostface = "tt-en_us_ghostface"
    Rocket = "tt-en_us_rocket" # BUG: no swear words allowed
    Stitch = "tt-en_us_stitch" # BUG: no swear words allowed