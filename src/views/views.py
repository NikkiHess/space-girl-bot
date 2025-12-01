"""
Defines classes for Discord UI buttons
"""

# PyPI
import discord

# built-in
from typing import Callable

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

class PageNavView(discord.ui.View):
    """
    Displays a forward and backward button
    """

    def __init__(self, num_pages: int, build_embed_callback: Callable):
        super().__init__()
        self.current_page = 1
        self.num_pages = num_pages
        self.build_embed = build_embed_callback

    @discord.ui.button(label="←", style=discord.ButtonStyle.gray, disabled=True)
    async def backward(self, button, interaction):
        # decrement current page if we can
        if self.current_page > 1:
            self.current_page -= 1

        # after decrementing, if the current page becomes 1 we disable this button
        button.disabled = (self.current_page == 1)
        self.forward.disabled = (self.current_page == self.num_pages)

        # update the embed
        new_embed = self.build_embed(self.current_page, self.num_pages)

        # update the view, VERY necessary
        await interaction.response.edit_message(embed=new_embed, view=self)
    
    @discord.ui.button(label="→", style=discord.ButtonStyle.gray)
    async def forward(self, button, interaction):
        # increment current page if we can
        if self.current_page < self.num_pages:
            self.current_page += 1

        # after incrementing, if current page == num_pages we disable this button
        button.disabled = (self.current_page == self.num_pages)
        self.backward.disabled = (self.current_page == 1)

        # update the embed
        new_embed = self.build_embed(self.current_page, self.num_pages)

        # update the view, VERY necessary
        await interaction.response.edit_message(embed=new_embed, view=self)