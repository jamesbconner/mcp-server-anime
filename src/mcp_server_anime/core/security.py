"""
Security infrastructure for MCP Server Anime.

This module provides security validation, logging, and query construction
utilities to prevent SQL injection and other security vulnerabilities.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    enable_table_validation: bool = True
    log_security_events: bool = True
    strict_validation_mode: bool = True
    allowed_providers: set[str] = field(default_factory=lambda: {"anidb"})


class SecurityLogger:
    """Enhanced logging for security events."""

    @staticmethod
    def log_table_validation_failure(table_name: str, provider: str) -> None:
        """Log table name validation failures."""
        logger.warning(
            "Table name validation failed",
            extra={
                "event_type": "table_validation_failure",
                "table_name": table_name,
                "provider": provider,
                "security_event": True,
            },
        )

    @staticmethod
    def log_exception_with_context(
        exception: Exception, context: dict[str, Any]
    ) -> None:
        """Log exceptions with security context."""
        logger.error(
            f"Exception occurred: {exception}",
            extra={
                "event_type": "exception_with_context",
                "exception_type": type(exception).__name__,
                "context": context,
                "security_event": True,
            },
            exc_info=True,
        )

    @staticmethod
    def log_security_event(event_type: str, details: dict[str, Any]) -> None:
        """Log general security events."""
        logger.info(
            f"Security event: {event_type}",
            extra={
                "event_type": event_type,
                "details": details,
                "security_event": True,
            },
        )


class TableNameValidator:
    """Validates table names against security policies."""

    # Allowed table name patterns by provider
    ALLOWED_TABLE_PATTERNS = {
        "anidb": ["{provider}_titles", "{provider}_metadata", "{provider}_cache"],
        "general": ["system_metadata", "provider_status"],
    }

    # Provider name must be alphanumeric with underscores, starting with letter
    PROVIDER_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")

    # Table name component pattern (alphanumeric with underscores)
    TABLE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")

    @classmethod
    def validate_table_name(cls, table_name: str, provider_name: str) -> str:
        """
        Validate and return safe table name.

        Args:
            table_name: The table name to validate
            provider_name: The provider name for context

        Returns:
            The validated table name

        Raises:
            ValueError: If table name is invalid or not allowed
        """
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")

        if not provider_name or not isinstance(provider_name, str):
            raise ValueError(f"Invalid provider name: {provider_name}")

        # Validate provider name format
        if not cls.PROVIDER_NAME_PATTERN.match(provider_name):
            SecurityLogger.log_table_validation_failure(table_name, provider_name)
            raise ValueError(f"Invalid provider name format: {provider_name}")

        # Check if table name matches allowed patterns
        allowed_patterns = cls.ALLOWED_TABLE_PATTERNS.get(provider_name, [])
        allowed_patterns.extend(cls.ALLOWED_TABLE_PATTERNS.get("general", []))

        # Generate expected table names from patterns
        expected_names = []
        for pattern in allowed_patterns:
            if "{provider}" in pattern:
                expected_names.append(pattern.format(provider=provider_name))
            else:
                expected_names.append(pattern)

        if table_name not in expected_names:
            SecurityLogger.log_table_validation_failure(table_name, provider_name)
            raise ValueError(
                f"Table name '{table_name}' not allowed for provider '{provider_name}'. "
                f"Allowed names: {expected_names}"
            )

        # Additional validation: check table name components
        if not cls.TABLE_COMPONENT_PATTERN.match(
            table_name.replace(f"{provider_name}_", "")
        ):
            SecurityLogger.log_table_validation_failure(table_name, provider_name)
            raise ValueError(f"Invalid table name format: {table_name}")

        SecurityLogger.log_security_event(
            "table_validation_success",
            {"table_name": table_name, "provider": provider_name},
        )

        return table_name

    @classmethod
    def get_allowed_table_patterns(cls) -> dict[str, list[str]]:
        """Return allowed table name patterns by provider."""
        return cls.ALLOWED_TABLE_PATTERNS.copy()

    @classmethod
    def is_valid_provider_name(cls, provider_name: str) -> bool:
        """Check if provider name is valid."""
        return bool(cls.PROVIDER_NAME_PATTERN.match(provider_name))


class SecureQueryHelper:
    """Helper for constructing secure SQL queries."""

    @staticmethod
    def build_select_query(
        table_name: str,
        columns: list[str],
        where_clause: str | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> tuple[str, list[Any]]:
        """
        Build parameterized SELECT query.

        Args:
            table_name: Validated table name (must be pre-validated)
            columns: List of column names to select
            where_clause: Optional WHERE clause with ? placeholders
            order_by: Optional ORDER BY clause
            limit: Optional LIMIT value

        Returns:
            Tuple of (query_string, parameters_list)
        """
        # Validate inputs
        if not table_name or not isinstance(table_name, str):
            raise ValueError("Invalid table name")

        if not columns or not isinstance(columns, list):
            raise ValueError("Invalid columns list")

        # Build column list (assuming column names are safe/predefined)
        columns_str = ", ".join(columns)

        # Build base query
        query_parts = [f"SELECT {columns_str} FROM {table_name}"]
        parameters = []

        # Add WHERE clause if provided
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        # Add ORDER BY if provided
        if order_by:
            query_parts.append(f"ORDER BY {order_by}")

        # Add LIMIT if provided
        if limit is not None:
            query_parts.append("LIMIT ?")
            parameters.append(limit)

        query = " ".join(query_parts)
        return query, parameters

    @staticmethod
    def build_metadata_query(metadata_table: str, key: str) -> tuple[str, tuple[str]]:
        """
        Build secure metadata lookup query.

        Args:
            metadata_table: Validated metadata table name
            key: The metadata key to look up

        Returns:
            Tuple of (query_string, parameters_tuple)
        """
        if not metadata_table or not isinstance(metadata_table, str):
            raise ValueError("Invalid metadata table name")

        if not key or not isinstance(key, str):
            raise ValueError("Invalid metadata key")

        query = f"SELECT value FROM {metadata_table} WHERE key = ?"
        return query, (key,)

    @staticmethod
    def build_count_query(
        table_name: str, where_clause: str | None = None
    ) -> tuple[str, list[Any]]:
        """
        Build secure COUNT query.

        Args:
            table_name: Validated table name
            where_clause: Optional WHERE clause with ? placeholders

        Returns:
            Tuple of (query_string, parameters_list)
        """
        if not table_name or not isinstance(table_name, str):
            raise ValueError("Invalid table name")

        query_parts = [f"SELECT COUNT(*) FROM {table_name}"]
        parameters = []

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        query = " ".join(query_parts)
        return query, parameters

    @staticmethod
    def build_delete_query(
        table_name: str, where_clause: str | None = None
    ) -> tuple[str, list[Any]]:
        """
        Build secure DELETE query.

        Args:
            table_name: Validated table name
            where_clause: Optional WHERE clause with ? placeholders

        Returns:
            Tuple of (query_string, parameters_list)
        """
        if not table_name or not isinstance(table_name, str):
            raise ValueError("Invalid table name")

        query_parts = [f"DELETE FROM {table_name}"]
        parameters = []

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        query = " ".join(query_parts)
        return query, parameters


class ValidationError(Exception):
    """Custom exception for validation failures."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


class SecurityValidationError(ValidationError):
    """Custom exception for security validation failures."""

    pass


def ensure_not_none(value: Any, name: str) -> Any:
    """
    Runtime validation to replace assert statements.

    Args:
        value: The value to check
        name: Name of the value for error messages

    Returns:
        The value if not None

    Raises:
        ValidationError: If value is None
    """
    if value is None:
        raise ValidationError(f"{name} cannot be None")
    return value


def ensure_condition(
    condition: bool, message: str, context: dict[str, Any] | None = None
) -> None:
    """
    Runtime validation to replace assert statements.

    Args:
        condition: The condition to check
        message: Error message if condition is False
        context: Optional context for debugging

    Raises:
        ValidationError: If condition is False
    """
    if not condition:
        raise ValidationError(message, context)
