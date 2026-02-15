"""SQL query filter to prevent dangerous operations."""

import logging
import re
from typing import List, Set, Tuple

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword

logger = logging.getLogger(__name__)


class SQLFilter:
    """Filter to validate SQL queries and prevent dangerous operations."""

    # Keywords that are forbidden for read-only access
    FORBIDDEN_KEYWORDS: Set[str] = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
        "EXECUTE",
        "CALL",
        "DO",
        # Functions that can modify data
        "COPY",
        "IMPORT",
        "LOAD",
        # Transaction control (not needed for read-only)
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        # Schema operations
        "RENAME",
        "COMMENT",
    }

    # Additional dangerous patterns to check
    DANGEROUS_PATTERNS: List[str] = [
        r";\s*(?:INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)",  # Multiple statements
        r"--\s*(?:INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)",  # Commented out
        r"/\*.*?(?:INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE).*?\*/",  # In comments
    ]

    @classmethod
    def validate_query(cls, sql: str) -> Tuple[bool, str]:
        """Validate SQL query for dangerous operations.

        Args:
            sql: SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty query"

        sql_upper = sql.upper()

        # Check for forbidden keywords
        for keyword in cls.FORBIDDEN_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r"\b" + keyword + r"\b"
            if re.search(pattern, sql_upper):
                logger.warning(f"Forbidden keyword detected: {keyword}")
                return False, f"Forbidden operation detected: {keyword}. Only SELECT queries are allowed."

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.DOTALL | re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return False, "Potentially dangerous SQL pattern detected. Only SELECT queries are allowed."

        # Parse SQL to check statement type
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return False, "Could not parse SQL query"

            for statement in parsed:
                if not cls._is_select_statement(statement):
                    stmt_type = statement.get_type()
                    logger.warning(f"Non-SELECT statement detected: {stmt_type}")
                    return False, f"Only SELECT queries are allowed. Detected: {stmt_type}"

        except Exception as e:
            logger.error(f"SQL parsing error: {e}")
            return False, f"Invalid SQL syntax: {e}"

        # Additional safety checks
        # Check for multiple statements (SQL injection prevention)
        if sql.count(";") > 1:
            return False, "Multiple SQL statements are not allowed"

        logger.info("SQL query validated successfully")
        return True, ""

    @staticmethod
    def _is_select_statement(statement: Statement) -> bool:
        """Check if a parsed SQL statement is a SELECT statement.

        Args:
            statement: Parsed SQL statement

        Returns:
            True if SELECT statement, False otherwise
        """
        stmt_type = statement.get_type()
        return stmt_type == "SELECT"

    @classmethod
    def sanitize_query(cls, sql: str) -> str:
        """Sanitize SQL query by removing comments and extra whitespace.

        Args:
            sql: SQL query to sanitize

        Returns:
            Sanitized SQL query
        """
        # Remove comments
        sql = sqlparse.format(sql, strip_comments=True)

        # Remove extra whitespace
        sql = sqlparse.format(sql, reindent=False, keyword_case="upper")

        # Remove trailing semicolons (keep only one if present)
        sql = sql.rstrip(";").strip()

        return sql

    @classmethod
    def extract_table_names(cls, sql: str) -> List[str]:
        """Extract table names from a SQL query.

        Args:
            sql: SQL query

        Returns:
            List of table names
        """
        tables = []

        try:
            parsed = sqlparse.parse(sql)
            for statement in parsed:
                for token in statement.tokens:
                    if isinstance(token, sqlparse.sql.Identifier):
                        tables.append(token.get_name())
                    elif token.ttype is Keyword and token.value.upper() == "FROM":
                        # Get the next token which should be the table name
                        idx = statement.token_index(token)
                        if idx < len(statement.tokens) - 1:
                            next_token = statement.tokens[idx + 1]
                            if isinstance(next_token, sqlparse.sql.Identifier):
                                tables.append(next_token.get_name())
        except Exception as e:
            logger.error(f"Error extracting table names: {e}")

        return tables

    @classmethod
    def add_limit_if_missing(cls, sql: str, max_limit: int = 100) -> str:
        """Add a LIMIT clause to the query if not present.

        Args:
            sql: SQL query
            max_limit: Maximum number of rows to return

        Returns:
            SQL query with LIMIT clause
        """
        sql_upper = sql.upper()

        # Check if LIMIT already exists
        if "LIMIT" in sql_upper:
            return sql

        # Add LIMIT clause
        sql = sql.rstrip(";").strip()
        sql = f"{sql} LIMIT {max_limit}"

        logger.info(f"Added LIMIT {max_limit} to query")
        return sql
