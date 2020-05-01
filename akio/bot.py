import traceback

import discord

from .command import Command, CommandResult, CommandResultType


class Bot(discord.Client):
    def __init__(self, print_command_errors=True, *, loop=None, **discord_py_options):
        ''' Bot framework using discord.py '''
        super().__init__(loop=loop, **discord_py_options)
        self.print_command_errors = print_command_errors

        self.commands = {}

    def command(self, coroutine):
        '''
        Decorator for registering commands. Coroutines must have a `message` parameter,
        followed by any number of command parameters.

        An example:
        ```
        @bot.command
        async def my_command(message: discord.Message, thing1, thing2):
            await bot.do_something_with(thing1, thing2)
        '''
        self.commands[coroutine.__name__] = Command(coroutine.__name__, coroutine)
        return coroutine

    async def invoke(self, prefix: str, quote_delimiter: str, message: discord.Message) -> CommandResult:
        '''
        |coro|

        Invokes a command. You should call this coroutine in `Bot.on_message` or any events you override.

        `CommandResult.command` will be `None` if `CommandResult.type` is either `NotACommand` or `UnknownCommand`.

        In all other cases the `Command` attribute will be available.

        Here is an example command result handler:

        ```
        async def on_message(self, message: discord.Message):
            result = await self.invoke('b.', '"', message)
            if result.type in {ResultType.NotEnoughArguments, ResultType.InvalidArgument}:
                await message.channel.send(some_usage_string_for(result.command))
            elif result.type is ResultType.CommandError:
                await send_error_to_owner(result.command, result.message_content)
        ```
        '''

        message_content: str = message.system_content

        if not message_content.startswith(prefix):
            return CommandResult(None, CommandResultType.NotACommand, message_content)

        _tokens_then_quoted = iter(message_content.split(quote_delimiter))
        _initial_tokens = next(_tokens_then_quoted).split()

        try:
            command: Command = self.commands[_initial_tokens[0][len(prefix):]]
        except KeyError:
            return CommandResult(None, CommandResultType.UnknownCommand, message_content)

        arguments = _initial_tokens[1:]
        try:
            for quote in _tokens_then_quoted:
                arguments.append(quote)
                arguments += next(_tokens_then_quoted).split()
        except StopIteration:
            pass

        if len(arguments) < command.number_of_required_parameters:
            return CommandResult(command, CommandResultType.NotEnoughArguments, message_content)

        try:
            bound_arguments = command.bound_arguments(arguments)
        except (TypeError, ValueError):
            return CommandResult(command, CommandResultType.InvalidArgument, message_content)

        try:
            await command.coro(message, *bound_arguments)
            return CommandResult(command, CommandResultType.Success, message_content)
        except Exception:
            if self.print_command_errors:
                traceback.print_exc()
            return CommandResult(command, CommandResultType.CommandError, message_content)
