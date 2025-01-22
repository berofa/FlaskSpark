class DatabaseConnectionError(Exception):
    def __str__(self):
        return "The database connection could not be established. Please check your configuration."