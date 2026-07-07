class StateManager:
    def __init__(self, filepath : str):
        self.filepath = filepath
        file = open(filepath, "a+")
        file.close()


    def post(self, marker_text: str):
        with open(self.filepath, "w") as file:
            file.write(marker_text)

    def get(self):
        with open(self.filepath, "r") as file:
            return file.read()