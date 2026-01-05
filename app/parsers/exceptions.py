class ColumnsError(Exception):
    """Raised when parsing input data with columns deviating from expectation"""

class DateRangeError(Exception):
    """Raised when parsing input data deviating from expected date range"""

class TimeFormatError(Exception):
    """Raised when parsing input data deviating grom expected date format"""