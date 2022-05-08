# material-list-bot
Discord bot for viewing Minecraft material lists

**Setup:**
- Create your discord bot at https://discord.com/developers/applications
- In OAuth URL generator select scopes messages.read, applications.commands
- In config.yml add your bot's token, your user id and server's id
- Use `pip install -r` to install requirements
- Run bot with `py main.py`

**Usage:**

To get material list right click on a message with the file and choose "Material List" in Apps.

In the bot message UI you can list view components and switch pages for big lists.

*After 3 minutes list view expire and buttons disappear, blame Discord for this*

**Extra:**

If command doesn't show up in message apps check bot scopes, or wait. It can take some time for Discord to register commands.
