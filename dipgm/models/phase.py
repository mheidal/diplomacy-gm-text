
from dataclasses import dataclass
from enum import Enum


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

_phase_map: dict[str, tuple[Season, PhaseType, Season, PhaseType]] = {
    's': (S.SPRING, P.MOVES, S.SPRING, P.RETREATS),
    'sr': (S.SPRING, P.RETREATS, S.FALL, P.MOVES),
    'f': (S.FALL, P.MOVES, S.FALL, P.RETREATS),
    'fr': (S.FALL, P.RETREATS, S.WINTER, P.ADJUSTMENTS),
    'w': (S.WINTER, P.ADJUSTMENTS, S.SPRING, P.MOVES),
}

@dataclass
class CurrentPhase(Phase):
    nxt: Phase

    @staticmethod
    def create_phase(phase_key: str, year: int):
        k = phase_key.strip().lower()
        cur_season, cur_type, nxt_season, nxt_type = _phase_map[k]
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