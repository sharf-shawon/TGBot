"""PostgreSQL database service for schema fetching and query execution."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for interacting with PostgreSQL database."""

    def __init__(self, connection_url: str):
        """Initialize database service with connection URL.

        Args:
            connection_url: PostgreSQL connection URL
        """
        self.connection_url = connection_url
        self._connection = None
        self._schema_cache: Optional[str] = None

    def connect(self) -> bool:
        """Establish connection to the database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._connection = psycopg2.connect(self.connection_url)
            # Set autocommit mode for read-only queries
            self._connection.autocommit = True
            logger.info("Successfully connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Disconnected from database")

    def is_connected(self) -> bool:
        """Check if database connection is active.

        Returns:
            True if connected, False otherwise
        """
        if not self._connection or self._connection.closed:
            return False
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            return False

    def fetch_full_schema(self) -> str:
        """Fetch the complete database schema including tables, columns, and data types.

        Returns:
            Formatted schema string for LLM context
        """
        if self._schema_cache:
            return self._schema_cache

        if not self.is_connected():
            logger.warning("Not connected, attempting to reconnect...")
            if not self.connect():
                raise Exception("Not connected to database")

        schema_parts = []

        try:
            with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get all tables in the public schema
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                tables = cursor.fetchall()

                for table in tables:
                    table_name = table["table_name"]
                    schema_parts.append(f"\nTable: {table_name}")

                    # Get columns for each table
                    cursor.execute("""
                        SELECT
                            column_name,
                            data_type,
                            is_nullable,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = %s
                        ORDER BY ordinal_position;
                    """, (table_name,))
                    columns = cursor.fetchall()

                    schema_parts.append("  Columns:")
                    for col in columns:
                        nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                        default = f" DEFAULT {col['column_default']}" if col["column_default"] else ""
                        schema_parts.append(
                            f"    - {col['column_name']}: {col['data_type']} {nullable}{default}"
                        )

                    # Get primary keys
                    cursor.execute("""
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.table_schema = 'public'
                        AND tc.table_name = %s
                        AND tc.constraint_type = 'PRIMARY KEY'
                        ORDER BY kcu.ordinal_position;
                    """, (table_name,))
                    pks = cursor.fetchall()

                    if pks:
                        pk_cols = ", ".join(pk["column_name"] for pk in pks)
                        schema_parts.append(f"  Primary Key: {pk_cols}")

                    # Get foreign keys
                    cursor.execute("""
                        SELECT
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.table_schema = 'public'
                        AND tc.table_name = %s
                        AND tc.constraint_type = 'FOREIGN KEY';
                    """, (table_name,))
                    fks = cursor.fetchall()

                    if fks:
                        schema_parts.append("  Foreign Keys:")
                        for fk in fks:
                            schema_parts.append(
                                f"    - {fk['column_name']} → "
                                f"{fk['foreign_table_name']}.{fk['foreign_column_name']}"
                            )

            self._schema_cache = "\n".join(schema_parts)
            
            if not tables:
                logger.warning("No tables found in database schema!")
                self._schema_cache = "No tables found in the database."
            else:
                logger.info(f"Successfully fetched database schema: {len(tables)} tables, {len(self._schema_cache)} characters")
            
            return self._schema_cache

        except Exception as e:
            logger.error(f"Failed to fetch schema: {e}")
            raise

    def execute_query(self, sql: str) -> Tuple[List[Dict[str, Any]], int]:
        """Execute a SQL query and return results.

        Args:
            sql: SQL query to execute (should be SELECT only)

        Returns:
            Tuple of (list of result rows as dicts, row count)

        Raises:
            Exception: If query execution fails
        """
        if not self.is_connected():
            logger.warning("Not connected, attempting to reconnect...")
            if not self.connect():
                raise Exception("Not connected to database")

        try:
            with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)

                # Only fetch results for SELECT statements
                if cursor.description:
                    results = cursor.fetchall()
                    # Convert to list of dicts
                    results_list = [dict(row) for row in results]
                    return results_list, len(results_list)
                else:
                    return [], 0

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the database connection.

        Returns:
            Tuple of (success status, error message if any)
        """
        try:
            if not self.is_connected():
                if not self.connect():
                    return False, "Failed to establish connection"

            with self._connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                logger.info(f"PostgreSQL version: {version}")
                return True, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed: {error_msg}")
            return False, error_msg

    def clear_schema_cache(self):
        """Clear the cached schema (useful after schema changes)."""
        self._schema_cache = None
        logger.info("Schema cache cleared")
