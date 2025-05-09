import logging
from typing import Dict, List, Any, Optional

import psycopg2
import psycopg2.extras

from core.config import Settings

logger = logging.getLogger(__name__)

class DBSchemaManager:
    """
    Manages fetching and representing the schema of the user's PostgreSQL database.
    """

    def __init__(self, settings: Settings):
        """
        Initializes the SchemaManager with database connection details from settings.

        Args:
            settings: The application settings object containing database configuration.
        """
        self._settings = settings
        self._db_url = settings.DATABASE_URL
        if not self._db_url:
            logger.error("DATABASE_URL is not configured. Schema manager cannot connect.")
            # Depending on strictness, you might raise an error here
            # raise ValueError("DATABASE_URL is not configured")

    def _connect(self):
        """Establishes a connection to the PostgreSQL database."""
        if not self._db_url:
            raise ConnectionError("Database connection URL is not configured.")
        try:
            conn = psycopg2.connect(self._db_url)
            logger.info("Successfully connected to the database.")
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            raise ConnectionError(f"Could not connect to database: {e}") from e

    def get_schema(self) -> Optional[str]:
        """
        Fetches the database schema (tables, columns, types, relationships)
        and returns it as a structured string suitable for LLM prompts.

        Returns:
            A string representation of the schema, or None if connection/fetch fails.
        """
        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            schema_info: Dict[str, Any] = {}

            # 1. Fetch tables and columns
            cursor.execute("""
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM
                    information_schema.columns
                WHERE
                    table_schema = 'public' -- Assuming 'public' schema, adjust if needed
                ORDER BY
                    table_name, ordinal_position;
            """)
            columns_data = cursor.fetchall()

            tables: Dict[str, Dict[str, Any]] = {}
            for row in columns_data:
                table_name = row['table_name']
                if table_name not in tables:
                    tables[table_name] = {'columns': []}
                tables[table_name]['columns'].append({
                    'column_name': row['column_name'],
                    'data_type': row['data_type'],
                    'is_nullable': row['is_nullable'] == 'YES',
                    'column_default': row['column_default']
                })

            schema_info['tables'] = tables

            # 2. Fetch primary keys
            cursor.execute("""
                SELECT
                    kcu.table_name,
                    kcu.column_name
                FROM
                    information_schema.table_constraints tc
                JOIN
                    information_schema.key_column_usage kcu
                ON
                    tc.constraint_name = kcu.constraint_name
                WHERE
                    tc.constraint_type = 'PRIMARY KEY'
                    AND kcu.table_schema = 'public'; -- Assuming 'public' schema
            """)
            pk_data = cursor.fetchall()
            for row in pk_data:
                table_name = row['table_name']
                column_name = row['column_name']
                if table_name in tables:
                    for col in tables[table_name]['columns']:
                        if col['column_name'] == column_name:
                            col['is_primary_key'] = True
                            break

            # 3. Fetch foreign keys (relationships)
            relationships: List[Dict[str, str]] = []
            cursor.execute("""
                SELECT
                    kcu.table_name AS from_table,
                    kcu.column_name AS from_column,
                    ccu.table_name AS to_table,
                    ccu.column_name AS to_column
                FROM
                    information_schema.table_constraints tc
                JOIN
                    information_schema.key_column_usage kcu
                ON
                    tc.constraint_name = kcu.constraint_name
                JOIN
                    information_schema.constraint_column_usage ccu
                ON
                    tc.constraint_name = ccu.constraint_name
                WHERE
                    tc.constraint_type = 'FOREIGN KEY'
                    AND kcu.table_schema = 'public'; -- Assuming 'public' schema
            """)
            fk_data = cursor.fetchall()
            for row in fk_data:
                 relationships.append({
                    'from_table': row['from_table'],
                    'from_column': row['from_column'],
                    'to_table': row['to_table'],
                    'to_column': row['to_column']
                 })

            schema_info['relationships'] = relationships

            # Format for LLM
            schema_string = self._format_schema_for_llm(schema_info)

            logger.info("Successfully fetched and formatted schema.")
            return schema_string

        except ConnectionError:
            # Connection error already logged in _connect
            return None
        except psycopg2.Error as e:
            logger.error(f"Database query failed during schema fetching: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during schema fetching: {e}")
            return None
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed.")

    def _format_schema_for_llm(self, schema_info: Dict[str, Any]) -> str:
        """
        Formats the fetched schema information into a string suitable for LLM prompts.

        Args:
            schema_info: Dictionary containing schema details (tables, relationships).

        Returns:
            A string representation of the schema.
        """
        formatted_string = "Database Schema:\n\n"

        # Add tables and columns
        formatted_string += "Tables:\n"
        for table_name, table_data in schema_info.get('tables', {}).items():
            formatted_string += f"- {table_name}:\n"
            for col in table_data.get('columns', []):
                col_details = f"  - {col['column_name']} ({col['data_type']}"
                if col.get('is_primary_key'):
                    col_details += ", PK"
                if col.get('is_nullable') is False:
                     col_details += ", NOT NULL"
                if col.get('column_default') is not None:
                     col_details += f", DEFAULT {col['column_default']}"

                # Check if this column is the 'from' side of any relationship
                is_fk = False
                for rel in schema_info.get('relationships', []):
                    if rel['from_table'] == table_name and rel['from_column'] == col['column_name']:
                        col_details += f", FK -> {rel['to_table']}.{rel['to_column']}"
                        is_fk = True
                        break # Assume one FK per column for simplicity in this format

                col_details += ")"
                formatted_string += col_details + "\n"
        formatted_string += "\n"

        # Add relationships explicitly
        if schema_info.get('relationships'):
            formatted_string += "Relationships (Foreign Keys):\n"
            for rel in schema_info['relationships']:
                formatted_string += f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}\n"
            formatted_string += "\n"

        formatted_string += "---" # Separator

        return formatted_string

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # This requires a running PostgreSQL DB and appropriate .env settings
    # Example .env (replace with your actual DB details):
    # DATABASE_URL="postgresql://user:password@host:port/dbname"
    # Or individual components:
    # DB_HOST=localhost
    # DB_PORT=5432
    # DB_NAME=mydatabase
    # DB_USER=myuser
    # DB_PASSWORD=mypassword

    # Need to load settings first
    from core.config import load_settings
    import os

    # Configure basic logging for the example
    logging.basicConfig(level=logging.INFO)

    # Create a dummy .env file for testing if it doesn't exist
    if not os.path.exists(".env"):
        print("Creating a dummy .env file for testing. Please update with your DB details.")
        with open(".env", "w") as f:
            f.write("DATABASE_URL=postgresql://user:password@localhost:5432/testdb\n")
            f.write("OPENAI_API_KEY=dummy_key\n") # LLM key needed by settings

    try:
        # Load settings from .env (and config.yaml if present)
        app_settings = load_settings()

        if not app_settings.DATABASE_URL:
             print("\nDATABASE_URL is not set in .env or config.yaml. Cannot test schema manager.")
             print("Please configure your PostgreSQL database connection details.")
        else:
            print(f"\nAttempting to connect to: {app_settings.DATABASE_URL}")
            schema_manager = DBSchemaManager(app_settings)
            schema_string = schema_manager.get_schema()

            if schema_string:
                print("\n--- Fetched Database Schema ---")
                print(schema_string)
            else:
                print("\nFailed to fetch database schema.")

    except Exception as e:
        print(f"\nAn error occurred during schema manager test: {e}")

    # Clean up dummy .env if created
    if os.path.exists(".env") and "dummy_key" in open(".env").read():
         print("Removing dummy .env file.")
         os.remove(".env")