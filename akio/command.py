import enum
import inspect
from asyncio import iscoroutinefunction


class Command:
    def __init__(self, name: str, coroutine):
        if not iscoroutinefunction(coroutine):
            raise TypeError("command registered must be a coroutine function")

        self.name = name
        self.coro = coroutine

        parameters_mapping = inspect.signature(coroutine).parameters
        parameters = parameters_mapping.values()
        parameters_iterator = iter(parameters)

        try:
            message_parameter = parameters_mapping['message']
            if next(parameters_iterator) is not message_parameter:
                raise ValueError('message must be the first parameter in the command definition')
        except KeyError:
            raise ValueError('missing required message parameter in command definition')

        # self.parameters won't contain the message parameter
        self.parameters = list(parameters)[1:]
        self.number_of_required_parameters = 0

        # count required parameters
        try:
            while next(parameters_iterator).default is inspect.Parameter.empty:
                self.number_of_required_parameters += 1
        except StopIteration:
            pass

        self.usage = " ".join(p.name if p.default is inspect.Parameter.empty else f'{p.name}:{p.default}' for p in self.parameters)

        self.docstring = inspect.getdoc(coroutine)
        self.description = inspect.cleandoc(self.docstring) if self.docstring is not None else f'Command `{name}` has no description :('

    def bound_arguments(self, arguments: list) -> list:
        return [a if p.annotation is inspect.Parameter.empty else p.annotation(a) for p, a in zip(self.parameters, arguments)]


class CommandResult:
    def __init__(self, command: Command, type: ResultType, message_content: str):
        self.command = command
        self.type = type
        self.message_content = message_content


class CommandResultType(enum.Enum):
    Success = 0
    NotACommand = enum.auto()
    UnknownCommand = enum.auto()
    NotEnoughArguments = enum.auto()
    InvalidArgument = enum.auto()
    CommandError = enum.auto()
