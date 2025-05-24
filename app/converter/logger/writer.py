"""
Logger writer module.

This module provides a file-like object that writes to a logger.
"""

import io


class LoggerWriter(io.TextIOBase):
    """
    A file-like object that writes to a logger.

    This class is used to redirect subprocess output directly to a logger.
    """

    def __init__(self, logger, prefix=""):
        """
        Initialize the LoggerWriter.

        Args:
            logger: The logger to write to
            prefix (str): A prefix to add to each log message
        """
        self.logger = logger
        self.prefix = prefix
        self.buffer = ""

    def write(self, data):
        """
        Write data to the logger.

        Args:
            data: The data to write

        Returns:
            int: The number of characters written
        """
        if data:
            # Buffer the data until we get a newline
            self.buffer += data
            if '\n' in self.buffer:
                lines = self.buffer.splitlines()
                # Keep the last line if it doesn't end with a newline
                if self.buffer.endswith('\n'):
                    self.buffer = ""
                    for line in lines:
                        if line:  # Skip empty lines
                            self.logger.info(f"{self.prefix}{line}")
                else:
                    self.buffer = lines[-1]
                    for line in lines[:-1]:
                        if line:  # Skip empty lines
                            self.logger.info(f"{self.prefix}{line}")
            return len(data)
        return 0

    def flush(self):
        """Flush the buffer."""
        if self.buffer:
            self.logger.info(f"{self.prefix}{self.buffer}")
            self.buffer = ""
