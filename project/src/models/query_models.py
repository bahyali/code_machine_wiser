from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str

# Add other models as needed for schema, results, etc.
# Example:
# class TableSchema(BaseModel):
#     table_name: str
#     columns: list # List of column dicts

# class DBSchema(BaseModel):
#     tables: list[TableSchema]
#     relationships: list # List of relationship dicts