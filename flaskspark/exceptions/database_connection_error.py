"""Database connection error for FlaskSpark."""

class DatabaseConnectionError(Exception):
    """Raised when FlaskSpark cannot connect to the configured database."""
    def __str__(self):
        """
        Return a user-friendly error message.

        Args:
            None

        Returns:
            str: Error message.
        """
        return "The database connection could not be established. Please check your configuration."
