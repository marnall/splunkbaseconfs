class VTConfigException(Exception):
    pass

class VTException(Exception):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.args[0]} | details={self.details}"
        return self.args[0]
    
    def __repr__(self):
        return f"VTException(message={self.message!r}, details={self.details!r})"

class VTAPIException(Exception):

  def __init__(self, code: str, message: str):
    self.code = code
    self.message = message
    super().__init__(code, message)