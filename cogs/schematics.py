import logging
from functools import partial
from os import path
import os
import glob

import nextcord
from litematica_tools import MaterialList
from nextcord.ext import commands
from nextcord.ui import Button

SUPPORTED_EXTENSIONS = [
    '.litematic',
    '.nbt',
    '.schem',
]


class MaterialListView(nextcord.ui.View):
    def __init__(self, mat_list, name,
                 *, timeout=180, blocks=True, entities=False, inventories=False):
        super().__init__(timeout=timeout)
        self.opts = {"Blocks": blocks, "Inventories": inventories, "Entities": entities}
        self.pages: list[nextcord.Embed] = []
        self.selected_page = 0

        self.name: str = mat_list.structure.metadata.name
        self.filename: str = name
        self.matl: MaterialList = mat_list

        self._set_embeds()
        self._set_toggles()
        self._set_pages()

    async def on_timeout(self):
        await self.message.edit(view=None)

    def _set_embeds(self):
        def field_len(lst: list):
            return len(max([str(i) for i in lst], key=len))

        def add_page(p: list):
            temp_pages.append(nextcord.Embed(title=self.filename,
                                             description=f"Page: {len(temp_pages) + 1}/{len(cmatl) // 50 + 1}\n"
                                                         f"Selection: {', '.join([k for k, v in self.opts.items() if v])}\n"
                                                         f"```\n{''.join(p)}\n```"))

        temp_pages = []
        cmatl = self.matl.composite_list(*self.opts.values()).sort()
        if not cmatl:
            self.pages = [nextcord.Embed(title=self.name,
                                         description="```\nNothing here, but this frog: 𓆏\n```")]
            return

        counts = list(cmatl.values())
        names = list(cmatl.names.values())
        boxes = [i[0] for i in cmatl.stacks.values()]
        stacks = [i[1] for i in cmatl.stacks.values()]
        items = [i[2] for i in cmatl.stacks.values()]

        counts_len = field_len(counts)
        names_len = field_len(names)
        boxes_len = field_len(boxes)
        stacks_len = field_len(stacks)
        items_len = field_len(items)

        _amh = 'Amount' if counts_len >= 6 else '#'
        header = f'+-{"Item":<{names_len}}-+-{_amh:>{counts_len}}-+{"SB":>{boxes_len + 1}}-{"ST":>{stacks_len + 1}}-{"IT":>{items_len + 1}}-+\n'.replace(
            ' ', '-')
        footer = f'+-{"-" * names_len}-+-{"-" * counts_len}-+-{"-" * (boxes_len + stacks_len + items_len + 4)}-+'

        page = [header]
        for n, c, b, s, i in zip(names, counts, boxes, stacks, items):
            page.append(
                f'| {n:<{names_len}} | {c:>{counts_len}} | {b:>{boxes_len}}  {s:>{stacks_len}}  {i:>{items_len}} |\n'
            )
            if len(page) == 50:
                page.append(footer)
                add_page(page)
                page = [header]
        page.append(footer)
        add_page(page)
        self.pages = temp_pages

    def _set_toggles(self):
        for k, v in self.opts.items():
            button = Button(
                label=k,
                style=self.get_toggled_style(v),
            )
            button.opt = k
            button.callback = partial(self.toggle, self, button)
            # setattr(self, callback.__name__, item) # not sure if I need this, but it's here in case everything breaks
            button._view = button
            self.children.append(button)

    def _set_pages(self):
        prev_page = Button(
            label="◀",
            style=nextcord.ButtonStyle.green,
            disabled=self.get_page_button_disabled(-1)
        )
        prev_page.modifier = -1
        prev_page.callback = partial(self.switch_page, self, prev_page)
        self.children.append(prev_page)

        next_page = Button(
            label="▶",
            style=nextcord.ButtonStyle.green,
            disabled=self.get_page_button_disabled(1)
        )
        next_page.modifier = 1
        next_page.callback = partial(self.switch_page, self, next_page)
        self.children.append(next_page)

    async def switch_page(self, _, button, interaction):
        if (self.selected_page + button.modifier) in range(len(self.pages)):
            self.selected_page += button.modifier
            button.disabled = self.get_page_button_disabled(button.modifier)
            await self.soft_update(interaction)

    async def toggle(self, _, button, interaction):
        toggle = not self.opts[button.opt]
        self.opts[button.opt] = toggle
        button.style = self.get_toggled_style(toggle)
        await self.update(interaction)

    async def soft_update(self, interaction):
        self.children[3].disabled = self.get_page_button_disabled(-1)
        self.children[4].disabled = self.get_page_button_disabled(1)
        await interaction.response.edit_message(embed=self.pages[self.selected_page], view=self)

    async def update(self, interaction):
        self._set_embeds()
        if self.selected_page >= len(self.pages):
            self.selected_page = len(self.pages) - 1
        await self.soft_update(interaction)

    # @nextcord.ui.button(label="Delete", style=nextcord.ButtonStyle.danger)
    # async def delete(self, _, interaction):
    #     await interaction.message.delete()
    #     self.stop()

    @staticmethod
    def get_toggled_style(active):
        return nextcord.ButtonStyle.primary if active else nextcord.ButtonStyle.secondary

    def get_page_button_disabled(self, modifier):
        return not (self.selected_page + modifier) in range(len(self.pages))


class Schematics(commands.Cog):
    def __init__(self, bot):
        self.LOGGER = logging.getLogger('schematics')

        self.bot = bot
        self.mat_list = None

        self.path = path.join(self.bot.CONFIG['temp_directory'], 'schematics/')
        os.makedirs(self.path, exist_ok=True)
        for file in glob.glob(self.path + '*'):
            os.remove(file)

    @nextcord.message_command(name="Material List")
    async def parse_command(self, interaction: nextcord.Interaction, message: nextcord.Message):
        for attachment in message.attachments:

            # Check file extension for compatibility
            if (ext := path.splitext(attachment.filename)[1]) in SUPPORTED_EXTENSIONS:

                # File is valid, so defer the response
                await interaction.response.defer()
                self.LOGGER.info(f'Downloading and parsing {attachment.filename}')

                # Download the file, unless we have it cached
                file = path.join(self.path, f'{message.id}{ext}')
                if path.isfile(file):
                    self.LOGGER.info('File cached, skipping download...')
                else:
                    self.LOGGER.info('Downloading...')
                    await attachment.save(file)

                # Delegate the actual parsing to litematica_tools
                self.LOGGER.info('Parsing...')
                try:
                    self.mat_list = MaterialList.from_file(file)
                except Exception as e:
                    self.LOGGER.error(f'Failed to parse {attachment.filename}')
                    self.LOGGER.exception(e)
                    await interaction.response.edit(f'Failed to parse {attachment.filename}')
                    continue

                # Create the View object and send a response
                self.LOGGER.info('Sending response...')
                view = MaterialListView(self.mat_list, attachment.filename)
                try:
                    view.message = await interaction.followup.send(
                        embed=view.pages[view.selected_page], view=view)
                except nextcord.errors.HTTPException as e:
                    self.LOGGER.exception(e)
                    await interaction.followup.send('Material list too large for discord to handle, aborted.')

                # Return if successful, breaking the for loop
                self.LOGGER.info('Done.')
                return

        # Reply with error if all attachments are invalid
        await interaction.response.send_message('This message does not contain a supported schematic.', ephemeral=True)


def setup(bot):
    bot.add_cog(Schematics(bot))
