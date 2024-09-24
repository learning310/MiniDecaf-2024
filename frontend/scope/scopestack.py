from typing import Optional

from frontend.symbol.symbol import Symbol

from .scope import Scope, ScopeKind

class ScopeStack:
    # Basic data structure of stack
    def __init__(self, scope: Scope) -> None:
        self.stk = [scope]
    
    def push(self, scope: Scope) -> None:
        self.stk.append(scope)
    
    def pop(self) -> None:
        self.stk.pop()
    
    def top(self) -> Scope:
        return self.stk[-1]
    
    def top2(self) -> Scope:
        return self.stk[-2]
    
    def bottom(self) -> Scope:
        return self.stk[0]
    
    def size(self) -> int:
        return len(self.stk)
    
    def empty(self) -> bool:
        return len(self.stk) == 0

    # To create a new scope
    def newScope(self, is_func: bool = False) -> None:
        current_loop_count = self.top().loop_count
        self.push(Scope(ScopeKind.LOCAL, is_func))
        self.top().loop_count = current_loop_count
    
    # To get a symbol in all scopes, from backward 
    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.stk):
            if scope.containsKey(name):
                return scope.get(name)
        return None
    
    # Increase the loop count of the top scope
    def increaseLoop(self) -> None:
        self.top().loop_count += 1

    # Decrease the loop count of the top scope
    def decreaseLoop(self) -> None:
        self.top().loop_count -= 1

    def __str__(self) -> str:
        res = []
        for i in range(len(self.stk)):
            res.append(f"Scope {i}: {self.stk[i].symbols}")
        return str(res)