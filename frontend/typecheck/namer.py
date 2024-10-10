import math
from typing import Protocol, TypeVar, cast

from ..ast.tree import ArrParameter

from ..ast.node import T
from ..ast.tree import ArrayAccess
from frontend.ast.node import Node, NullType
from frontend.ast.tree import *
from frontend.ast.visitor import RecursiveVisitor, Visitor
from frontend.scope.globalscope import GlobalScope
from frontend.scope.scope import Scope, ScopeKind
from frontend.scope.scopestack import ScopeStack
from frontend.symbol.funcsymbol import FuncSymbol
from frontend.symbol.symbol import Symbol
from frontend.symbol.varsymbol import VarSymbol
from frontend.symbol.arrsymbol import ArrSymbol
from frontend.type.array import ArrayType
from frontend.type.type import DecafType
from utils.error import *
from utils.riscv import MAX_INT

"""
The namer phase: resolve all symbols defined in the abstract 
syntax tree and store them in symbol tables (i.e. scopes).
"""


class Namer(Visitor[ScopeStack, None]):
    def __init__(self) -> None:
        pass

    # Entry of this phase
    def transform(self, program: Program) -> Program:
        # Global scope. You don't have to consider it until Step 6.
        program.globalScope = GlobalScope
        ctx = ScopeStack(program.globalScope)

        program.accept(self, ctx)
        return program

    def visitProgram(self, program: Program, ctx: ScopeStack) -> None:
        # Check if the 'main' function is missing
        if not program.hasMainFunc():
            raise DecafNoMainFuncError
        
        redefinedSymbol = program.getRedefinedSymbol()
        if not redefinedSymbol is None:
            raise DecafRedefinedSymbolError(redefinedSymbol)

        for child in program.children:
            child.accept(self, ctx)

    def visitVarParameter(self, param: VarParameter, ctx: ScopeStack) -> None:
        varSymbol = VarSymbol(param.ident.value, param.var_t)
        if ctx.top().lookup(param.ident.value) is None:
            ctx.top().declare(varSymbol)
        else:
            raise DecafDeclConflictError(param.ident.value)
        param.setattr('symbol', varSymbol)
    
    def visitArrParameter(self, param: ArrParameter, ctx: ScopeStack) -> None:
        arrSymbol = ArrSymbol(param.ident.value, param.var_t)
        if ctx.top().lookup(param.ident.value) is None:
            ctx.top().declare(arrSymbol)
        else:
            raise DecafDeclConflictError(param.ident.value)
        param.setattr('symbol', arrSymbol)
        
    def visitParameterList(self, params: ParameterList, ctx: ScopeStack) -> None:
        for param in params:
            param.accept(self, ctx)

    def visitFunction(self, func: Function, ctx: ScopeStack) -> None:
        funcSymbol = FuncSymbol(func.ident.value, func.ret_t, GlobalScope)
        print(f'# COMMENT: [def {funcSymbol}]')
        # TODO: Define 和 Declare 的区别是什么？
        for param in func.params:
            funcSymbol.addParaType(param.var_t)
        if GlobalScope.containsKey(funcSymbol):
            raise DecafDeclConflictError(func.ident.value)
        GlobalScope.define(funcSymbol)
        GlobalScope.declare(funcSymbol)

        ctx.newScope(True)
        func.params.accept(self, ctx)
        func.body.accept(self, ctx)
        ctx.pop()
    
    def visitCall(self, call: Call, ctx: ScopeStack) -> None:
        funcSymbol = ctx.lookup(call.ident.value)
        print(f'# COMMENT: [call {funcSymbol}]')
        if funcSymbol is None:
            raise DecafUndefinedFuncError(call.ident.value)
        if not isinstance(funcSymbol, FuncSymbol):
            raise DecafDeclConflictError(call.ident.value)
        call.setattr('symbol', funcSymbol)

        if funcSymbol.parameterNum != len(call.argument_list):
            raise DecafBadArgCountError(funcSymbol.name, funcSymbol.parameterNum, len(call.argument_list))

        for arg in call.argument_list:
            arg.accept(self, ctx)

    def visitBlock(self, block: Block, ctx: ScopeStack) -> None:
        if ctx.top().is_func:
            ctx.top().is_func = False
            for child in block:
                child.accept(self, ctx)
        else:
            ctx.newScope()
            for child in block:
                child.accept(self, ctx)
            ctx.pop()

    def visitReturn(self, stmt: Return, ctx: ScopeStack) -> None:
        stmt.expr.accept(self, ctx)

    """
    def visitFor(self, stmt: For, ctx: Stack) -> None:

    1. Open a local scope for stmt.init.
    2. Visit stmt.init, stmt.cond, stmt.update.
    3. Open a loop in ctx (for validity checking of break/continue)
    4. Visit body of the loop.
    5. Close the loop and the local scope.
    """
    def visitFor(self, stmt: For, ctx: ScopeStack) -> None:
        ctx.newScope()
        stmt.init.accept(self, ctx)
        if not stmt.cond is NULL:
            stmt.cond.accept(self, ctx)
        else:
            stmt.cond = IntLiteral(1)
        stmt.update.accept(self, ctx)
        ctx.increaseLoop()
        stmt.body.accept(self, ctx)
        ctx.decreaseLoop()
        ctx.pop()

    def visitIf(self, stmt: If, ctx: ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.then.accept(self, ctx)

        # check if the else branch exists
        if not stmt.otherwise is NULL:
            stmt.otherwise.accept(self, ctx)

    def visitWhile(self, stmt: While, ctx: ScopeStack) -> None:
        ctx.increaseLoop()
        stmt.cond.accept(self, ctx)
        stmt.body.accept(self, ctx)
        ctx.decreaseLoop()

    def visitBreak(self, stmt: Break, ctx: ScopeStack) -> None:
        """
        You need to check if it is currently within the loop.
        To do this, you may need to check 'visitWhile'.

        if not in a loop:
            raise DecafBreakOutsideLoopError()
        """
        if ctx.top().loop_count == 0:
            raise DecafBreakOutsideLoopError

    """
    def visitContinue(self, stmt: Continue, ctx: Stack) -> None:
    
    1. Refer to the implementation of visitBreak.
    """
    def visitContinue(self, stmt: Continue, ctx: ScopeStack) -> None:
        if ctx.top().loop_count == 0:
            raise DecafContinueOutsideLoopError

    def visitVarDeclaration(self, decl: VarDeclaration, ctx: ScopeStack) -> None:
        """
        1. Use ctx.lookup to find if a variable with the same name has been declared.
        2. If not, build a new VarSymbol, and put it into the current scope using ctx.declare.
        3. Set the 'symbol' attribute of decl.
        4. If there is an initial value, visit it.
        """
        varSymbol = ctx.top().lookup(decl.ident.value)
        if varSymbol is None:
            varSymbol = VarSymbol(decl.ident.value, decl.var_t, ctx.isGlobalScope())
            ctx.top().declare(varSymbol)
        else:
            raise DecafDeclConflictError(decl.ident.value)
        decl.setattr('symbol', varSymbol)
        if not decl.init_expr is NULL:
            decl.init_expr.accept(self, ctx)
        
    def visitArrDeclaration(self, decl: ArrDeclaration, ctx: ScopeStack) -> None:
        arrSymbol = ctx.top().lookup(decl.ident.value)
        if arrSymbol is None:
            arrSymbol = ArrSymbol(decl.ident.value, decl.var_t, ctx.isGlobalScope())
            ctx.top().declare(arrSymbol)
        else:
            raise DecafDeclConflictError(decl.ident.value)
        decl.setattr('symbol', arrSymbol)
        # TODO: No initial value for array
    
    def visitArrayAccess(self, expr: ArrayAccess, ctx: T) -> None:
        expr.base.accept(self, ctx)
        expr.index.accept(self, ctx)
        base_symbol = expr.base.getattr('symbol')
        expr.setattr('symbol', ArrSymbol("indexed_" + base_symbol.name, base_symbol.type.indexed))

    def visitAssignment(self, expr: Assignment, ctx: ScopeStack) -> None:
        """
        1. Refer to the implementation of visitBinary.
        """
        if isinstance(expr.lhs, Identifier) or isinstance(expr.lhs, ArrayAccess):
            expr.lhs.accept(self, ctx)
            expr.rhs.accept(self, ctx)
        else:
            raise DecafBadAssignTypeError

    def visitUnary(self, expr: Unary, ctx: ScopeStack) -> None:
        expr.operand.accept(self, ctx)

    def visitBinary(self, expr: Binary, ctx: ScopeStack) -> None:
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)

    def visitCondExpr(self, expr: ConditionExpression, ctx: ScopeStack) -> None:
        """
        1. Refer to the implementation of visitBinary.
        """
        expr.cond.accept(self, ctx)
        expr.then.accept(self, ctx)
        expr.otherwise.accept(self, ctx)

    def visitIdentifier(self, ident: Identifier, ctx: ScopeStack) -> None:
        """
        1. Use ctx.lookup to find the symbol corresponding to ident.
        2. If it has not been declared, raise a DecafUndefinedVarError.
        3. Set the 'symbol' attribute of ident.
        """
        varSymbol = ctx.lookup(ident.value)
        if varSymbol is None:
            raise DecafUndefinedVarError(ident.value)
        else:
            ident.setattr('symbol', varSymbol)

    def visitIntLiteral(self, expr: IntLiteral, ctx: ScopeStack) -> None:
        value = expr.value
        if value > MAX_INT:
            raise DecafBadIntValueError(value)
