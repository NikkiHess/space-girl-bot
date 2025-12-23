from enum import Enum

class TTSReturnCode(Enum):
    NONE = -1
    OKAY = 0
    TOO_LONG = 1
    TOO_MANY_REPEAT_CHARS = 2
    LANGUAGE_UNSUPPORTED = 3

    GENERIC_TTSVIBES_ERROR = 99