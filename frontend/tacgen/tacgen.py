from ..ast.tree import ArrParameter
from frontend.ast.node import Optional
from frontend.ast.tree import Function, Optional, ExpressionList
from frontend.ast import node
from frontend.ast.tree import *
from frontend.ast.visitor import Visitor
from frontend.symbol.varsymbol import VarSymbol
from frontend.symbol.arrsymbol import ArrSymbol
from frontend.type.array import ArrayType
from utils.label.blocklabel import BlockLabel
from utils.label.funclabel import FuncLabel
from utils.tac import tacop
from utils.tac.temp import Temp
from utils.tac.tacinstr import *
from utils.tac.tacfunc import TACFunc
from utils.tac.globalvar import GlobalVar
from utils.tac.globalarr import GlobalArr
from utils.tac.tacprog import TACProg
from utils.tac.tacvisitor import TACVisitor


"""
The TAC generation phase: translate the abstract syntax tree into three-address code.
"""


class LabelManager:
    """
    A global label manager (just a counter).
    We use this to create unique (block) labels accross functions.
    """

    def __init__(self):
        self.nextTempLabelId = 0

    def freshLabel(self) -> BlockLabel:
        self.nextTempLabelId += 1
        return BlockLabel(str(self.nextTempLabelId))


class TACFuncEmitter(TACVisitor):
    """
    Translates a minidecaf (AST) function into low-level TAC function.
    """

    def __init__(
        self, entry: FuncLabel, numArgs: int, labelManager: LabelManager
    ) -> None:
        self.labelManager = labelManager
        self.func = TACFunc(entry, numArgs)
        self.visitLabel(entry)
        self.nextTempId = 0

        self.continueLabelStack = []
        self.breakLabelStack = []

        self.func.add(DeclParams([Temp(i) for i in range(numArgs)]))

        self.is_rvalue = True

    # To get a fresh new temporary variable.
    def freshTemp(self) -> Temp:
        temp = Temp(self.nextTempId)
        self.nextTempId += 1
        return temp

    # To get a fresh new label (for jumping and branching, etc).
    def freshLabel(self) -> Label:
        return self.labelManager.freshLabel()

    # To count how many temporary variables have been used.
    def getUsedTemp(self) -> int:
        return self.nextTempId

    # In fact, the following methods can be named 'appendXXX' rather than 'visitXXX'.
    # E.g., by calling 'visitAssignment', you add an assignment instruction at the end of current function.
    def visitAssignment(self, dst: Temp, src: Temp) -> Temp:
        self.func.add(Assign(dst, src))
        return src

    def visitLoad(self, value: Union[int, str]) -> Temp:
        temp = self.freshTemp()
        self.func.add(LoadImm4(temp, value))
        return temp

    def visitUnary(self, op: UnaryOp, operand: Temp) -> Temp:
        temp = self.freshTemp()
        self.func.add(Unary(op, temp, operand))
        return temp

    def visitUnarySelf(self, op: UnaryOp, operand: Temp) -> None:
        self.func.add(Unary(op, operand, operand))

    def visitBinary(self, op: BinaryOp, lhs: Temp, rhs: Temp) -> Temp:
        temp = self.freshTemp()
        self.func.add(Binary(op, temp, lhs, rhs))
        return temp

    def visitBinarySelf(self, op: BinaryOp, lhs: Temp, rhs: Temp) -> None:
        self.func.add(Binary(op, lhs, lhs, rhs))

    def visitBranch(self, target: Label) -> None:
        self.func.add(Branch(target))

    def visitCondBranch(self, op: CondBranchOp, cond: Temp, target: Label) -> None:
        self.func.add(CondBranch(op, cond, target))

    def visitReturn(self, value: Optional[Temp]) -> None:
        self.func.add(Return(value))

    def visitCall(self, func: FuncLabel, params: list[Temp]) -> Temp:
        temp = self.freshTemp()
        self.func.add(Call(func, temp, params))
        return temp

    def visitGlobalSymbol(self, symbol: VarSymbol) -> Temp:
        temp = self.freshTemp()
        self.func.add(LoadSymbol(temp, symbol.name))
        return temp

    def visitAddr(self, addr: Temp) -> Temp:
        dst = self.freshTemp()
        self.func.add(Load(dst, addr))
        return dst
    
    def visitAddrAssign(self, addr: Temp, src: Temp, offset: int = 0) -> Temp:
        self.func.add(AddrAssign(addr, src, offset))
        return src

    def visitAlloc(self, size: int) -> Temp:
        temp = self.freshTemp()
        self.func.add(Alloc(temp, size))
        return temp
    
    def visitInitArray(self, addr: Temp, size: int, init_exprs: list[int]) -> None:
        temps = [self.visitLoad(init_expr) for init_expr in init_exprs]
        # Integer division is '//' in Python! Not '/'!!!
        # Otherwise, you will encounter something like 'li t1, 1.0' in TAC.
        len = self.visitLoad(size // 4)
        self.func.add(Memset(addr, len))
        for i, temp in enumerate(temps):
            self.visitAddrAssign(addr, temp, 4 * i)

    def visitLabel(self, label: Label) -> None:
        self.func.add(Mark(label))

    def visitMemo(self, content: str) -> None:
        self.func.add(Memo(content))

    def visitRaw(self, instr: TACInstr) -> None:
        self.func.add(instr)

    def visitEnd(self) -> TACFunc:
        if (len(self.func.instrSeq) == 0) or (not self.func.instrSeq[-1].isReturn()):
            self.func.add(Return(None))
        self.func.tempUsed = self.getUsedTemp()
        return self.func

    # To open a new loop (for break/continue statements)
    def openLoop(self, breakLabel: Label, continueLabel: Label) -> None:
        self.breakLabelStack.append(breakLabel)
        self.continueLabelStack.append(continueLabel)

    # To close the current loop.
    def closeLoop(self) -> None:
        self.breakLabelStack.pop()
        self.continueLabelStack.pop()

    # To get the label for 'break' in the current loop.
    def getBreakLabel(self) -> Label:
        return self.breakLabelStack[-1]

    # To get the label for 'continue' in the current loop.
    def getContinueLabel(self) -> Label:
        return self.continueLabelStack[-1]


class TACGen(Visitor[TACFuncEmitter, None]):
    # Entry of this phase
    def transform(self, program: Program) -> TACProg:
        labelManager = LabelManager()

        # Global functions
        tacFuncs = []
        for funcName, astFunc in program.functions().items():
            # in step9, you need to use real parameter count
            emitter = TACFuncEmitter(FuncLabel(funcName), len(astFunc.params), labelManager)
            astFunc.params.accept(self, emitter)
            astFunc.body.accept(self, emitter)
            tacFuncs.append(emitter.visitEnd())

        # Global variables
        globalVars = []
        for var in program.var_declarations().values():
            init_value = None
            if var.init_expr != NULL:
                init_value = var.init_expr.value
            globalVars.append(GlobalVar(var.getattr('symbol').name, init_value, var.getattr('symbol').type.size))
        
        # Global arrays
        globalArrs = []
        for arr in program.arr_declarations().values():
            init_values = None
            if arr.init_exprs != NULL:
                init_values = arr.init_exprs
            globalArrs.append(GlobalArr(arr.getattr('symbol').name, init_values, arr.getattr('symbol').type.size))
        
        return TACProg(tacFuncs, globalVars, globalArrs)

    def visitBlock(self, block: Block, mv: TACFuncEmitter) -> None:
        for child in block:
            child.accept(self, mv)

    def visitReturn(self, stmt: Return, mv: TACFuncEmitter) -> None:
        stmt.expr.accept(self, mv)
        mv.visitReturn(stmt.expr.getattr("val"))

    def visitBreak(self, stmt: Break, mv: TACFuncEmitter) -> None:
        mv.visitBranch(mv.getBreakLabel())
    
    def visitContinue(self, stmt: Continue, mv: TACFuncEmitter) -> None:
        mv.visitBranch(mv.getContinueLabel())

    def visitIdentifier(self, ident: Identifier, mv: TACFuncEmitter) -> None:
        """
        1. Set the 'val' attribute of ident as the temp variable of the 'symbol' attribute of ident.
        """
        if ident.getattr('symbol').isGlobal:
            if isinstance(ident.getattr('symbol'), VarSymbol):
                global_var_addr = mv.visitGlobalSymbol(ident.getattr('symbol'))
                ident.getattr('symbol').temp = global_var_addr
                if mv.is_rvalue:
                    ident.setattr('val', mv.visitAddr(global_var_addr))
            if isinstance(ident.getattr('symbol'), ArrSymbol):
                global_arr_addr = mv.visitGlobalSymbol(ident.getattr('symbol'))
                ident.getattr('symbol').addr = global_arr_addr
                if mv.is_rvalue:
                    ident.setattr('val', global_arr_addr)
        else:
            if mv.is_rvalue:
                if isinstance(ident.getattr('symbol'), VarSymbol):
                    ident.setattr('val', ident.getattr('symbol').temp)
                if isinstance(ident.getattr('symbol'), ArrSymbol):
                    ident.setattr('val', ident.getattr('symbol').addr)

    def visitVarParameter(self, param: VarParameter, mv: TACFuncEmitter) -> None:
        varSymbol = param.getattr('symbol')
        varSymbol.temp = mv.freshTemp()
        param.setattr('val', varSymbol.temp)
    
    def visitArrParameter(self, param: ArrParameter, mv: TACFuncEmitter) -> None:
        arrSymbol = param.getattr('symbol')
        arrSymbol.addr = mv.freshTemp()
        param.setattr('val', arrSymbol.addr)

    def visitParameterList(self, params: ParameterList, mv: TACFuncEmitter) -> None:
        for param in params:
            param.accept(self, mv)

    def visitCall(self, call: Call, mv: TACFuncEmitter) -> None:
        for arg in call.argument_list:
            arg.accept(self, mv)
        varSymbol = call.getattr('symbol')
        varSymbol.temp = mv.visitCall(
            FuncLabel(call.ident.value), [arg.getattr('val') for arg in call.argument_list]
        )
        call.setattr('val', varSymbol.temp)

    def visitVarDeclaration(self, decl: VarDeclaration, mv: TACFuncEmitter) -> None:
        """
        1. Get the 'symbol' attribute of decl.
        2. Use mv.freshTemp to get a new temp variable for this symbol.
        3. If the declaration has an initial value, use mv.visitAssignment to set it.
        """
        varSymbol = decl.getattr('symbol')
        varSymbol.temp = mv.freshTemp()
        if not decl.init_expr is NULL:
            decl.init_expr.accept(self, mv)
            tempVarInitExpr = decl.init_expr.getattr('val')
            mv.visitAssignment(varSymbol.temp, tempVarInitExpr)

    def visitArrDeclaration(self, decl: ArrDeclaration, mv: TACFuncEmitter) -> None:
        arrSymbol = decl.getattr('symbol')
        arrSymbol.addr = mv.visitAlloc(arrSymbol.type.size)
        if len(decl.init_exprs) > 0:
            mv.visitInitArray(arrSymbol.addr, arrSymbol.type.size, decl.init_exprs)

    def visitArrayAccess(self, expr: ArrayAccess, mv: TACFuncEmitter) -> None:

        is_rvalue = mv.is_rvalue
        mv.is_rvalue = False
        expr.base.accept(self, mv)

        mv.is_rvalue = True
        expr.index.accept(self, mv)

        base_symbol = expr.base.getattr('symbol')
        expr.getattr('symbol').addr = mv.visitBinary(
            tacop.TacBinaryOp.ADD,
            base_symbol.addr,
            mv.visitBinary(
                tacop.TacBinaryOp.MUL,
                expr.index.getattr("val"),
                mv.visitLoad(expr.getattr('symbol').type.size)
            )
        )

        if is_rvalue:
            if isinstance(expr.getattr('symbol').type, ArrayType):
                raise DecafBadOperationTypeError
            expr.setattr('val', mv.visitAddr(expr.getattr('symbol').addr))

    def visitAssignment(self, expr: Assignment, mv: TACFuncEmitter) -> None:
        """
        1. Visit the right hand side of expr, and get the temp variable of left hand side.
        2. Use mv.visitAssignment to emit an assignment instruction.
        3. Set the 'val' attribute of expr as the value of assignment instruction.
        """
        expr.rhs.accept(self, mv)
        tempVarRHS = expr.rhs.getattr("val")
        mv.is_rvalue = False

        expr.lhs.accept(self, mv)
        tempVarLHS = expr.lhs.getattr('symbol').addr \
            if isinstance(expr.lhs.getattr('symbol'), ArrSymbol) \
                else expr.lhs.getattr('symbol').temp
        mv.is_rvalue = True

        if isinstance(expr.lhs.getattr('symbol').type, ArrayType):
            raise DecafBadOperationTypeError

        if isinstance(expr.lhs.getattr('symbol'), ArrSymbol):
            result = mv.visitAddrAssign(tempVarLHS, tempVarRHS)
        else:
            if expr.lhs.getattr('symbol').isGlobal:
                result = mv.visitAddrAssign(tempVarLHS, tempVarRHS)
            else:
                result = mv.visitAssignment(tempVarLHS, tempVarRHS)
        expr.setattr('val', result)

    def visitIf(self, stmt: If, mv: TACFuncEmitter) -> None:
        stmt.cond.accept(self, mv)

        if stmt.otherwise is NULL:
            skipLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitLabel(skipLabel)
        else:
            skipLabel = mv.freshLabel()
            exitLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitBranch(exitLabel)
            mv.visitLabel(skipLabel)
            stmt.otherwise.accept(self, mv)
            mv.visitLabel(exitLabel)

    def visitWhile(self, stmt: While, mv: TACFuncEmitter) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        mv.visitLabel(beginLabel)
        stmt.cond.accept(self, mv)
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)

        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitFor(self, stmt: For, mv: TACFuncEmitter) -> None:
        stmt.init.accept(self, mv)

        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        mv.visitLabel(beginLabel)
        stmt.cond.accept(self, mv)
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)
        
        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        stmt.update.accept(self, mv)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitUnary(self, expr: Unary, mv: TACFuncEmitter) -> None:
        expr.operand.accept(self, mv)

        op = {
            node.UnaryOp.Neg: tacop.TacUnaryOp.NEG,
            # You can add unary operations here.
            node.UnaryOp.BitNot: tacop.TacUnaryOp.NOT,
            node.UnaryOp.LogicNot: tacop.TacUnaryOp.LNOT,
        }[expr.op]
        expr.setattr("val", mv.visitUnary(op, expr.operand.getattr("val")))

    def visitBinary(self, expr: Binary, mv: TACFuncEmitter) -> None:
        expr.lhs.accept(self, mv)
        expr.rhs.accept(self, mv)

        op = {
            # Arithmetic Operators
            node.BinaryOp.Add: tacop.TacBinaryOp.ADD,
            node.BinaryOp.Sub: tacop.TacBinaryOp.SUB,
            node.BinaryOp.Mul: tacop.TacBinaryOp.MUL,
            node.BinaryOp.Div: tacop.TacBinaryOp.DIV,
            node.BinaryOp.Mod: tacop.TacBinaryOp.MOD,
            # Comparison Operators
            node.BinaryOp.EQ: tacop.TacBinaryOp.EQ,
            node.BinaryOp.NE: tacop.TacBinaryOp.NE,
            node.BinaryOp.LT: tacop.TacBinaryOp.LT,
            node.BinaryOp.LE: tacop.TacBinaryOp.LE,
            node.BinaryOp.GT: tacop.TacBinaryOp.GT,
            node.BinaryOp.GE: tacop.TacBinaryOp.GE,
            # Logical Operators
            node.BinaryOp.LogicAnd: tacop.TacBinaryOp.LAND,
            node.BinaryOp.LogicOr: tacop.TacBinaryOp.LOR,
            # You can add binary operations here.
            # Bitwise Operators
            node.BinaryOp.BitAnd: tacop.TacBinaryOp.AND,
            node.BinaryOp.BitOr: tacop.TacBinaryOp.OR,
            node.BinaryOp.Xor: tacop.TacBinaryOp.XOR,
        }[expr.op]
        expr.setattr(
            "val", mv.visitBinary(op, expr.lhs.getattr("val"), expr.rhs.getattr("val"))
        )

    def visitCondExpr(self, expr: ConditionExpression, mv: TACFuncEmitter) -> None:
        """
        1. Refer to the implementation of visitIf and visitBinary.
        """
        expr.cond.accept(self, mv)
        
        skipLabel = mv.freshLabel()
        exitLabel = mv.freshLabel()
        mv.visitCondBranch(
            tacop.CondBranchOp.BEQ, expr.cond.getattr("val"), skipLabel
        )

        # Temp variable for the result
        tempVar = mv.freshTemp()

        # The 'then' branch
        expr.then.accept(self, mv)
        mv.visitAssignment(tempVar, expr.then.getattr('val'))
        mv.visitBranch(exitLabel)

        # The 'otherwise' branch
        mv.visitLabel(skipLabel)
        expr.otherwise.accept(self, mv)
        mv.visitAssignment(tempVar, expr.otherwise.getattr('val'))
        mv.visitLabel(exitLabel)

        # Assign the temp variable to the expression
        expr.setattr('val', tempVar)

    def visitIntLiteral(self, expr: IntLiteral, mv: TACFuncEmitter) -> None:
        expr.setattr("val", mv.visitLoad(expr.value))
