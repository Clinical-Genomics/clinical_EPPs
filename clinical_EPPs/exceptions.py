
class Clinical_EPPsError(Exception):
    def __init__(self, message):
        self.message = message

class QueueArtifactsError(Clinical_EPPsError):
    pass

class DuplicateSampleError(Clinical_EPPsError):
    pass

class MissingArtifactError(Clinical_EPPsError):
    pass

class WhatToCallThisError(Clinical_EPPsError):
    pass


