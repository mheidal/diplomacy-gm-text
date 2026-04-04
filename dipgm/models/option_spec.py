
from dataclasses import dataclass
from typing import Callable


@dataclass
class OptionSpec:
    param_name: str
    click_decorator: Callable