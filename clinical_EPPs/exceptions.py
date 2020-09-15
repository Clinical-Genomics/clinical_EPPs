
class Clinical_EPPsError(Exception):
    def __init__(self, message):
        self.message = message

class QueueArtifactsError(Clinical_EPPsError):
    pass


