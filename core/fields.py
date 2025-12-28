from django.contrib.postgres.search import SearchVectorField


class OptionalSearchVectorField(SearchVectorField):
    """SearchVectorField compativel com SQLite (armazenado como texto)."""

    def db_type(self, connection):
        if connection.vendor != "postgresql":
            return "text"
        return super().db_type(connection)
