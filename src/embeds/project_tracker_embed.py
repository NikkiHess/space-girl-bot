# PyPI
import discord

class ProjectTrackerEmbed(discord.Embed):
    def __init__(
        self,
        title: str,
        description: str | None = None,
        project_start: str | None = None,
        project_end: str | None = None,
        status: str | None = None,
    ):
        super().__init__(title=title, description=description)
        self.project_start = project_start
        self.project_end = project_end
        self.status = status

        # if both fields are present, combine them
        if project_start and project_end:
            self.add_field(
                name="Project Dates",
                value=f"{project_start} - {project_end}",
            )
        elif project_start:
            self.add_field(
                name="Project Dates",
                value=f"{project_start} - Present",
            )
        elif project_end:
            self.add_field(
                name="End Date",
                value=project_end,
            )