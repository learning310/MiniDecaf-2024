from enum import Enum, auto, unique
from typing import Any, Optional, Union

from utils.label.label import Label
from utils.label.funclabel import FuncLabel
from utils.tac.reg import Reg

from .tacop import *
from .tacvisitor import TACVisitor
from .temp import Temp
from frontend.symbol.varsymbol import VarSymbol

class TACInstr:
    def __init__(
        self,
        kind: InstrKind,
        dsts: list[Temp],
        srcs: list[Temp],
        label: Optional[Label],
    ) -> None:
        self.kind = kind
        self.dsts = dsts.copy()
        self.srcs = srcs.copy()
        self.label = label

    def getRead(self) -> list[int]:
        return [src.index for src in self.srcs]

    def getWritten(self) -> list[int]:
        return [dst.index for dst in self.dsts]

    def isLabel(self) -> bool:
        return self.kind is InstrKind.LABEL

    def isSequential(self) -> bool:
        return self.kind == InstrKind.SEQ

    def isReturn(self) -> bool:
        return self.kind == InstrKind.RET

    def accept(self, v: TACVisitor) -> None:
        pass


# Assignment instruction.
class Assign(TACInstr):
    def __init__(self, dst: Temp, src: Temp) -> None:
        super().__init__(InstrKind.SEQ, [dst], [src], None)
        self.dst = dst
        self.src = src

    def __str__(self) -> str:
        return "%s = %s" % (self.dst, self.src)

    def accept(self, v: TACVisitor) -> None:
        v.visitAssign(self)


# Loading an immediate 32-bit constant.
class LoadImm4(TACInstr):
    def __init__(self, dst: Temp, value: int) -> None:
        super().__init__(InstrKind.SEQ, [dst], [], None)
        self.dst = dst
        self.value = value

    def __str__(self) -> str:
        return "%s = %d" % (self.dst, self.value)

    def accept(self, v: TACVisitor) -> None:
        v.visitLoadImm4(self)


# Unary operations.
class Unary(TACInstr):
    def __init__(self, op: TacUnaryOp, dst: Temp, operand: Temp) -> None:
        super().__init__(InstrKind.SEQ, [dst], [operand], None)
        self.op = op
        self.dst = dst
        self.operand = operand

    def __str__(self) -> str:
        return "%s = %s %s" % (
            self.dst,
            ("-" if (self.op == TacUnaryOp.NEG) else "!"),
            self.operand,
        )

    def accept(self, v: TACVisitor) -> None:
        v.visitUnary(self)


# Binary Operations.
class Binary(TACInstr):
    def __init__(self, op: TacBinaryOp, dst: Temp, lhs: Temp, rhs: Temp) -> None:
        super().__init__(InstrKind.SEQ, [dst], [lhs, rhs], None)
        self.op = op
        self.dst = dst
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self) -> str:
        opStr = {
            TacBinaryOp.ADD: "+",
            TacBinaryOp.SUB: "-",
            TacBinaryOp.MUL: "*",
            TacBinaryOp.DIV: "/",
            TacBinaryOp.MOD: "%",
            TacBinaryOp.EQ: "==",
            TacBinaryOp.NE: "!=",
            TacBinaryOp.LT: "<",
            TacBinaryOp.LE: "<=",
            TacBinaryOp.GT: ">",
            TacBinaryOp.GE: ">=",
            TacBinaryOp.LAND: "&&",
            TacBinaryOp.LOR: "||",
        }[self.op]
        return "%s = (%s %s %s)" % (self.dst, self.lhs, opStr, self.rhs)

    def accept(self, v: TACVisitor) -> None:
        v.visitBinary(self)


# Branching instruction.
class Branch(TACInstr):
    def __init__(self, target: Label) -> None:
        super().__init__(InstrKind.JMP, [], [], target)
        self.target = target

    def __str__(self) -> str:
        return "branch %s" % str(self.target)

    def accept(self, v: TACVisitor) -> None:
        v.visitBranch(self)


# Branching with conditions.
class CondBranch(TACInstr):
    def __init__(self, op: CondBranchOp, cond: Temp, target: Label) -> None:
        super().__init__(InstrKind.COND_JMP, [], [cond], target)
        self.op = op
        self.cond = cond
        self.target = target

    def __str__(self) -> str:
        return "if (%s %s) branch %s" % (
            self.cond,
            "== 0" if self.op == CondBranchOp.BEQ else "!= 0",
            str(self.target),
        )

    def accept(self, v: TACVisitor) -> None:
        v.visitCondBranch(self)


# Return instruction.
class Return(TACInstr):
    def __init__(self, value: Optional[Temp]) -> None:
        if value is None:
            super().__init__(InstrKind.RET, [], [], None)
        else:
            super().__init__(InstrKind.RET, [], [value], None)
        self.value = value

    def __str__(self) -> str:
        return "return" if (self.value is None) else ("return " + str(self.value))

    def accept(self, v: TACVisitor) -> None:
        v.visitReturn(self)


# Annotation (used for debugging).
class Memo(TACInstr):
    def __init__(self, msg: str) -> None:
        super().__init__(InstrKind.SEQ, [], [], None)
        self.msg = msg

    def __str__(self) -> str:
        return "memo '%s'" % self.msg

    def accept(self, v: TACVisitor) -> None:
        v.visitMemo(self)


# Label (function entry or branching target).
class Mark(TACInstr):
    def __init__(self, label: Label) -> None:
        super().__init__(InstrKind.LABEL, [], [], label)

    def __str__(self) -> str:
        return "%s:" % str(self.label)

    def accept(self, v: TACVisitor) -> None:
        v.visitMark(self)


# Declare parameters.
class DeclParams(TACInstr):
    def __init__(self, params: list[Temp]) -> None:
        super().__init__(TacFuncOp.DECL_PARAMS, [], params, None)
        self.params = params

    def __str__(self) -> str:
        return "param %s" % len(self.params)

    def accept(self, v: TACVisitor) -> None:
        v.visitDeclParams(self)


# Function call.
class Call(TACInstr):
    def __init__(self, func: FuncLabel, ret: Temp, params: list[Temp]) -> None:
        super().__init__(TacFuncOp.CALL, [ret], params, func)
        self.label = func
        self.ret = ret
        self.params = params

    def __str__(self) -> str:
        return "%s = call %s(%s)" % (self.ret, self.label, ", ".join(map(str, self.params)))

    def accept(self, v: TACVisitor) -> None:
        v.visitCall(self)


# Load symbols.
class LoadSymbol(TACInstr):
    def __init__(self, dst: Temp, symbol: str) -> None:
        super().__init__(InstrKind.SEQ, [dst], [], None)
        self.dst = dst
        self.symbol = symbol

    def __str__(self) -> str:
        return "%s = &%s" % (self.dst, self.symbol)

    def accept(self, v: TACVisitor) -> None:
        v.visitLoadSymbol(self)


# Load global variables.
class Load(TACInstr):
    def __init__(self, src: Temp, base: Temp) -> None:
        super().__init__(InstrKind.SEQ, [], [src, base], None)
        self.src = src
        self.base = base

    def __str__(self) -> str:
        return "%s = *%s" % (self.src, self.base)

    def accept(self, v: TACVisitor) -> None:
        v.visitLoad(self)


# Assign a value to a global address.
class AddrAssign(TACInstr):
    def __init__(self, addr: Temp, src: Temp, offset: int = 0) -> None:
        super().__init__(InstrKind.SEQ, [], [src, addr], None)
        self.addr = addr
        self.offset = offset
        self.src = src

    def __str__(self) -> str:
        return "%s[%s] = %s" % (self.addr, self.offset, self.src)

    def accept(self, v: TACVisitor) -> None:
        v.visitAddrAssign(self)


# Allocate memory on the stack.
class Alloc(TACInstr):
    def __init__(self, dst: Temp, size: int) -> None:
        super().__init__(InstrKind.SEQ, [dst], [], None)
        self.dst = dst
        self.size = size

    def __str__(self) -> str:
        return f"{self.dst} = alloc {self.size}"
    
    def accept(self, v: TACVisitor) -> None:
        v.visitAlloc(self)


# Memset operation.
class Memset(TACInstr):
    def __init__(self, addr: Temp, size: Temp) -> None:
        super().__init__(InstrKind.SEQ, [], [addr, size], None)
        self.addr = addr
        self.size = size

    def __str__(self) -> str:
        return f"memset {self.addr} {self.size}"

    def accept(self, v: TACVisitor) -> None:
        v.visitMemset(self)
