import logging
import psycopg2
from core.config import settings

logger = logging.getLogger(__name__)

class DBSchemaManager:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self._schema_cache = None # Simple in-memory cache

    async def get_schema(self, request_id: str = None):
        """
        Fetches database schema information. Uses a simple cache.
        """
        if self._schema_cache:
            logger.debug("Returning schema from cache", extra={'request_id': request_id})
            return self._schema_cache

        logger.info("Fetching database schema from PostgreSQL", extra={'request_id': request_id})
        schema_info = {}
        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()

            # Fetch tables and columns
            cursor.execute("""
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' -- Adjust schema name if necessary
                ORDER BY table_name, ordinal_position;
            """)
            columns_data = cursor.fetchall()

            tables = {}
            for table_name, column_name, data_type, is_nullable in columns_data:
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append({
                    "column_name": column_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable == 'YES'
                })

            schema_info['tables'] = [{"table_name": name, "columns": cols} for name, cols in tables.items()]

            # Fetch foreign key relationships (simplified)
            cursor.execute("""
                SELECT
                    tc.constraint_name, tc.table_name, kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'; -- Adjust schema name
            """)
            fk_data = cursor.fetchall()

            relationships = []
            for constraint_name, table_name, column_name, foreign_table_name, foreign_column_name in fk_data:
                relationships.append({
                    "constraint_name": constraint_name,
                    "from_table": table_name,
                    "from_column": column_name,
                    "to_table": foreign_table_name,
                    "to_column": foreign_column_name
                })
            schema_info['relationships'] = relationships

            logger.info("Successfully fetched database schema", extra={'request_id': request_id, 'table_count': len(tables), 'fk_count': len(relationships)})

            self._schema_cache = schema_info # Cache the result
            return schema_info

        except psycopg2.OperationalError as e:
            logger.error("Database connection or operational error while fetching schema", extra={'request_id': request_id, 'error': str(e)}, exc_info=True)
            raise # Re-raise for orchestrator to handle
        except Exception as e:
            logger.error("An unexpected error occurred while fetching schema", extra={'request_id': request_id, 'error': str(e)}, exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    # Method to format schema for LLM (example)
    def format_schema_for_llm(self, schema_info):
        """Formats schema information into a string suitable for LLM prompts."""
        if not schema_info:
            return "No schema information available."

        formatted_schema = "Database Schema:\n\n"

        if 'tables' in schema_info:
            formatted_schema += "Tables:\n"
            for table in schema_info['tables']:
                formatted_schema += f"- Table: {table['table_name']}\n"
                formatted_schema += "  Columns:\n"
                for col in table['columns']:
                    formatted_schema += f"  - {col['column_name']} ({col['data_type']}{', NULL' if col['is_nullable'] else ''})\n"
            formatted_schema += "\n"

        if 'relationships' in schema_info:
            formatted_schema += "Relationships (Foreign Keys):\n"
            for rel in schema_info['relationships']:
                formatted_schema += f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']} (Constraint: {rel['constraint_name']})\n"
            formatted_schema += "\n"

        return formatted_schema