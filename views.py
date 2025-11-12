"""
Defines classes for Discord UI buttons
"""

# PyPI
import discord

class ConfirmView(discord.ui.View):
    """
    Displays a yes and no button.
    """

    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji="✔️")
    async def yes(self, button, interaction):
        self.value = True
        await interaction.response.defer() # quietly acknowledge the click
        self.stop() # no longer waiting for input

    
    @discord.ui.button(label="No", style=discord.ButtonStyle.red, emoji="✖️")
    async def no(self, button, interaction):
        self.value = False
        await interaction.response.defer() # quietly acknowledge the click
        self.stop() # no longer waiting for input