class GlobalArr:
    def __init__(self, name: str, value: list[int] | None, size: int = 4) -> None:
        self.name = name
        self.size = size
        if value is None:
            self.m_value = [0] * (size // 4)
            self.initialized = False
        else:
            self.m_value = [0] * (size // 4)
            for i in range(len(value)):
                self.m_value[i] += value[i]
            self.initialized = True
    
    @property
    def value(self) -> str:
        return ", ".join(map(str, self.m_value))

    def printTo(self) -> None:
        if self.initialized:
            print(f"    {self.name} = {self.m_value}")
        else:
            print(f"    {self.name} = ?")
