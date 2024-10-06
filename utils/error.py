from typing import Any, Generic, Optional, TypeVar, Union

from utils import find_column


class DecafLexError(Exception):
    def __init__(self, t) -> None:
        super().__init__(
            f"Lex error: invalid token at line {t.lineno}, column {find_column(t.lexer.lexdata, t.lexpos)}"
        )
        self.token = t


class DecafSyntaxError(Exception):
    def __init__(self, t, extra: Optional[str] = None) -> None:
        if t is not None:
            msg = (
                f"Syntax error: line {t.lineno}, column {find_column(t.lexer.lexdata, t.lexpos)}"
                + (extra or "")
            )
        else:
            msg = f"Syntax error: " + (extra or "")
        super().__init__(msg)
        self.token = t


class DecafNoMainFuncError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: can not find 'main' function")


class DecafDeclConflictError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__("Semantic error: declaration conflict '%s'" % name)


class DecafRedefinedSymbolError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__("Semantic error: redefined symbol '%s'" % name)


class DecafBadIntValueError(Exception):
    def __init__(self, val: Union[str, int]) -> None:
        super().__init__("Semantic error: bad integer value " + str(val))


class DecafEmptyArraySizeError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__("Semantic error: array '%s' with an empty size" % name)


class DecafNonPositiveArraySizeError(Exception):
    def __init__(self, name: str, size: int) -> None:
        super().__init__("Semantic error: array '%s' with non-positive size '%d'" % (name, size))


class DecafArrayInitSizeError(Exception):
    def __init__(self, name: str, expected: int, got: int) -> None:
        super().__init__(
            "Semantic error: array '%s' with size '%d' but initialized with '%d' values"
            % (name, expected, got)
        )


class DecafUndefinedVarError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__("Semantic error: undefined variable '%s'" % name)


class DecafUndefinedFuncError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__("Semantic error: undefined function '%s'" % name)


class DecafBadArgCountError(Exception):
    def __init__(self, name: str, expected: int, got: int) -> None:
        super().__init__(
            "Semantic error: bad argument count for function '%s', expected %d, got %d"
            % (name, expected, got)
        )

class DecafBreakOutsideLoopError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: 'break' outside any loops")


class DecafContinueOutsideLoopError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: 'continue' outside any loops")


class DecafGlobalVarDefinedTwiceError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(
            "Semantic error: global variable '%s' has been defined twice" % name
        )


class DecafGlobalVarBadInitValueError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(
            "Semantic error: the initial value of global variable '%s' must be an integer constant"
            % name
        )


class DecafBadIndexError(Exception):
    def __init__(self, name: Optional[str] = None) -> None:
        if name:
            super().__init__("Semantic error: bad index on '%s'" % name)
        else:
            super().__init__("Semantic error: bad index")


class DecafTypeMismatchError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: type mismatch") # TODO: Type mismatch


class DecafBadReturnTypeError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: bad return type")


class DecafBadFuncCallError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__("Semantic error: bad function call '%s'" % name)


class DecafBadAssignTypeError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: cannot assign to a non-lvalue") # TODO: Type mismatch


class DecafBadOperationTypeError(Exception):
    def __init__(self) -> None:
        super().__init__("Semantic error: cannot perform operation on the given type") # TODO: Type mismatch


class IllegalArgumentException(Exception):
    def __init__(self) -> None:
        super().__init__("error: encounter a non-returned basic block")


class NullPointerException(Exception):
    def __init__(self) -> None:
        super().__init__("NullPointerException")
