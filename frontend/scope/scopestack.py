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
    
    def size(self) -> int:
        return len(self.stk)
    
    def empty(self) -> bool:
        return len(self.stk) == 0

    # To create a new scope
    def newScope(self) -> None:
        self.push(Scope(ScopeKind.LOCAL))
    
    # To get a symbol in all scopes, from backward 
    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.stk):
            if scope.containsKey(name):
                return scope.get(name)
        return None