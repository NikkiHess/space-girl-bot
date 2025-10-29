"""
defines errors for use within this project

Author:
Nikki Hess (nkhess@umich.edu)
"""

class CharLimitError(Exception):
    """
    a simple exception to remind users of the char limit.

    Args:
        num_chars (int): the number of characters we have
        max_chars (int): the maximum number of characters allowed
    """
    
    def __init__(self, num_chars: int, max_chars: int):
        self.message = f"The character limit is {max_chars}! You have {num_chars} characters."
        super().__init__(self.message)
        
class CharRepeatError(Exception):
    """
    a simple exception to remind users of the char limit.

    Args:
        num_chars (int): the number of characters repeated
        max_chars (int): the maximum number of repeated characters allowed
    """
    
    def __init__(self, num_char_repeat: int, max_char_repeat: int):
        self.message = f"The character repeat limit is {max_char_repeat}! You have a string of {num_char_repeat} repeating characters."
        super().__init__(self.message)