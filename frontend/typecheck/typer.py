from typing import Protocol, TypeVar

from ..ast.node import T
from ..ast.tree import Function
from frontend.ast.node import Node
from frontend.ast.tree import *
from frontend.ast.visitor import Visitor
from frontend.scope.globalscope import GlobalScope
from frontend.scope.scopestack import ScopeStack
from frontend.type.array import ArrayType
from utils.error import *

"""
The typer phase: type check abstract syntax tree.
"""


class Typer(Visitor[ScopeStack, None]):
    def __init__(self) -> None:
        pass

    # Entry of this phase
    def transform(self, program: Program) -> Program:
        for decl in program.var_declarations().values():
            decl.accept(self, None)
        for decl in program.arr_declarations().values():
            decl.accept(self, None)
        for func in program.functions().values():
            func.accept(self, None)
        return program

    def visitBlock(self, block: Block, ctx: T) -> None:
        block.type = INT
        for child in block.children:
            child.accept(self, ctx)
            if isinstance(child, Return):
                block.type = child.type

    def visitReturn(self, stmt: Return, ctx: T) -> None:
        stmt.expr.accept(self, ctx)
        stmt.type = stmt.expr.type

    def visitVarDeclaration(self, decl: VarDeclaration, ctx: T) -> None:
        if decl.init_expr != NULL:
            decl.init_expr.accept(self, ctx)
            if decl.init_expr.type != decl.var_t:
                raise DecafTypeMismatchError()

    def visitIdentifier(self, ident: Identifier, ctx: T) -> None:
        ident.type = ident.getattr('symbol').type

    def visitFunction(self, func: Function, ctx: T) -> None:
        func.body.accept(self, ctx)
        if func.ret_t != func.body.type:
            raise DecafTypeMismatchError()

    def visitCall(self, call: Call, ctx: T) -> None:
        para_types = call.getattr('symbol').para_types
        for t, arg in zip(para_types, call.argument_list):
            arg.accept(self, ctx)
            if isinstance(arg.type, ArrayType) and isinstance(t, ArrayType):
                # Ignore the first dimension of ArrayType
                # int[10][7] == int[7][7] == int[][7]
                if arg.type.base != t.base:
                    raise DecafTypeMismatchError()
            elif arg.type != t:
                print(f'{arg.type} != {t}')
                raise DecafTypeMismatchError()
        call.type = call.getattr('symbol').type

    def visitArrayAccess(self, expr: ArrayAccess, ctx: T) -> None:
        expr.base.accept(self, ctx)
        expr.index.accept(self, ctx)
        if expr.index.type != INT:
            raise DecafTypeMismatchError()
        if not isinstance(expr.base.type, ArrayType):
            raise DecafTypeMismatchError()
        expr.type = expr.getattr('symbol').type

    def visitAssignment(self, expr: Assignment, ctx: T) -> None:
        expr.rhs.accept(self, ctx)
        expr.lhs.accept(self, ctx)
        if expr.lhs.type != expr.rhs.type:
            raise DecafTypeMismatchError()
        expr.type = expr.lhs.type

    def visitIf(self, stmt: If, ctx: T) -> None:
        stmt.cond.accept(self, ctx)

        if stmt.otherwise is NULL:
            stmt.then.accept(self, ctx)
        else:
            stmt.then.accept(self, ctx)
            stmt.otherwise.accept(self, ctx)

    def visitWhile(self, stmt: While, ctx: T) -> None:
        stmt.cond.accept(self, ctx)
        stmt.body.accept(self, ctx)

    def visitFor(self, stmt: For, ctx: T) -> None:
        stmt.init.accept(self, ctx)
        stmt.cond.accept(self, ctx)
        stmt.body.accept(self, ctx)
        stmt.update.accept(self, ctx)

    def visitUnary(self, expr: Unary, ctx: T) -> None:
        expr.operand.accept(self, ctx)
        expr.type = expr.operand.type

    def visitBinary(self, expr: Binary, ctx: T) -> None:
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)
        if expr.lhs.type != expr.rhs.type:
            raise DecafTypeMismatchError()
        if expr.lhs.type != INT:
            raise DecafTypeMismatchError()
        expr.type = expr.lhs.type

    def visitCondExpr(self, expr: ConditionExpression, ctx: T) -> None:
        expr.cond.accept(self, ctx)
        expr.then.accept(self, ctx)
        expr.otherwise.accept(self, ctx)

        if expr.then.type != expr.otherwise.type:
            raise DecafTypeMismatchError()
        expr.type = expr.then.type

    def visitIntLiteral(self, expr: IntLiteral, ctx: T) -> None:
        expr.type = INT
