from typing import Any, Optional, Union

from .tacfunc import TACFunc
from .globalvar import GlobalVar
from .globalarr import GlobalArr


# A TAC program consists of several TAC functions and global variables.
class TACProg:
    def __init__(self, funcs: list[TACFunc], vars: list[GlobalVar], arrs: list[GlobalArr]) -> None:
        self.funcs = funcs
        self.vars = vars
        self.arrs = arrs

    def printTo(self) -> None:
        for var in self.vars:
            var.printTo()
        for arr in self.arrs:
            arr.printTo()
        for func in self.funcs:
            func.printTo()
