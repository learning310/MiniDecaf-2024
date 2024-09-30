from backend.dataflow.cfg import CFG
from backend.dataflow.cfgbuilder import CFGBuilder
from backend.dataflow.livenessanalyzer import LivenessAnalyzer
from backend.reg.bruteregalloc import BruteRegAlloc
from backend.riscv.riscvasmemitter import RiscvAsmEmitter
from utils.tac.tacprog import TACProg
from utils.riscv import Riscv

"""
Asm: we use it to generate all the asm code for the program
"""

class Asm:
    def __init__(self, emitter: RiscvAsmEmitter, reg_alloc: BruteRegAlloc) -> None:
        self.emitter = emitter
        self.reg_alloc = reg_alloc

    def transform(self, prog: TACProg):
        analyzer = LivenessAnalyzer()
        
        for func in prog.funcs:
            pair = self.emitter.selectInstr(func)
            builder = CFGBuilder()
            cfg: CFG = builder.buildFrom(pair[0])
            analyzer.accept(cfg)
            self.reg_alloc.accept(cfg, pair[1])

        return self.emitter.emitEnd()
