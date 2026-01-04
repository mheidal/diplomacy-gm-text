import datetime as dt
from typing import Optional
from zoneinfo import ZoneInfo
import click
from click import echo, group, argument, option
from dataclasses import dataclass, field
from pathlib import Path
from pickle import load, dump
import pytz
import tkinter as tk

@dataclass
class Game:
    name: str
    adju_time: str = field(default= "14:00")
    adju_tz: str = field(default="America/Los_Angeles")

@dataclass
class Data:
    games: dict[str, Game] = field(default_factory=dict)
    nicknames: dict[str, str] = field(default_factory=dict)

    def try_get_game(self, name: str) -> Game:
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
        map(int, time.split(':'))
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
@option('--nicknames', '-n', multiple=True)
def create_game(name: str, time: Optional[str] = None, timezone: Optional[str] = None, nicknames: Optional[list[str]] = None):
    data = load_data()
    if name in data.games:
        echo(f"Game {name} already exists")
        return
    args = [name]
    if time is not None: args.append(time)
    if timezone is not None: args.append(timezone)
    data.games[name] = Game(*args)
    if nicknames is not None:
        for nickname in nicknames:
            _set_nickname(data, name, nickname)
    save_data(data)


@cli.command()
@argument('name')
def delete_game(name: str):
    data = load_data()
    try:
        name = data.try_get_game(name).name
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
        echo(f"{game.name}, adju @ {game.adju_time} {game.adju_tz}")
        for nickname, game_name in data.nicknames.items():
            if game_name == game.name:
                echo(f"\t-{nickname}")


@cli.command()
@argument('name')
@option('--adju_time', '-t')
@option('adju_tz', '-z')
def edit_game(name: str, adju_time: Optional[str] = None, adju_tz: Optional[str] = None):
    if adju_time is None and adju_tz is None:
        echo("No edits to be made")
    data = load_data()
    game = data.try_get_game(name)
    if adju_time is not None:
        if time_is_valid(adju_time):
            game.adju_time = adju_time
    if adju_tz is not None:
        if tz_is_valid(adju_tz):
            game.adju_tz = adju_tz
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


def next_adju_occurrence(day_offset: int, adju_time: str, adju_tz, **kwargs) -> dt.datetime:
    hour, minute = map(int, adju_time.split(':'))
    target_time = dt.time(hour, minute)
    now = dt.datetime.now()
    today_target = dt.datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=target_time.hour,
        minute=target_time.minute,
        tzinfo=ZoneInfo(adju_tz)
    )
    if today_target.timestamp() > now.timestamp():
        return today_target + dt.timedelta(day_offset)
    else:
        return today_target + dt.timedelta(int(day_offset) + 1)


@dataclass
class Phase:
    season: str
    retreats: bool = False
    year: Optional[int] = None

    def set_year(self, year: int):
        self.year = year

    def simple_title(self):
        moves = self.moves_title()
        if self.retreats:
            return moves
        else:
            return ' '.join(w for w in moves.split()[:-1])

    def moves_title(self) -> str:
        match self.season:
            case "Spring" | "Fall":
                return f"{self.season} {self.year} {'Retreats' if self.retreats else 'Moves'}"
            case "Winter":
                return f"{self.season} {self.year} Adjustments"
            case _: raise ValueError

    def results_title(self) -> str:
        if self.year is None:
            raise ValueError("No year set")
        if self.retreats:
            match self.season:
                case "Spring":
                    return f"Fall {self.year}"
                case "Fall":
                    return f"Winter {self.year}"
                case _: raise ValueError
        else:
            match self.season:
                case "Spring" | "Fall":
                    return f"{self.season} {self.year} Results"
                case "Winter":
                    return f"Spring {int(self.year) + 1}"
                case _: raise ValueError
    
    def following_title(self):
        if self.retreats or self.season == "Winter":
            return self.results_title()
        return f"{self.season} {self.year} Retreats"


@cli.command()
@argument('game_name')
@argument('phase')
@argument('year')
@option('--days_offset', '-o')
def adju(game_name: str, phase: str, year: int, days_offset: Optional[int] = None):
    clean_phase = phase.strip().lower()
    valid_phases = ['s', 'sr', 'f', 'fr', 'w']

    phases: dict[str, Phase] = {
        's': Phase("Spring"),
        'sr': Phase("Spring", retreats=True),
        'f': Phase("Fall"),
        'fr': Phase("Fall", retreats=True),
        'w': Phase("Winter")
    }
    for p in phases.values():
        p.set_year(year)

    if clean_phase not in valid_phases:
        echo(f"Invalid phase: {phase}. Phase must be one of: {' '.join(valid_phases)}")
        return
    
    data = load_data()
    game = data.try_get_game(game_name)

    if days_offset is None:
        day_offset = 1 if clean_phase in ['s', 'f', 'fr'] else 2
    else:
        day_offset = int(days_offset)
    next_adju_time = next_adju_occurrence(day_offset, game.adju_time, game.adju_tz)
    
    timestamp = int(next_adju_time.timestamp())
    discord_timestamp = f"<t:{timestamp}:" + "{}>"
    timestamp_str = f"{discord_timestamp.format('F')} {discord_timestamp.format('R')}"

    p = phases[clean_phase]
    simple_title = p.simple_title()
    moves_title = p.moves_title()
    results_title = p.results_title()
    following_title = p.following_title()

    rendered_F = next_adju_time.astimezone(ZoneInfo(game.adju_tz)).strftime('%A, %B %d, %Y %H:%M %p')
    delta = (next_adju_time - dt.datetime.now(ZoneInfo(game.adju_tz)))
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

if __name__ == "__main__":
    cli()