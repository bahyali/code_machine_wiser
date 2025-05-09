import pytest
from unittest.mock import MagicMock, patch

# Assuming the SQLExecutionModule is in src/services/sql_executor.py
# and uses psycopg2-binary.
# from src.services.sql_executor import SQLExecutionModule
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
    def __init__(self):
        self._results = None
        self._description = None
        self._rowcount = -1 # Default

    def execute(self, query, params=None):
        # Simulate execution and set results/description based on query
        if "SELECT 1" in query:
            self._results = [(1,)]
            self._description = [('?column?', None, None, None, None, None, None)]
            self._rowcount = 1
        elif "SELECT user_id, username FROM users" in query:
            self._results = [(1, 'alice'), (2, 'bob')]
            self._description = [('user_id', None, None, None, None, None, None), ('username', None, None, None, None, None, None)]
            self._rowcount = 2
        elif "SELECT SUM(price * quantity)" in query:
             self._results = [(1234.50,)]
             self._description = [('sum', None, None, None, None, None, None)]
             self._rowcount = 1
        elif "SELECT * FROM non_existent_table" in query:
            # Simulate a database error
            raise MockOperationalError("relation \"non_existent_table\" does not exist")
        else:
            self._results = []
            self._description = []
            self._rowcount = 0

    def fetchall(self):
        return self._results

    @property
    def description(self):
        return self._description

    @property
    def rowcount(self):
        return self._rowcount

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

class MockOperationalError(Exception):
    """Mock DB error."""
    pass

class MockPsycopg2:
    def connect(self, **kwargs):
        # Validate connection parameters if needed
        assert kwargs.get('host') == "localhost"
        assert kwargs.get('port') == 5432
        assert kwargs.get('database') == "testdb"
        assert kwargs.get('user') == "testuser"
        assert kwargs.get('password') == "testpass"
        return MockConnection()

    # Expose mock error types
    OperationalError = MockOperationalError
    # Add others like ProgrammingError, etc. if needed for testing

# Mock the actual SQLExecutionModule class if it doesn't exist
class MockSQLExecutionModule:
    def __init__(self, settings: MockSettings):
        self.settings = settings
        # In a real implementation, you might use a connection pool here
        self._conn_params = {
            "host": self.settings.db_host,
            "port": self.settings.db_port,
            "database": self.settings.db_name,
            "user": self.settings.db_user,
            "password": self.settings.db_password,
        }

    def execute_sql(self, sql_query: str, fetch_results: bool = True):
        """Mock method to execute SQL."""
        # Simulate connecting and executing using the mock psycopg2
        try:
            # In a real implementation: with psycopg2.connect(**self._conn_params) as conn:
            mock_psycopg2_lib = MockPsycopg2() # Use the mock library defined above
            with mock_psycopg2_lib.connect(**self._conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_query)
                    if fetch_results:
                        results = cur.fetchall()
                        # Simulate getting column names from cursor description
                        column_names = [desc[0] for desc in cur.description] if cur.description else []
                        return {"columns": column_names, "rows": results}
                    else:
                        return {"rowcount": cur.rowcount} # For INSERT/UPDATE/DELETE (if ever supported)
        except mock_psycopg2_lib.OperationalError as e:
            # Simulate catching DB errors
            raise e # Re-raise the mock error
        # Add other exception types as needed

# Mock the actual module path and its dependencies
# @pytest.fixture
# def sql_executor(mocker):
#     mock_settings = MockSettings() # Or mock the actual Settings
#     # Mock the actual SQLExecutionModule class
#     mock_executor_class = mocker.patch('src.services.sql_executor.SQLExecutionModule')
#     mock_instance = mock_executor_class.return_value
#     mock_instance.execute_sql = MagicMock()
#     # Configure return values in tests
#     return mock_instance

# A better approach is to mock the external dependency (psycopg2)
# and test the actual SQLExecutionModule logic.
# Assuming src.services.sql_executor.py exists and has the class.

# from src.services.sql_executor import SQLExecutionModule
# from src.core.config import Settings # Actual dependency
# import psycopg2 # Actual library

@pytest.fixture
def mock_psycopg2_lib(mocker):
    """Mocks the psycopg2 library for execution tests."""
    mock_lib = mocker.patch('psycopg2')
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_lib.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Configure default behavior for cursor methods
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = None
    mock_cursor.rowcount = -1

    # Expose mock error types
    mock_lib.OperationalError = MockOperationalError
    mock_lib.ProgrammingError = Exception # Use a generic exception for others

    return mock_lib

@pytest.fixture
def mock_settings_for_executor(mocker):
    """Mocks the configuration settings for DB connection."""
    mock_settings_obj = MockSettings()
    mocker.patch('src.core.config.get_settings', return_value=mock_settings_obj)
    mocker.patch('src.core.config.Settings', return_value=mock_settings_obj)
    return mock_settings_obj


@pytest.fixture
def sql_executor_instance(mock_settings_for_executor):
    """Provides an instance of SQLExecutionModule with mocked settings."""
    # In a real test, you'd import and instantiate the actual class:
    # return SQLExecutionModule(mock_settings_for_executor)
    # Using the mock class for demonstration:
    return MockSQLExecutionModule(mock_settings_for_executor)


def test_execute_sql_select_success(sql_executor_instance, mock_psycopg2_lib):
    """Test successful execution of a SELECT query."""
    sql_query = "SELECT user_id, username FROM users WHERE user_id = 1;"

    # Configure the mock cursor to return specific data for this query
    mock_psycopg2_lib.connect().cursor().fetchall.return_value = [(1, 'alice')]
    mock_psycopg2_lib.connect().cursor().description = [('user_id',), ('username',)]

    results = sql_executor_instance.execute_sql(sql_query)

    # Verify psycopg2.connect was called
    mock_psycopg2_lib.connect.assert_called_once_with(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass"
    )
    # Verify cursor.execute was called with the query
    mock_psycopg2_lib.connect().cursor().execute.assert_called_once_with(sql_query)
    # Verify fetchall was called for SELECT
    mock_psycopg2_lib.connect().cursor().fetchall.assert_called_once()
    # Verify connection and cursor were closed (via context manager)
    mock_psycopg2_lib.connect().close.assert_called_once()
    mock_psycopg2_lib.connect().cursor().close.assert_called_once()

    # Verify the returned results format
    assert isinstance(results, dict)
    assert "columns" in results
    assert "rows" in results
    assert results["columns"] == ['user_id', 'username']
    assert results["rows"] == [(1, 'alice')]


def test_execute_sql_select_no_results(sql_executor_instance, mock_psycopg2_lib):
    """Test SELECT query that returns no rows."""
    sql_query = "SELECT * FROM users WHERE user_id = 999;"

    # Configure the mock cursor for no results
    mock_psycopg2_lib.connect().cursor().fetchall.return_value = []
    mock_psycopg2_lib.connect().cursor().description = [('user_id',), ('username',)]

    results = sql_executor_instance.execute_sql(sql_query)

    mock_psycopg2_lib.connect().cursor().execute.assert_called_once_with(sql_query)
    mock_psycopg2_lib.connect().cursor().fetchall.assert_called_once()

    assert results["columns"] == ['user_id', 'username']
    assert results["rows"] == []


def test_execute_sql_db_error(sql_executor_instance, mock_psycopg2_lib):
    """Test execution that raises a database error."""
    sql_query = "SELECT * FROM non_existent_table;"

    # Configure the mock cursor to raise an exception on execute
    mock_psycopg2_lib.connect().cursor().execute.side_effect = mock_psycopg2_lib.OperationalError("relation \"non_existent_table\" does not exist")

    # Expect the exception to be raised by the executor
    with pytest.raises(mock_psycopg2_lib.OperationalError) as excinfo:
        sql_executor_instance.execute_sql(sql_query)

    # Verify execute was called
    mock_psycopg2_lib.connect().cursor().execute.assert_called_once_with(sql_query)
    # Verify fetchall was NOT called
    mock_psycopg2_lib.connect().cursor().fetchall.assert_not_called()
    # Verify the exception message
    assert "relation \"non_existent_table\" does not exist" in str(excinfo.value)

# Add tests for other potential errors (e.g., connection error)
# Add tests for execute_sql(fetch_results=False) if that functionality is implemented