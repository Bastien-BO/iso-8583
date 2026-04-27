"""
All expections
"""


class FieldOutOfRange(ValueError):
    """
    Raised when a bit position exceeds the bitmap capacity.
    """


class FieldValidationError(ValueError):
    """
    Raised when a field value does not match its specification.
    May carry a `partial` dict of subfields that were read successfully
    before the error, useful for partial unpacking.
    """

    def __init__(self, message, partial=None):
        super().__init__(message)
        self.partial = partial
