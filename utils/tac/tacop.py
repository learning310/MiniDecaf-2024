from enum import Enum, auto, unique


# Kinds of instructions.
@unique
class InstrKind(Enum):
    # Labels.
    LABEL = auto()
    # Sequential instructions (unary operations, binary operations, etc).
    SEQ = auto()
    # Branching instructions.
    JMP = auto()
    # Branching with conditions.
    COND_JMP = auto()
    # Return instruction.
    RET = auto()


# Kinds of unary operations.
@unique
class TacUnaryOp(Enum):
    NEG = auto()
    NOT = auto()
    LNOT = auto()

# Kinds of binary operations.
@unique
class TacBinaryOp(Enum):
    # Arithmetic Operators
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    # Comparison Operators
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    # Logical Operators
    LAND = auto()
    LOR = auto()
    # Bitwise Operators
    AND = auto()
    OR = auto()
    XOR = auto()


# Kinds of branching with conditions.
@unique
class CondBranchOp(Enum):
    BEQ = auto()
    BNE = auto()


# Kinds of function-related instructions.
@unique
class TacFuncOp(Enum):
    CALL = auto()
    DECL_PARAMS = auto()


# Kinds of instructions for load global symbols.
@unique
class TacLoadOp(Enum):
    LOAD = auto()
    LOAD_SYMBOL = auto()
