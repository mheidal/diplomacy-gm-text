import datetime as dt
from enum import Enum
from typing import Optional, Self
from zoneinfo import ZoneInfo
import click
from click import echo, group, argument, option
from dataclasses import dataclass, fields, field
from pathlib import Path
from pickle import load, dump
import pytz
import tkinter as tk

@dataclass
class GameConfigDefaults:
    adju_time: str = "14:00"
    adju_tz: str = "America/Los_Angeles"
    move_length: int = 2
    retreat_length: int = 1
    adjustment_length: int = 1

@dataclass
class GameConfigOverrides:
    adju_time: Optional[str]
    adju_tz: Optional[str]
    move_length: Optional[int]
    retreat_length: Optional[int]
    adjustment_length: Optional[int]

class Game(GameConfigDefaults):
    name: str
    def __init__(
        self,
        name: str,
    ):
        self.name = name
    
    def apply_overrides(self, overrides: GameConfigOverrides):
        for field_ in fields(overrides):
            value = getattr(overrides, field_.name)
            if value is not None:
                setattr(self, field_.name, value)

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

def get_datapath() -> Path:
    return Path("data.pickle")

def initialize_data(path: Path):
    data = Data()
    with open(path, 'wb') as f:
        dump(data, f)
    return data

def load_data() -> Data:
    path = get_datapath()
    try:
        with open(path, 'rb') as f:
            data = load(f)
        return data
    except FileNotFoundError:
        return initialize_data(path)
    except EOFError:
        return initialize_data(path)

def save_data(data: Data):
    path = get_datapath()
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


@group()
def cli():
    pass

@cli.command()
@argument('name')
@option('--time', '-t')
@option('--timezone', '-z')
@option('--phase-lengths', '-p', nargs=3, type=tuple[int, int, int], help="Phase lengths, in days (moves, retreats, adjustments)")
@option('--nicknames', '-n', multiple=True)
def create_game(
    name: str,
    time: Optional[str] = None,
    timezone: Optional[str] = None,
    phase_lengths: Optional[tuple[int, int, int]] = None,
    nicknames: Optional[list[str]] = None
):
    data = load_data()
    if name in data.games:
        echo(f"Game {name} already exists")
        return

    game = Game(name)
    game.apply_overrides(GameConfigOverrides(
            adju_time=time,
            adju_tz=timezone,
            move_length=phase_lengths[0] if phase_lengths is not None else None,
            retreat_length=phase_lengths[1] if phase_lengths is not None else None,
            adjustment_length=phase_lengths[2] if phase_lengths is not None else None,
    ))

    data.games[name] = game

    if nicknames is not None:
        for nickname in nicknames:
            _set_nickname(data, name, nickname)
    save_data(data)


@cli.command()
@argument('name')
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
        _view_game(data, game)


@cli.command()
@argument('name')
def view_game(name: str):
    data = load_data()
    game = data.get_game(name)
    _view_game(data, game)

def _view_game(data: Data, game: Game):
    echo(f"{game.name}, adju @ {game.adju_time} {game.adju_tz}")
    echo(f"\t-M/R/A: {game.move_length}/{game.retreat_length}/{game.adjustment_length}")
    for nickname, game_name in data.nicknames.items():
        if game_name == game.name:
            echo(f'\t-"{nickname}"')

@cli.command()
@argument('name')
@option('--adju-time', '-t')
@option('--adju-tz', '-z')
@option('--moves-length', '-m', type=int)
@option('--retreats-length', '-r', type=int)
@option('--adjustments-length', '-a', type=int)
def edit_game(
    name: str,
    adju_time: Optional[str] = None,
    adju_tz: Optional[str] = None,
    moves_length: Optional[int] = None,
    retreats_length: Optional[int] = None,
    adjustments_length: Optional[int] = None,
):
    data = load_data()
    game = data.get_game(name)

    game.apply_overrides(GameConfigOverrides(
            adju_time=adju_time,
            adju_tz=adju_tz,
            move_length=moves_length,
            retreat_length=retreats_length,
            adjustment_length=adjustments_length,
    ))

    _view_game(data, game)
    save_data(data)


def _set_nickname(data: Data, full_name: str, nickname: str):
    data.nicknames[nickname] = full_name


@cli.command()
@argument('full_name')
@argument('nickname')
def set_nickname(full_name: str, nickname: str):
    data = load_data()
    _set_nickname(data, full_name, nickname)
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


def get_deadline(days_until: int, adju_time: str, adju_tz) -> dt.datetime:
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

    return target_time_today + dt.timedelta(days_until)


class PhaseType(Enum):
    MOVES = "Moves"
    RETREATS = "Retreats"
    ADJUSTMENTS = "Adjustments"

    def __str__(self) -> str:
        return self.value

class Season(Enum):
    SPRING = "Spring"
    FALL = "Fall"
    WINTER = "Winter"

    def __str__(self) -> str:
        return self.value

P = PhaseType
S = Season

@dataclass
class Phase:
    season: Season
    year: int
    phase_type: PhaseType

    def simple_title(self):
        ret = f"{self.season} {self.year}"
        if self.phase_type == PhaseType.RETREATS:
            ret += " Retreats"
        return ret

@dataclass
class CurrentPhase(Phase):
    nxt: Phase

    _phase_map: dict[str, tuple[Season, PhaseType, Season, PhaseType]] = {
        's': (S.SPRING, P.MOVES, S.SPRING, P.RETREATS),
        'sr': (S.SPRING, P.RETREATS, S.FALL, P.MOVES),
        'f': (S.FALL, P.MOVES, S.FALL, P.RETREATS),
        'fr': (S.FALL, P.RETREATS, S.WINTER, P.ADJUSTMENTS),
        'w': (S.WINTER, P.ADJUSTMENTS, S.SPRING, P.MOVES),
    }

    @staticmethod
    def create_phase(phase_key: str, year: int):
        k = phase_key.strip().lower()
        cur_season, cur_type, nxt_season, nxt_type = CurrentPhase._phase_map[k]
        return CurrentPhase(
            cur_season,
            year,
            cur_type,
            Phase(
                nxt_season,
                year + (1 if cur_season == Season.WINTER else 0),
                nxt_type
            )
        )

    def moves_title(self) -> str:
        ret = self.simple_title()
        match self.phase_type:
            case PhaseType.RETREATS:
                pass
            case PhaseType.MOVES:
                ret += " Moves"
            case PhaseType.ADJUSTMENTS:
                ret += " Adjustments"
        return ret

    def results_title(self) -> str:
        match self.phase_type:
            case PhaseType.RETREATS | PhaseType.ADJUSTMENTS:
                return self.nxt.simple_title()
            case PhaseType.MOVES:
                    return self.simple_title() + " Results"


@cli.command()
@argument('game_name')
@argument('phase_name')
@argument('year', type=int)
@option('--days-until', '-u', type=int)
@option('--no-window', '-n', is_flag=True)
@option('--adju-time', '-t')
def adju(*args, **kwargs):
    _adju(*args, **kwargs)


def _adju(
    game_name: str,
    phase_name: str,
    year: int,
    days_until: Optional[int] = None,
    no_window: Optional[bool] = False,
    adju_time: Optional[str] = None
):

    phase: CurrentPhase = CurrentPhase.create_phase(phase_name, year)
    
    data = load_data()
    game = data.get_game(game_name)

    if days_until is None:
        match phase.nxt.phase_type:
            case P.MOVES: days_until = game.move_length
            case P.RETREATS: days_until = game.retreat_length
            case P.ADJUSTMENTS: days_until = game.adjustment_length

    if adju_time is None:
        adju_time = game.adju_time

    deadline = get_deadline(days_until, adju_time, game.adju_tz)
    
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
