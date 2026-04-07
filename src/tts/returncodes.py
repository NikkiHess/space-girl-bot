from enum import Enum

class TTSReturnCode(Enum):
    NONE = -1
    OKAY = 0
    LANGUAGE_UNSUPPORTED = 3
    TEMP_UNAVAILABLE = 4

    GENERIC_ERROR = 99