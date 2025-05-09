import logging
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from typing import List, Dict, Any, Optional

from core.config import settings # Assuming core.config is correctly set up

logger = logging.getLogger(__name__)

class SQLExecutionError(Exception):
    """Custom exception for SQL execution errors."""
    def __init__(self, message: str, original_error: Optional[Exception] = None, sql_query: Optional[str] = None):
        self.message = message
        self.original_error = original_error
        self.sql_query = sql_query
        super().__init__(self.message)

    def __str__(self):
        error_str = self.message
        if self.sql_query:
            error_str += f"\nSQL Query: {self.sql_query}"
        if self.original_error:
            error_str += f"\nOriginal Error: {self.original_error}"
        return error_str

class SQLExecutionModule:
    """
    Module responsible for connecting to and executing SQL queries against
    the user's PostgreSQL database.
    """
    _pool: Optional[SimpleConnectionPool] = None

    def __init__(self):
        """
        Initializes the SQL Execution Module.
        Ensures the connection pool is set up.
        """
        if SQLExecutionModule._pool is None:
            self._setup_connection_pool()

        self.pool = SQLExecutionModule._pool
        self.timeout_ms = settings.SQL_TIMEOUT_SECONDS * 1000
        self.max_rows_returned = settings.SQL_MAX_ROWS_RETURNED

    def _setup_connection_pool(self):
        """Sets up the PostgreSQL connection pool."""
        db_url = settings.DATABASE_URL
        if not db_url:
            # Assemble from components if URL is not provided
            if all([settings.DB_USER, settings.DB_HOST, settings.DB_NAME]):
                 password_part = f":{settings.DB_PASSWORD}" if settings.DB_PASSWORD else ""
                 port_part = f":{settings.DB_PORT}" if settings.DB_PORT is not None else ""
                 db_url = f"postgresql://{settings.DB_USER}{password_part}@{settings.DB_HOST}{port_part}/{settings.DB_NAME}"

        if not db_url:
            logger.error("Database connection details are not configured.")
            raise SQLExecutionError("Database connection details are not configured.")

        try:
            # Using SimpleConnectionPool for basic pooling
            # minconn and maxconn can be configured via settings if needed
            SQLExecutionModule._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10, # Default pool size, can be moved to config
                dsn=db_url
            )
            logger.info("Database connection pool created successfully.")
        except psycopg2.Error as e:
            logger.error(f"Failed to create database connection pool: {e}", exc_info=True)
            raise SQLExecutionError("Failed to connect to the database.", original_error=e)
        except Exception as e:
            logger.error(f"An unexpected error occurred during database pool setup: {e}", exc_info=True)
            raise SQLExecutionError("An unexpected error occurred during database setup.", original_error=e)


    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Executes a given SQL query against the configured database.

        Args:
            sql_query: The SQL query string to execute.

        Returns:
            A list of dictionaries representing the query results for SELECT queries.
            For non-SELECT queries, returns an empty list or a success indicator
            (design choice, returning empty list for simplicity now).

        Raises:
            SQLExecutionError: If the query execution fails.
        """
        if not self.pool:
             raise SQLExecutionError("Database connection pool is not initialized.")

        conn = None
        cursor = None
        results: List[Dict[str, Any]] = []

        try:
            # Get a connection from the pool
            conn = self.pool.getconn()
            # Use DictCursor to get results as dictionaries
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # Set statement timeout
            # Timeout is in milliseconds for statement_timeout
            cursor.execute("SET statement_timeout TO %s;", (self.timeout_ms,))

            logger.debug(f"Executing SQL query: {sql_query}")
            cursor.execute(sql_query)

            # Check if the query is a SELECT statement to fetch results
            # This is a simple check and might not cover all cases (e.g., CTEs)
            # A more robust check might involve parsing the query or relying on
            # cursor.description being not None.
            if cursor.description is not None:
                # It's likely a SELECT or similar query returning rows
                results = [dict(row) for row in cursor.fetchall()]
                logger.debug(f"Fetched {len(results)} rows.")

                # Optional: Log a warning if results exceed max_rows_returned
                if len(results) > self.max_rows_returned:
                     logger.warning(f"Query returned {len(results)} rows, exceeding the configured limit of {self.max_rows_returned}.")
                     # Note: We are not truncating here, just warning.
                     # Truncation logic should ideally be handled by the caller
                     # or the SQL generation step (using LIMIT).

            else:
                # It's likely an INSERT, UPDATE, DELETE, DDL, etc.
                # Commit the transaction for non-SELECT statements
                conn.commit()
                logger.debug(f"Executed non-SELECT query. Rows affected: {cursor.rowcount}")
                # Return empty list or a status message for non-SELECT
                results = [] # Indicate success but no data rows

        except psycopg2.errors.QueryCanceled as e:
             logger.warning(f"SQL query timed out after {settings.SQL_TIMEOUT_SECONDS} seconds: {sql_query}", exc_info=True)
             # Rollback on timeout
             if conn:
                 conn.rollback()
             raise SQLExecutionError(
                 f"SQL query timed out after {settings.SQL_TIMEOUT_SECONDS} seconds.",
                 original_error=e,
                 sql_query=sql_query
             ) from e
        except psycopg2.Error as e:
            # Catch specific psycopg2 errors (syntax, connection, etc.)
            logger.error(f"Database error during SQL execution: {e}", exc_info=True)
            # Rollback the transaction on error
            if conn:
                conn.rollback()
            raise SQLExecutionError(
                f"Database error executing query: {e}",
                original_error=e,
                sql_query=sql_query
            ) from e
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"An unexpected error occurred during SQL execution: {e}", exc_info=True)
            # Rollback the transaction on error
            if conn:
                conn.rollback()
            raise SQLExecutionError(
                f"An unexpected error occurred during query execution: {e}",
                original_error=e,
                sql_query=sql_query
            ) from e
        finally:
            # Ensure cursor and connection are closed and returned to the pool
            if cursor:
                cursor.close()
            if conn:
                self.pool.putconn(conn)
                logger.debug("Connection returned to pool.")

        return results

# Example Usage (for testing the module directly)
if __name__ == "__main__":
    # This block requires a running PostgreSQL DB and appropriate .env/config.yaml
    # For testing, you might need to set up a dummy DB and configure settings.
    # Example .env content:
    # DATABASE_URL=postgresql://user:password@host:port/dbname
    # Or individual components:
    # DB_USER=myuser
    # DB_PASSWORD=mypassword
    # DB_HOST=localhost
    # DB_PORT=5432
    # DB_NAME=mydatabase

    # Ensure logging is configured for standalone test
    logging.basicConfig(level=logging.DEBUG)

    try:
        # Instantiate the module
        sql_executor = SQLExecutionModule()

        # --- Test Case 1: Valid SELECT query ---
        print("\n--- Testing Valid SELECT Query ---")
        # Replace with a valid query for your test DB
        test_select_query = "SELECT 1 as id, 'test' as name;"
        # Or a real query if you have a test DB set up:
        # test_select_query = "SELECT column1, column2 FROM your_table LIMIT 5;"
        try:
            select_results = sql_executor.execute_query(test_select_query)
            print("Query successful. Results:")
            for row in select_results:
                print(row)
        except SQLExecutionError as e:
            print(f"Error executing SELECT query: {e}")

        # --- Test Case 2: Invalid SQL query (syntax error) ---
        print("\n--- Testing Invalid SQL Query ---")
        test_invalid_query = "SELECT * FROM non_existent_table WHERE syntax error;"
        try:
            invalid_results = sql_executor.execute_query(test_invalid_query)
            print("Invalid query test unexpectedly succeeded.")
        except SQLExecutionError as e:
            print(f"Caught expected error for invalid query: {e}")
        except Exception as e:
             print(f"Caught unexpected exception for invalid query: {e}")


        # --- Test Case 3: Non-SELECT query (e.g., CREATE TABLE - requires permissions) ---
        # This test might fail depending on the DB user's permissions.
        # It also creates a dummy table, so be careful running this.
        print("\n--- Testing Non-SELECT Query (CREATE TABLE) ---")
        test_create_table_query = "CREATE TEMPORARY TABLE test_temp_table (id INT PRIMARY KEY, name VARCHAR(50));"
        try:
            print(f"Attempting to execute: {test_create_table_query}")
            create_results = sql_executor.execute_query(test_create_table_query)
            print("CREATE TABLE query successful.")
            # Clean up the temporary table if needed (though temporary tables are session-scoped)
            # sql_executor.execute_query("DROP TABLE test_temp_table;")
            # print("Dropped test_temp_table.")
        except SQLExecutionError as e:
            print(f"Error executing CREATE TABLE query (may be permission issue): {e}")
        except Exception as e:
             print(f"Caught unexpected exception for CREATE TABLE query: {e}")

        # --- Test Case 4: Query that might timeout (if timeout is short) ---
        # This requires a query that takes longer than SQL_TIMEOUT_SECONDS
        # Example: SELECT pg_sleep(5); if timeout is 3 seconds
        print("\n--- Testing Query Timeout ---")
        # Ensure SQL_TIMEOUT_SECONDS in config is set appropriately (e.g., 3)
        # and the sleep duration is longer (e.g., 5)
        test_timeout_query = "SELECT pg_sleep(5);"
        try:
            print(f"Attempting to execute query that should timeout: {test_timeout_query}")
            timeout_results = sql_executor.execute_query(test_timeout_query)
            print("Timeout query test unexpectedly succeeded.")
        except SQLExecutionError as e:
            print(f"Caught expected timeout error: {e}")
        except Exception as e:
             print(f"Caught unexpected exception for timeout query: {e}")


    except SQLExecutionError as e:
        print(f"\nModule Initialization Error: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during testing: {e}")
    finally:
        # Close the pool when done testing
        if SQLExecutionModule._pool:
            SQLExecutionModule._pool.closeall()
            print("\nDatabase connection pool closed.")