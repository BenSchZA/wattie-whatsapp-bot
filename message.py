class Message:

    def __init__(self, uid, timestamp, sender_name='', sender_number='', content='') -> None:
        super().__init__()
        self.uid = uid
        self.timestamp = timestamp
        self.sender_name = sender_name
        self.sender_number = sender_number
        self.content = content
