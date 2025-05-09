import pytest
from unittest.mock import MagicMock, patch

# Assuming the DBSchemaManager is in src/services/schema_manager.py
# and uses psycopg2-binary.
# from src.services.schema_manager import DBSchemaManager
# from src.core.config import Settings # Dependency for DB connection details

# Mock the actual classes if they don't exist
class MockSettings:
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "testdb"
    db_user: str = "testuser"
    db_password: str = "testpass"

# Mock the psycopg2 library and its connection/cursor
class MockCursor:
    def execute(self, query, params=None):
        pass # Simulate execution

    def fetchall(self):
        # Simulate fetching schema data
        # Example schema data structure (simplified)
        # (table_name, column_name, data_type, is_nullable, column_default)
        return [
            ('users', 'user_id', 'integer', 'NO', 'nextval(\'users_user_id_seq\'::regclass)'),
            ('users', 'username', 'varchar', 'NO', None),
            ('users', 'created_at', 'timestamp with time zone', 'NO', 'now()'),
            ('products', 'product_id', 'integer', 'NO', 'nextval(\'products_product_id_seq\'::regclass)'),
            ('products', 'product_name', 'varchar', 'NO', None),
            ('products', 'price', 'numeric', 'NO', None),
            ('orders', 'order_id', 'integer', 'NO', 'nextval(\'orders_order_id_seq\'::regclass)'),
            ('orders', 'user_id', 'integer', 'NO', None),
            ('orders', 'order_date', 'timestamp with time zone', 'NO', 'now()'),
            ('order_items', 'item_id', 'integer', 'NO', 'nextval(\'order_items_item_id_seq\'::regclass)'),
            ('order_items', 'order_id', 'integer', 'NO', None),
            ('order_items', 'product_id', 'integer', 'NO', None),
            ('order_items', 'quantity', 'integer', 'NO', None),
            ('order_items', 'price_per_item', 'numeric', 'NO', None),
        ]

    def close(self):
        pass

class MockConnection:
    def cursor(self):
        return MockCursor()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class MockPsycopg2:
    def connect(self, **kwargs):
        # Validate connection parameters if needed
        assert kwargs.get('host') == "localhost"
        assert kwargs.get('port') == 5432
        assert kwargs.get('database') == "testdb"
        assert kwargs.get('user') == "testuser"
        assert kwargs.get('password') == "testpass"
        return MockConnection()

    # Add mock for OperationalError or other exceptions if testing error handling

# Mock the actual DBSchemaManager class if it doesn't exist
class MockDBSchemaManager:
    def __init__(self, settings: MockSettings):
        self.settings = settings
        self._schema_cache = None # Simulate caching

    def _get_db_connection_params(self):
        """Helper to get connection params from settings."""
        return {
            "host": self.settings.db_host,
            "port": self.settings.db_port,
            "database": self.settings.db_name,
            "user": self.settings.db_user,
            "password": self.settings.db_password,
        }

    def get_schema(self, force_refresh=False) -> str:
        """Mock method to get schema."""
        if self._schema_cache is None or force_refresh:
            # Simulate fetching from DB
            conn_params = self._get_db_connection_params()
            # In a real implementation, this would use psycopg2.connect
            # For the mock, we just simulate the result
            raw_schema_data = [
                ('users', 'user_id', 'integer', 'NO', 'nextval(\'users_user_id_seq\'::regclass)'),
                ('users', 'username', 'varchar', 'NO', None),
                ('users', 'created_at', 'timestamp with time zone', 'NO', 'now()'),
                ('products', 'product_id', 'integer', 'NO', 'nextval(\'products_product_id_seq\'::regclass)'),
                ('products', 'product_name', 'varchar', 'NO', None),
                ('products', 'price', 'numeric', 'NO', None),
                ('orders', 'order_id', 'integer', 'NO', 'nextval(\'orders_order_id_seq\'::regclass)'),
                ('orders', 'user_id', 'integer', 'NO', None),
                ('orders', 'order_date', 'timestamp with time zone', 'NO', 'now()'),
                ('order_items', 'item_id', 'integer', 'NO', 'nextval(\'order_items_item_id_seq\'::regclass)'),
                ('order_items', 'order_id', 'integer', 'NO', None),
                ('order_items', 'product_id', 'integer', 'NO', None),
                ('order_items', 'quantity', 'integer', 'NO', None),
                ('order_items', 'price_per_item', 'numeric', 'NO', None),
            ]
            self._schema_cache = self._format_schema_for_llm(raw_schema_data)
        return self._schema_cache

    def _format_schema_for_llm(self, raw_data) -> str:
        """Mock method to format schema data."""
        # Simulate formatting logic
        schema_string = "Database Schema:\n"
        tables = {}
        for row in raw_data:
            table_name, col_name, data_type, is_nullable, default = row
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append(f"  - {col_name} ({data_type}, Nullable: {is_nullable})")

        for table, columns in tables.items():
            schema_string += f"Table: {table}\n"
            schema_string += "\n".join(columns) + "\n"
        return schema_string.strip()

# Mock the actual module path and its dependencies
# @pytest.fixture
# def schema_manager(mocker):
#     mock_settings = MockSettings() # Or mock the actual Settings
#     # Mock the actual DBSchemaManager class
#     mock_manager_class = mocker.patch('src.services.schema_manager.DBSchemaManager')
#     # Configure the mock instance
#     mock_instance = mock_manager_class.return_value
#     mock_instance.get_schema = MagicMock()
#     mock_instance.get_schema.return_value = "Mocked Schema String"
#     return mock_instance

# A better approach is to mock the external dependency (psycopg2)
# and test the actual DBSchemaManager logic.
# Assuming src.services.schema_manager.py exists and has the class.

# from src.services.schema_manager import DBSchemaManager
# from src.core.config import Settings # Actual dependency

@pytest.fixture
def mock_psycopg2(mocker):
    """Mocks the psycopg2 library."""
    mock_lib = mocker.patch('psycopg2')
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_lib.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Configure the cursor to return mock schema data
    mock_cursor.fetchall.return_value = [
        ('users', 'user_id', 'integer', 'NO', 'nextval(\'users_user_id_seq\'::regclass)'),
        ('users', 'username', 'varchar', 'NO', None),
        ('products', 'product_id', 'integer', 'NO', 'nextval(\'products_product_id_seq\'::regclass)'),
        ('products', 'price', 'numeric', 'NO', None),
    ]

    # Add side_effect for execute if you need to check queries
    # mock_cursor.execute.side_effect = lambda q, p=None: print(f"Executed: {q}")

    return mock_lib

@pytest.fixture
def mock_settings_for_db(mocker):
    """Mocks the configuration settings for DB connection."""
    mock_settings_obj = MockSettings()
    mocker.patch('src.core.config.get_settings', return_value=mock_settings_obj)
    mocker.patch('src.core.config.Settings', return_value=mock_settings_obj)
    return mock_settings_obj

@pytest.fixture
def schema_manager_instance(mock_settings_for_db):
    """Provides an instance of DBSchemaManager with mocked settings."""
    # In a real test, you'd import and instantiate the actual class:
    # return DBSchemaManager(mock_settings_for_db)
    # Using the mock class for demonstration:
    return MockDBSchemaManager(mock_settings_for_db)


def test_get_schema_fetches_and_formats(schema_manager_instance, mock_psycopg2):
    """Test that get_schema fetches from DB and formats correctly."""
    # Ensure cache is initially empty for this test
    schema_manager_instance._schema_cache = None

    schema_string = schema_manager_instance.get_schema()

    # Verify psycopg2.connect was called with settings
    mock_psycopg2.connect.assert_called_once_with(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass"
    )
    # Verify cursor was created and fetchall was called
    mock_psycopg2.connect().cursor.assert_called_once()
    mock_psycopg2.connect().cursor().execute.assert_called_once() # Assuming execute is called to get schema
    mock_psycopg2.connect().cursor().fetchall.assert_called_once()

    # Verify the formatted schema string contains expected parts
    assert "Database Schema:" in schema_string
    assert "Table: users" in schema_string
    assert "  - user_id (integer, Nullable: NO)" in schema_string
    assert "  - username (varchar, Nullable: NO)" in schema_string
    assert "Table: products" in schema_string
    assert "  - product_id (integer, Nullable: NO)" in schema_string
    assert "  - price (numeric, Nullable: NO)" in schema_string
    assert "orders" not in schema_string # Based on mock fetchall data

    # Verify schema is cached
    assert schema_manager_instance._schema_cache is not None
    assert schema_manager_instance._schema_cache == schema_string


def test_get_schema_uses_cache(schema_manager_instance, mock_psycopg2):
    """Test that get_schema uses the cached value on subsequent calls."""
    # Populate the cache first
    initial_schema = schema_manager_instance.get_schema()
    mock_psycopg2.connect.reset_mock() # Reset mock call count

    # Call get_schema again without force_refresh
    cached_schema = schema_manager_instance.get_schema()

    # Verify that psycopg2.connect was NOT called again
    mock_psycopg2.connect.assert_not_called()
    assert cached_schema == initial_schema
    assert schema_manager_instance._schema_cache == cached_schema


def test_get_schema_force_refresh(schema_manager_instance, mock_psycopg2):
    """Test that get_schema refreshes cache when force_refresh is True."""
    # Populate the cache first
    initial_schema = schema_manager_instance.get_schema()
    mock_psycopg2.connect.reset_mock() # Reset mock call count

    # Call get_schema with force_refresh=True
    refreshed_schema = schema_manager_instance.get_schema(force_refresh=True)

    # Verify that psycopg2.connect WAS called again
    mock_psycopg2.connect.assert_called_once()
    assert refreshed_schema != initial_schema # Assuming mock fetchall returns different data or cache is cleared
    assert schema_manager_instance._schema_cache == refreshed_schema

# Add tests for database connection errors (e.g., mocking psycopg2.connect to raise an exception)
# Add tests for handling empty schema or specific schema structures