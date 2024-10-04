class GlobalVar:
    def __init__(self, name: str, value: int | None) -> None:
        self.name = name
        if value is None:
            self.value = 0
            self.initialized = False
        else:
            self.value = value
            self.initialized = True

    def printTo(self) -> None:
        if self.initialized:
            print(f"    {self.name} = {self.value}")
        else:
            print(f"    {self.name} = ?")
