import datetime as dt
from enum import Enum
from typing import Callable, Iterable, Optional, ParamSpec, TypeVar
import uuid
from zoneinfo import ZoneInfo
import click
from click import echo, group, argument, option
from dataclasses import dataclass, fields, field
from pathlib import Path
from pickle import load, dump
import pytz
import tkinter as tk
from platformdirs import user_data_dir
from dipgm.models.option_spec import OptionSpec
from dipgm.models.phase import CurrentPhase, PhaseType
from dipgm.models.scheduled_command import ScheduledCommand
from models.param_types import TIMEDELTA


@dataclass
class GameConfigDefaults:
    adju_time: str = "14:00"
    adju_tz: str = "America/Los_Angeles"
    move_length: dt.timedelta = dt.timedelta(days=2)
    retreat_length: dt.timedelta = dt.timedelta(days=1)
    adjustment_length: dt.timedelta = dt.timedelta(days=1)
    scheduled_commands: list[ScheduledCommand] = []

@dataclass
class GameConfigUpdates:
    adju_time: Optional[str]
    adju_tz: Optional[str]
    move_length: Optional[dt.timedelta]
    retreat_length: Optional[dt.timedelta]
    adjustment_length: Optional[dt.timedelta]
    scheduled_commands: list[ScheduledCommand]

class Game(GameConfigDefaults):
    name: str
    def __init__(
        self,
        name: str,
    ):
        self.name = name

    def apply_updates(self, updates: GameConfigUpdates):
        for field_ in fields(updates):
            if field_.name == 'scheduled_commands':
                continue
            value = getattr(updates, field_.name)
            if value is not None:
                setattr(self, field_.name, value)
        if updates.scheduled_commands is not None:
            self.scheduled_commands.extend(updates.scheduled_commands)
            self.scheduled_commands.sort(key=lambda command: command.offset)

@dataclass
class Data:
    games: dict[str, Game] = field(default_factory=dict)
    nicknames: dict[str, str] = field(default_factory=dict)

    def get_game(self, name: str) -> Game:
        if name not in self.games:
            if name in self.nicknames:
                name = self.nicknames[name]
            else:
                raise ValueError(f"No game called {name}")
        return self.games[name]

APP_NAME = "dipgm"
DATA_DIR = Path(user_data_dir(APP_NAME))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "data.pickle"


def initialize_data(path: Path):
    data = Data()
    with open(path, 'wb') as f:
        dump(data, f)
    return data

def load_data() -> Data:
    path = DATA_FILE
    try:
        with open(path, 'rb') as f:
            data = load(f)
        return data
    except FileNotFoundError:
        return initialize_data(path)
    except EOFError:
        return initialize_data(path)

def save_data(data: Data):
    path = DATA_FILE
    with open(path, 'wb') as f:
        dump(data, f)

def time_is_valid(time: str) -> bool:
    try:
        h, m = map(int, time.split(':'))
        if any(59 < t or 0 > t for t in (h, m)):
            return False
        return True
    except:
        echo(f"Invalid time: {time}")
        return False
    
def tz_is_valid(tz: str) -> bool:
    return tz in pytz.all_timezones


ARGUMENT_HELP_STRINGS = {
    "adju-time": "Adjudication time of day, in 24 hour time (e.g. -t 16:00)",
    "timezone": "Time zone for adjudication time, from tz time zones (e.g. -z America/Los Angeles)",
    "phase-lengths": "Phase lengths (moves, retreats, adjustments)",
    "nicknames": "List of alternate names which can be invoked to refer to this game",
    "name": "Full name or nickname of game to ",
    "scheduled-commands": """Commands to run automatically each phase in time-before-next-adjudication-to-run and command text (e.g. 12:00 "v m b f" to run `v m b f` 12h before adjudication)""",
    "time-delta-format": """\n\tEnter time values in formats like "12:00" or "12h30m" """
}


@group()
def cli():
    pass

GAME_UPDATE_OPTIONS: list[OptionSpec] = [
    OptionSpec(
        "adju_time",
        option('--adju-time', '-t', help=ARGUMENT_HELP_STRINGS["adju-time"])
    ),
    OptionSpec(
        "timezone",
        option('--timezone', '-z', help=ARGUMENT_HELP_STRINGS["timezone"])
    ),
    OptionSpec(
        "phase-lengths",
        option('--phase-lengths', '-p', nargs=3, type=tuple[TIMEDELTA, TIMEDELTA, TIMEDELTA], help=ARGUMENT_HELP_STRINGS['phase-lengths'] + ARGUMENT_HELP_STRINGS['time-delta-format'])
    ),
    OptionSpec(
        "nicknames",
        option('--nicknames', '-n', multiple=True, help=ARGUMENT_HELP_STRINGS['nicknames'])
    ),
    OptionSpec(
        "scheduled-commands",
        option(
            '--scheduled-commands', '-s',
            multiple=True,
            type=tuple[TIMEDELTA, str],
            help=ARGUMENT_HELP_STRINGS['scheduled-commands'] + ARGUMENT_HELP_STRINGS['time-delta-format'])
    ),
]

def apply_options(option_specs: Iterable[OptionSpec]) -> Callable[[Callable], Callable]:
    """Decorator to apply a list of decorators to the function"""
    def decorator(f: Callable) -> Callable:
        for spec in reversed(list(option_specs)):
            f = spec.click_decorator(f)
        return f
    return decorator

def process_and_apply_game_updates(
    game: Game,
    adju_time: Optional[str] = None,
    adju_tz: Optional[str] = None,
    phase_lengths: Optional[tuple[dt.timedelta, dt.timedelta, dt.timedelta]] = None,
    nicknames: Optional[list[str]] = None,
    scheduled_commands: Optional[tuple[tuple[dt.timedelta, str], ...]] = None
):

    if nicknames is not None:
        set_nicknames(nicknames)
        

    move_length, retreat_length, adjustment_length = phase_lengths if phase_lengths is not None else (None, None, None)

    commands = []
    if scheduled_commands is not None:
        for offset, command in scheduled_commands:
            commands.append((offset, command, uuid.uuid1()))

    game.apply_updates(GameConfigUpdates(
        adju_time=adju_time,
        adju_tz=adju_tz,
        move_length=move_length,
        retreat_length=retreat_length,
        adjustment_length=adjustment_length,
        scheduled_commands=commands,
    ))


@cli.command()
@argument('name', help="Full name of game")
@apply_options(GAME_UPDATE_OPTIONS)
def create_game(
    name: str,
    adju_time: Optional[str] = None,
    adju_tz: Optional[str] = None,
    phase_lengths: Optional[tuple[dt.timedelta, dt.timedelta, dt.timedelta]] = None,
    nicknames: Optional[list[str]] = None,
    scheduled_commands: Optional[tuple[tuple[dt.timedelta, str], ...]] = None
):
    data = load_data()
    if name in data.games:
        echo(f"Game {name} already exists")
        return

    game = Game(name)
    process_and_apply_game_updates(game, adju_time, adju_tz, phase_lengths,nicknames, scheduled_commands)
    data.games[name] = game

    save_data(data)


@cli.command()
@argument('name', help=ARGUMENT_HELP_STRINGS["name"] + "delete")
def delete_game(name: str):
    data = load_data()
    try:
        del data.games[name]
        echo(f"Deleted game {name}")
        nns_to_remove = []
        for nickname, full_name in data.nicknames.items():
            if full_name == name:
                nns_to_remove.append(nickname)
        for nn in nns_to_remove:
            del data.nicknames[nn]
            echo(f"Deleted nickname {nn}")
        save_data(data)
    except ValueError as e:
        echo(e)

@cli.command()
def view_games():
    data = load_data()
    if len(data.games) == 0:
        echo("No games")
        return
    for game in data.games.values():
        _output_game_view(data, game)


def format_timedelta(delta: dt.timedelta) -> str:
    return "".join(str(increment) + abbr for increment, abbr in zip(
        [delta.days, delta.seconds // 3600, (delta.seconds // 60) % 60, delta.seconds % 60],
        ['d', 'h', 'm', 's']
    ))

@cli.command()
@argument('name', help=ARGUMENT_HELP_STRINGS["name"] + "view")
def view_game(name: str):
    data = load_data()
    game = data.get_game(name)
    _output_game_view(data, game)

def _output_game_view(data: Data, game: Game):
    echo(f"{game.name}, adju @ {game.adju_time} {game.adju_tz}")
    echo(f"\t-M/R/A: {format_timedelta(game.move_length)}/{format_timedelta(game.retreat_length)}/{format_timedelta(game.adjustment_length)}")
    for nickname, game_name in data.nicknames.items():
        if game_name == game.name:
            echo(f'\t-"{nickname}"')
    if game.scheduled_commands:
        echo("Scheduled commands:")
        for command in game.scheduled_commands:
            echo (f"\t{format_timedelta(command.offset)}: {command.command} {command.uuid.hex}")


@cli.command()
@argument('name', help=ARGUMENT_HELP_STRINGS["name"] + "edit")
@apply_options(GAME_UPDATE_OPTIONS)
def edit_game(
    name: str,
    adju_time: Optional[str] = None,
    adju_tz: Optional[str] = None,
    phase_lengths: Optional[tuple[dt.timedelta, dt.timedelta, dt.timedelta]] = None,
    nicknames: Optional[list[str]] = None,
    scheduled_commands: Optional[tuple[tuple[dt.timedelta, str], ...]] = None
):
    data = load_data()
    game = data.get_game(name)

    process_and_apply_game_updates(game, adju_time, adju_tz, phase_lengths, nicknames, scheduled_commands)

    _output_game_view(data, game)
    save_data(data)


def _set_nicknames(data: Data, name: str, nicknames: list[str]):
    for nickname in nicknames:
        data.nicknames[nickname] = name


@cli.command()
@argument('name', help=ARGUMENT_HELP_STRINGS['name'])
@argument('nicknames', multiple=True, help=ARGUMENT_HELP_STRINGS['nicknames'])
def set_nicknames(name: str, nicknames: list[str]):
    data = load_data()
    game = data.get_game(name)
    _set_nicknames(data, game.name, nicknames)
    save_data(data)


@cli.command()
def view_nicknames():
    data = load_data()
    if len(data.nicknames) == 0:
        echo("No nicknames set")
    for nickname, full_name in data.nicknames.items():
        echo(f"\t{nickname:.<10}{full_name:.>32}")


@cli.command()
@click.argument('nickname')
def remove_nickname(nickname: str):
    data = load_data()
    del data.nicknames[nickname]
    save_data(data)

@cli.command()
@click.argument('game-name', type=str, help=ARGUMENT_HELP_STRINGS['name'])
@click.argument('id', type=str, nargs=-1, help="ID of scheduled command(s) to remove")
def remove_scheduled_command(game_name: str, ids: tuple[str, ...]):
    data = load_data()
    game = data.get_game(game_name)
    for command_id in ids:
        to_remove = []
        for command in game.scheduled_commands:
            if command.uuid.hex.startswith(command_id):
                to_remove.append(command)
        if len(to_remove) == 0:
            echo(f"No command with id {command_id}")
        elif len(to_remove) > 1:
            echo(f"Ambiguous command id: {command_id}. Matches:")
            for c in to_remove:
                echo(f"\t{c.uuid}")
        else:
            game.scheduled_commands.remove(to_remove.pop())


def get_deadline(time_until: dt.timedelta, adju_time: str, adju_tz) -> dt.datetime:
    # Get the timestamp for this game's adjudication time, on the date `days_until` days from today
    # e.g. args=1, "14:00", ...; call at 13:50 1 Jan 2026 -> timestamp for 14:00 2 Jan 2026
    try:
        hour, minute = map(int, adju_time.split(':'))
    except:
        raise ValueError(f"Invalid timestamp: {adju_time}")
    now = dt.datetime.now(tz=ZoneInfo(adju_tz))
    target_time_today = dt.datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=hour,
        minute=minute,
        tzinfo=ZoneInfo(adju_tz)
    )

    return target_time_today + time_until


@cli.command()
@argument('game_name')
@argument('phase-key', type=str, help="Key for phase (spring/retreats/fall/retreats/winter: s/sr/f/fr/w)")
@argument('year', type=int)
@option('--days-until', '-u', type=TIMEDELTA)
@option('--no-window', '-n', is_flag=True)
@option('--adju-time', '-t')
def adju(*args, **kwargs):
    _adju(*args, **kwargs)


def _adju(
    game_name: str,
    phase_key: str,
    year: int,
    time_until: Optional[dt.timedelta] = None,
    no_window: Optional[bool] = False,
    adju_time: Optional[str] = None
):

    phase: CurrentPhase = CurrentPhase.create_phase(phase_key, year)
    
    data = load_data()
    game = data.get_game(game_name)

    if time_until is None:
        match phase.nxt.phase_type:
            case PhaseType.MOVES: time_until = game.move_length
            case PhaseType.RETREATS: time_until = game.retreat_length
            case PhaseType.ADJUSTMENTS: time_until = game.adjustment_length

    if adju_time is None:
        adju_time = game.adju_time

    deadline = get_deadline(time_until, adju_time, game.adju_tz)
    
    timestamp = int(deadline.timestamp())
    discord_timestamp = f"<t:{timestamp}:" + "{}>"
    timestamp_str = f"{discord_timestamp.format('F')} {discord_timestamp.format('R')}"

    simple_title = phase.simple_title()
    following_title = phase.nxt.simple_title()
    moves_title = phase.moves_title()
    results_title = phase.results_title()

    rendered_F = deadline.astimezone(ZoneInfo(game.adju_tz)).strftime('%A, %B %d, %Y %H:%M')
    delta = (deadline - dt.datetime.now(ZoneInfo(game.adju_tz)))
    rendered_R = f"in {delta.days}d {delta.seconds // 3600}h {(delta.seconds//60)%60}m"

    lines = [
        f"**{simple_title} has been adjudicated. The phase is now {following_title}.** Orders are due {timestamp_str}.",
        f"**{following_title.upper()}: {timestamp_str}**",
        f"**{game.name.upper()} {moves_title.upper()}**",
        f"**{game.name.upper()} {results_title.upper()}**",
        discord_timestamp.format('F'),
        f"\nRendered timestamp:\n\t{rendered_F}\n\t{rendered_R}"
    ]

    for line in lines:
        echo(line)

    if no_window:
        return

    root = tk.Tk()
    root.title("Copy to Clipboard")
    
    for line in lines[:-1]:
        frame = tk.Frame(root)
        frame.pack(fill=tk.X, padx=5, pady=5)
        checkbox = tk.Checkbutton(frame, variable=tk.BooleanVar())
        checkbox.pack(side=tk.LEFT)
        
        label = tk.Label(frame, text=line, wraplength=400, justify=tk.LEFT)
        label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        button = tk.Button(frame, text="Copy", command=lambda l=line: root.clipboard_clear() or root.clipboard_append(l))
        button.pack(side=tk.RIGHT, padx=5)

    root.mainloop()

@cli.command()
def test_adju_output():
    phase_order = ['s', 'sr', 'f', 'fr', 'w']
    for phase in phase_order:
        _adju("wc", phase, 0, no_window=True)

if __name__ == "__main__":
    cli()
