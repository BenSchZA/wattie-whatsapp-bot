class Delivery:

    def __init__(self, number=None, txt='', url=None, media=None, filename=None) -> None:
        super().__init__()
        self.number = number
        self.txt = txt
        self.url = url
        self.media = media
        self.filename = filename

    def set_number(self, number):
        self.number = number
        return self
