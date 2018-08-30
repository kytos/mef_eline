"""MEF Eline Exceptions."""


class MEFELineException(Exception):
    """MEF Eline Base Exception."""

    pass


class EVCException(MEFELineException):
    """EVC Exception."""

    pass


class ValidationException(EVCException):
    """Exception for validation errors."""

    pass
