"""
Tools for the agent to use.
"""
from langchain_core.tools import tool
from sqlalchemy import create_engine, text, Engine
import pandas as pd
from .. import env
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing import Annotated
from langchain_core.messages import ToolMessage
from ..databases.pg import PG
from ..databases.vector import Vector

class ServerSession:
    """A session for server-side state management and operations. 
    
    In practice, this would be a separate service from where the agent is running and the agent would communicate with it using a REST API. In this simplified example, we use it to persist the db engine and data returned from the query_db tool.
    """
    def __init__(self):
        self.engine: Engine = None
        self.df: pd.DataFrame = None

        self.engine = self._get_engine()

    def _get_engine(self):
        if self.engine is None:
            # Configure SQLAlchemy for session pooling
            _engine = create_engine(
                env.POSTGRES_URL,
                pool_size=5,                # Smaller pool size since the pooler manages connections
                max_overflow=5,             # Fewer overflow connections needed
                pool_timeout=10,            # Shorter timeout for getting connections
                pool_recycle=1800,          # Recycle connections more frequently
                pool_pre_ping=True,         # Keep this to verify connections
                pool_use_lifo=True,         # Keep LIFO to reduce number of open connections
                connect_args={
                    "application_name": "memento agent",
                    "options": "-c statement_timeout=30000",
                    # Keepalives less important with transaction pooler but still good practice
                    "keepalives": 1,
                    "keepalives_idle": 60,
                    "keepalives_interval": 30,
                    "keepalives_count": 3
                }
            )
            return _engine
        return self.engine


# Create a global instance of the ServerSession
session = ServerSession()

@tool
def table_searcher(query: str) -> list:
    """Search for relevant database tables based on a query.
    
    Args:
        query: The search query to find matching tables
        
    Returns:
        A list of table information including columns, descriptions, and metadata
    """
    vector_store = Vector()
    try:
        results = vector_store.get_similarity_search_results(query, top_k=5)
        output = []

        for doc in results:
            whole_table = doc.metadata.get("whole_table", {})
            if not whole_table:
                continue

            simplified = {
                "is_dimension": whole_table.get("is_dimension", False),
                "table_name": whole_table.get("table_name"),
                "table_desc": whole_table.get("table_desc"),
                "table_domain": whole_table.get("table_domain"),
                "table_display_name": whole_table.get("table_display_name"),
                "columns": [],
                "hierarchy": whole_table.get("hierarchy", []),
            }

            for col in whole_table.get("columns", []):
                simplified["columns"].append(
                    {
                        "col_name": col.get("col_name"),
                        "col_type": col.get("col_type"),
                        "column_display_name": col.get("column_display_name"),
                        "col_description": col.get("col_description"),
                        "business_attribute": col.get("business_attribute", []),
                    }
                )

            output.append(simplified)

        return output

    except Exception as e:
        return [{"error": str(e)}]

@tool
def sql_checker(query: str) -> bool:
    """
    Simple SQL query validator - checks syntax and executes.
    
    Args:
        query: SQL query to validate
        
    Returns:
        True if the query is valid, False otherwise
    """
    try:
        pg_instance = PG()
        
        # Basic syntax check
        if not query.strip():
            return "Error: Empty query"
        
        # Safety check - only allow SELECT
        if not query.strip().upper().startswith('SELECT'):
            return "Error: Only SELECT queries are allowed"
        
        # Test execution with LIMIT 1
        test_query = f"{query.rstrip(';')} LIMIT 1;"
        
        with pg_instance.connection.begin():
            result = pg_instance.connection.execute(statement=text(test_query))
            row = result.fetchone()
            
            return True
                
    except Exception as e:
        print(f"Query validation failed: {str(e)}")
        return False

@tool
def sql_runner(query: str) -> list:
    """
    Simple SQL query runner - executes the query and returns the result.
    
    Args:
        query: SQL query to execute
        
    Returns:
        query execution results
    """
    try:
        pg_instance = PG()
        
        # Basic syntax check
        if not query.strip():
            return "Error: Empty query"
        
        # Safety check - only allow SELECT
        if not query.strip().upper().startswith('SELECT'):
            return "Error: Only SELECT queries are allowed"
        
        # Test execution with LIMIT 1
        test_query = f"{query.rstrip(';')};"
        
        with pg_instance.connection.begin():
            result = pg_instance.connection.execute(text(test_query))
            columns = result.keys()  # get column names
            rows = result.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    except Exception as e:
        return [{"error": str(e)}]