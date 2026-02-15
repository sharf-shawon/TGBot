"""Query processor to orchestrate the complete NL → SQL → Results → NL flow."""

import logging
from typing import Any, Dict, List

from services.database import DatabaseService
from services.llm_service import LLMService
from services.sql_filter import SQLFilter

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Processor to handle the complete query flow."""

    def __init__(self, database: DatabaseService, api_key: str, model: str = None):
        """Initialize query processor.

        Args:
            database: Database service instance
            api_key: OpenRouter API key
            model: OpenRouter model to use (optional, uses LLMService default if not provided)
        """
        self.database = database
        self.llm = LLMService(api_key, model)
        self.sql_filter = SQLFilter()

        # Get database schema once
        self.schema = self._get_schema()

    def _get_schema(self) -> str:
        """Get database schema, handling connection issues.

        Returns:
            Database schema string
        """
        try:
            if not self.database.is_connected():
                self.database.connect()

            schema = self.database.fetch_full_schema()
            return schema
        except Exception as e:
            logger.error(f"Failed to fetch schema: {e}")
            return "Schema unavailable"

    def process_query(
        self,
        question: str,
        max_results: int = 100,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """Process a natural language query and return results.

        Args:
            question: Natural language question
            max_results: Maximum number of results to return
            max_retries: Maximum number of retries for SQL generation

        Returns:
            Dictionary containing:
                - success: bool
                - sql: str (generated SQL query)
                - results: list (query results)
                - row_count: int
                - explanation: str (natural language explanation)
                - error: str (if failed)
        """
        result = {
            "success": False,
            "sql": "",
            "results": [],
            "row_count": 0,
            "explanation": "",
            "error": ""
        }

        try:
            # Check if schema is available
            if not self.schema or self.schema == "Schema unavailable" or "No tables found" in self.schema:
                result["error"] = (
                    "Database schema is empty or unavailable. "
                    "Please ensure your database has tables and the bot has permission to access them. "
                    "Try using /refresh to reload the schema."
                )
                return result

            # Step 1: Validate if question is a query intent
            if not self.llm.validate_sql_intent(question):
                result["error"] = "This doesn't appear to be a database query question. Please ask about data in the database."
                return result

            # Step 2: Generate SQL from natural language
            logger.info(f"Processing question: {question}")
            sql = self.llm.generate_sql(question, self.schema)
            result["sql"] = sql

            # Step 3: Validate SQL query
            is_valid, error_msg = self.sql_filter.validate_query(sql)

            retry_count = 0
            while not is_valid and retry_count < max_retries:
                logger.warning(f"SQL validation failed (attempt {retry_count + 1}): {error_msg}")

                # Try to improve the SQL based on the error
                try:
                    sql = self.llm.improve_sql(sql, error_msg, self.schema)
                    result["sql"] = sql
                    is_valid, error_msg = self.sql_filter.validate_query(sql)
                    retry_count += 1
                except Exception as e:
                    logger.error(f"Failed to improve SQL: {e}")
                    break

            if not is_valid:
                result["error"] = f"Generated SQL query is not safe: {error_msg}"
                return result

            # Step 4: Add LIMIT if not present
            sql = self.sql_filter.add_limit_if_missing(sql, max_results)
            result["sql"] = sql

            # Step 5: Execute SQL query
            try:
                results, row_count = self.database.execute_query(sql)
                result["results"] = results
                result["row_count"] = row_count
            except Exception as e:
                error_str = str(e)
                logger.error(f"Query execution failed: {error_str}")

                # Try to improve SQL based on execution error
                if retry_count < max_retries:
                    try:
                        logger.info("Attempting to fix SQL based on execution error")
                        sql = self.llm.improve_sql(sql, error_str, self.schema)
                        result["sql"] = sql

                        # Validate again
                        is_valid, error_msg = self.sql_filter.validate_query(sql)
                        if not is_valid:
                            result["error"] = f"Could not generate safe SQL query: {error_msg}"
                            return result

                        # Execute again
                        sql = self.sql_filter.add_limit_if_missing(sql, max_results)
                        result["sql"] = sql
                        results, row_count = self.database.execute_query(sql)
                        result["results"] = results
                        result["row_count"] = row_count
                    except Exception as e2:
                        result["error"] = f"Query execution failed: {str(e2)}"
                        return result
                else:
                    result["error"] = f"Query execution failed: {error_str}"
                    return result

            # Step 6: Generate natural language explanation
            try:
                explanation = self.llm.explain_results(
                    question,
                    sql,
                    results,
                    row_count
                )
                result["explanation"] = explanation
            except Exception as e:
                logger.error(f"Failed to generate explanation: {e}")
                # Provide basic explanation
                if row_count == 0:
                    result["explanation"] = "No results found for your query."
                else:
                    result["explanation"] = f"Found {row_count} result(s)."

            result["success"] = True
            logger.info(f"Query processed successfully. Rows: {row_count}")

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            result["error"] = f"Failed to process query: {str(e)}"

        return result

    def format_results_for_telegram(
        self,
        results: List[Dict[str, Any]],
        max_rows_display: int = 20
    ) -> str:
        """Format query results for Telegram display.

        Args:
            results: Query results
            max_rows_display: Maximum number of rows to display

        Returns:
            Formatted string for Telegram
        """
        if not results:
            return "No results."

        # Limit displayed rows
        display_results = results[:max_rows_display]
        total_rows = len(results)

        lines = []

        # Create a simple table-like format
        for idx, row in enumerate(display_results, 1):
            lines.append(f"\n📊 Result {idx}:")
            for key, value in row.items():
                # Handle None values
                if value is None:
                    value = "NULL"
                # Truncate long strings
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."

                lines.append(f"  • {key}: {value_str}")

        # Add truncation notice if needed
        if total_rows > max_rows_display:
            lines.append(f"\n... and {total_rows - max_rows_display} more results")

        return "\n".join(lines)

    def refresh_schema(self):
        """Refresh the database schema cache."""
        try:
            self.database.clear_schema_cache()
            self.schema = self._get_schema()
            logger.info("Schema refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh schema: {e}")
            raise
