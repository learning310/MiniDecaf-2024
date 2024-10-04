from typing import Any, Optional, Union

from .tacfunc import TACFunc
from .globalvar import GlobalVar


# A TAC program consists of several TAC functions and global variables.
class TACProg:
    def __init__(self, funcs: list[TACFunc], vars: list[GlobalVar]) -> None:
        self.funcs = funcs
        self.vars = vars

    def printTo(self) -> None:
        for var in self.vars:
            var.printTo()
        for func in self.funcs:
            func.printTo()
