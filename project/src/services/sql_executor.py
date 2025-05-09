import logging
import psycopg2
from core.config import settings
import time

logger = logging.getLogger(__name__)

class SQLExecutionModule:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        # Consider adding a connection pool here for efficiency

    async def execute_sql(self, sql_query: str, request_id: str = None):
        """
        Executes an SQL query against the PostgreSQL database.
        Returns results for SELECT queries.
        """
        logger.debug("Executing SQL query", extra={'request_id': request_id, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})

        conn = None
        cursor = None
        start_time = time.time()

        try:
            # Connect to the database (using connection pool if implemented)
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()

            # Execute the query
            cursor.execute(sql_query)
            conn.commit() # Commit for DML, harmless for SELECT

            end_time = time.time()
            duration = end_time - start_time

            # Fetch results if it was a SELECT query
            if cursor.description:
                results = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                # Format results as list of dicts for easier processing
                formatted_results = [dict(zip(column_names, row)) for row in results]
                logger.info("SQL execution successful (SELECT)", extra={'request_id': request_id, 'duration_seconds': duration, 'rows_returned': len(formatted_results), 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})
                return formatted_results
            else:
                # Handle non-SELECT queries if necessary (though requirements focus on retrieval/insights)
                logger.info("SQL execution successful (Non-SELECT)", extra={'request_id': request_id, 'duration_seconds': duration, 'rows_affected': cursor.rowcount, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH]})
                return [] # No results for non-SELECT

        except psycopg2.Error as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error("SQL execution failed", extra={'request_id': request_id, 'duration_seconds': duration, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH], 'db_error': str(e)}, exc_info=True)
            conn.rollback() # Rollback on error
            raise # Re-raise the specific DB error for error correction module
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error("An unexpected error occurred during SQL execution", extra={'request_id': request_id, 'duration_seconds': duration, 'sql_query_truncated': sql_query[:settings.SQL_QUERY_LOG_MAX_LENGTH], 'error': str(e)}, exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()