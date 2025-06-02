class ResParserError(Exception):
    """Exception raised when parsing Android resource files fails."""
    pass


class BufferUnderrunError(ResParserError):
    """Exception raised when trying to read beyond available buffer data."""
    pass


class InvalidStringPoolError(ResParserError):
    """Exception raised when string pool data is invalid or corrupted."""
    pass


class InvalidChunkError(ResParserError):
    """Exception raised when chunk header or data is invalid."""
    pass
