class Message:

    def __init__(self, uid, timestamp, sender_name='', content='') -> None:
        super().__init__()
        self.uid = uid
        self.timestamp = timestamp
        self.sender_name = sender_name
        self.content = content
