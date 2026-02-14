"""Database incomplete error for FlaskSpark."""

class DatabaseIncompleteError(Exception):
    """Raised when the database is missing required tables."""
    def __init__(self, missing_tables):
        """
        Initializes the exception with details about the missing tables.

        Args:
            missing_tables (list): List of missing table names.

        Returns:
            None
        """
        self.missing_tables = missing_tables

    def __str__(self):
        """
        Returns a formatted error message.

        Args:
            None

        Returns:
            str: Human-readable error message.
        """
        return (
            "The database is incomplete. The following tables are missing:\n"
            "  " + f"{', '.join(self.missing_tables)}\n\n"
            "To resolve this issue, run the following command:\n"
            "  flask db upgrade\n\n"
            "This will apply the necessary migrations to bring your database up to date.\n"
            "Important: Create a backup of your database befor running this command!"
        )
