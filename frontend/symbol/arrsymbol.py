from utils.tac.temp import Temp

from .symbol import *

"""
Array symbol, representing an array definition.
"""


class ArrSymbol(Symbol):
    def __init__(self, name: str, type: DecafType, isGlobal: bool = False) -> None:
        super().__init__(name, type)
        self.addr: Temp
        self.isGlobal = isGlobal
        self.initValue = 0

    def __str__(self) -> str:
        return "array %s : %s" % (self.name, str(self.type))

    # To set the initial value of an array symbol (used for global array).
    def setInitValue(self, value: int) -> None:
        self.initValue = value
