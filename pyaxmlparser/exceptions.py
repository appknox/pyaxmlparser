class ResParserError(Exception):
    """Base exception for resource parsing errors"""
    pass


class StringBlockError(ResParserError):
    """Exception raised when string block parsing fails"""
    pass


class ChunkError(ResParserError):
    """Exception raised when chunk processing fails"""
    pass


class NamespaceError(ResParserError):
    """Exception raised when namespace processing fails"""
    pass


class AttributeError(ResParserError):
    """Exception raised when attribute parsing fails"""
    pass


class ValidationError(ResParserError):
    """Exception raised when validation fails"""
    pass
