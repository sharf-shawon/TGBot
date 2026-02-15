"""LLM service for natural language to SQL conversion using LangChain and OpenRouter."""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations using OpenRouter."""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Default model - can be changed by user
    DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

    def __init__(self, api_key: str, model: Optional[str] = None):
        """Initialize LLM service.

        Args:
            api_key: OpenRouter API key
            model: Model to use (default: claude-3.5-sonnet)
        """
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

        # Initialize LangChain ChatOpenAI with OpenRouter
        self.llm = ChatOpenAI(
            model=self.model,
            openai_api_key=api_key,
            openai_api_base=self.OPENROUTER_BASE_URL,
            temperature=0.0,  # Deterministic for SQL generation
        )

        logger.info(f"Initialized LLM service with model: {self.model}")

    def generate_sql(self, question: str, schema: str) -> str:
        """Generate SQL query from natural language question.

        Args:
            question: Natural language question
            schema: Database schema

        Returns:
            Generated SQL query

        Raises:
            Exception: If SQL generation fails
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert PostgreSQL SQL generator. Your job is to convert natural language questions into valid PostgreSQL SQL queries.

Database Schema:
{schema}

IMPORTANT RULES:
1. Generate ONLY valid PostgreSQL SELECT queries
2. Never use INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or any data modification commands
3. Use proper JOIN syntax when querying multiple tables
4. Always use table aliases for clarity
5. Return ONLY the SQL query without any explanation, markdown formatting, or code blocks
6. Do not include semicolons at the end
7. Use appropriate WHERE clauses to filter data
8. Use LIMIT clause if the question implies a limited result set
9. Handle NULL values appropriately
10. Use PostgreSQL-specific functions when needed (e.g., string_agg, array_agg, etc.)

For ambiguous questions, make reasonable assumptions based on the schema.
"""),
            ("user", "Question: {question}")
        ])

        try:
            chain = prompt_template | self.llm
            response = chain.invoke({
                "question": question,
                "schema": schema
            })

            sql = response.content.strip()

            # Clean up the SQL
            sql = self._clean_sql(sql)

            logger.info(f"Generated SQL: {sql}")
            return sql

        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            raise Exception(f"Failed to generate SQL query: {e}")

    def explain_results(self, question: str, sql: str, results: List[Dict[str, Any]], row_count: int) -> str:
        """Convert SQL query results back to natural language.

        Args:
            question: Original natural language question
            sql: SQL query that was executed
            results: Query results
            row_count: Number of rows returned

        Returns:
            Natural language explanation of results

        Raises:
            Exception: If explanation generation fails
        """
        # Limit results for explanation if too many
        results_for_llm = results[:10] if len(results) > 10 else results

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data analyst. Your job is to explain SQL query results in clear, natural language. Explanation should be 1-2 sentences max, and should focus on the key insights from the data.

IMPORTANT RULES:
1. Provide a clear, concise explanation of the results
2. Mention the total number of results if relevant
3. Highlight key insights or patterns in the data
4. Use proper formatting (bullet points, numbers) when appropriate
5. Be conversational and easy to understand
6. If there are many results, summarize the key findings
7. If there are no results, explain that clearly
8. Do not include the SQL query in your response unless specifically relevant
"""),
            ("user", """Original question: {question}

SQL query executed: {sql}

Number of results: {row_count}

Sample results (first 10 rows):
{results}

Please explain these results in natural language.""")
        ])

        try:
            chain = prompt_template | self.llm
            response = chain.invoke({
                "question": question,
                "sql": sql,
                "row_count": row_count,
                "results": str(results_for_llm)
            })

            explanation = response.content.strip()

            logger.info("Generated result explanation")
            return explanation

        except Exception as e:
            logger.error(f"Failed to explain results: {e}")
            # Return a basic explanation if LLM fails
            if row_count == 0:
                return "No results found for your query."
            else:
                return f"Found {row_count} result(s). The data has been retrieved successfully."

    def _clean_sql(self, sql: str) -> str:
        """Clean the generated SQL query.

        Args:
            sql: Raw SQL query

        Returns:
            Cleaned SQL query
        """
        # Remove markdown code blocks
        sql = sql.replace("```sql", "").replace("```", "")

        # Remove leading/trailing whitespace
        sql = sql.strip()

        # Remove trailing semicolons
        sql = sql.rstrip(";")

        # Remove extra whitespace
        sql = " ".join(sql.split())

        return sql

    def validate_sql_intent(self, question: str) -> bool:
        """Validate if the question is a valid SQL query intent.

        Args:
            question: Natural language question

        Returns:
            True if question seems to be a database query, False otherwise
        """
        # Common keywords that indicate a query
        query_keywords = [
            "show", "list", "get", "find", "how many", "count", "what",
            "who", "when", "where", "which", "select", "display", "retrieve",
            "fetch", "give me", "tell me", "search", "look for", "filter"
        ]

        question_lower = question.lower()

        # Check if question contains query keywords
        for keyword in query_keywords:
            if keyword in question_lower:
                return True

        # If question is long enough and contains "?" it's probably a query
        if len(question.split()) > 3 and "?" in question:
            return True

        return False

    def improve_sql(self, sql: str, error: str, schema: str) -> str:
        """Improve SQL query based on error feedback.

        Args:
            sql: Original SQL query that failed
            error: Error message
            schema: Database schema

        Returns:
            Improved SQL query

        Raises:
            Exception: If improvement fails
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert PostgreSQL SQL debugger. Fix the SQL query based on the error message.

Database Schema:
{schema}

IMPORTANT RULES:
1. Generate ONLY valid PostgreSQL SELECT queries
2. Never use INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or any data modification commands
3. Return ONLY the SQL query without any explanation or markdown formatting
4. Do not include semicolons at the end
"""),
            ("user", """This SQL query failed:
{sql}

Error message:
{error}

Please provide a corrected version of the SQL query.""")
        ])

        try:
            chain = prompt_template | self.llm
            response = chain.invoke({
                "sql": sql,
                "error": error,
                "schema": schema
            })

            improved_sql = response.content.strip()
            improved_sql = self._clean_sql(improved_sql)

            logger.info(f"Improved SQL: {improved_sql}")
            return improved_sql

        except Exception as e:
            logger.error(f"Failed to improve SQL: {e}")
            raise Exception(f"Failed to improve SQL query: {e}")
