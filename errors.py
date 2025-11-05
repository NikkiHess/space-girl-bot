"""
Defines errors for this particular project
"""

class OSNotSupportedError(Exception):
    def __init__(self, message="Your OS is not currently supported."):
        super().__init__(message)

class OpusNotFoundError(Exception):
    def __init__(self, message="Opus not found."):
        super().__init__(message)