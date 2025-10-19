"""Tests for logging configuration and structured logging."""

import json
import logging
import sys
from io import StringIO
from unittest.mock import patch

from src.mcp_server_anime.core.exceptions import MCPServerAnimeError
from src.mcp_server_anime.core.logging_config import (
    ContextualFormatter,
    MCPServerAnimeLogger,
    StructuredFormatter,
    clear_request_context,
    get_logger,
    log_api_request,
    log_cache_operation,
    log_error_with_context,
    log_performance,
    operation_var,
    request_id_var,
    set_request_context,
    setup_logging,
    setup_logging_for_environment,
    user_context_var,
)


class TestStructuredFormatter:
    """Test the structured JSON formatter."""

    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_formatting_with_context(self):
        """Test formatting with context variables."""
        formatter = StructuredFormatter()

        # Set context variables
        request_id_var.set("req-123")
        operation_var.set("test_operation")
        user_context_var.set({"user_id": "user-456"})

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/test/path.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            record.module = "test_module"
            record.funcName = "test_function"

            result = formatter.format(record)
            log_data = json.loads(result)

            assert log_data["request_id"] == "req-123"
            assert log_data["operation"] == "test_operation"
            assert log_data["user_context"] == {"user_id": "user-456"}
        finally:
            clear_request_context()

    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            record.module = "test_module"
            record.funcName = "test_function"

            result = formatter.format(record)
            log_data = json.loads(result)

            assert "exception" in log_data
            assert log_data["exception"]["type"] == "ValueError"
            assert log_data["exception"]["message"] == "Test exception"
            assert "traceback" in log_data["exception"]

    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.custom_field = "custom_value"
        record.another_field = 123

        result = formatter.format(record)
        log_data = json.loads(result)

        assert "extra" in log_data
        assert log_data["extra"]["custom_field"] == "custom_value"
        assert log_data["extra"]["another_field"] == 123

    def test_formatting_without_extra_fields(self):
        """Test formatting without extra fields."""
        formatter = StructuredFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.custom_field = "custom_value"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert "extra" not in log_data


class TestContextualFormatter:
    """Test the contextual human-readable formatter."""

    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = ContextualFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.0  # Fixed timestamp for testing

        result = formatter.format(record)

        assert "test.logger" in result
        assert "INFO" in result
        assert "Test message" in result

    def test_formatting_with_context(self):
        """Test formatting with context variables."""
        formatter = ContextualFormatter()

        # Set context variables
        request_id_var.set("req-123")
        operation_var.set("test_operation")

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/test/path.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            record.created = 1234567890.0

            result = formatter.format(record)

            assert "[req_id=req-123, op=test_operation]" in result
        finally:
            clear_request_context()

    def test_formatting_with_ctx_fields(self):
        """Test formatting with ctx_ prefixed fields."""
        formatter = ContextualFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.0
        record.ctx_user_id = "user-123"
        record.ctx_action = "search"

        result = formatter.format(record)

        assert "[user_id=user-123, action=search]" in result


class TestMCPServerAnimeLogger:
    """Test the enhanced logger class."""

    def setup_method(self):
        """Set up test logger."""
        self.logger = MCPServerAnimeLogger("test.logger")

        # Capture log output
        self.log_capture = StringIO()
        handler = logging.StreamHandler(self.log_capture)
        handler.setFormatter(StructuredFormatter())

        # Clear existing handlers and add our test handler
        self.logger.logger.handlers.clear()
        self.logger.logger.addHandler(handler)
        self.logger.logger.setLevel(logging.DEBUG)

    def test_debug_logging(self):
        """Test debug level logging."""
        self.logger.debug("Debug message", user_id="user-123")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "DEBUG"
        assert log_data["message"] == "Debug message"
        assert log_data["extra"]["ctx_user_id"] == "user-123"

    def test_info_logging(self):
        """Test info level logging."""
        self.logger.info("Info message", action="search")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Info message"
        assert log_data["extra"]["ctx_action"] == "search"

    def test_warning_logging(self):
        """Test warning level logging."""
        self.logger.warning("Warning message", retry_count=3)

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "WARNING"
        assert log_data["message"] == "Warning message"
        assert log_data["extra"]["ctx_retry_count"] == 3

    def test_error_logging(self):
        """Test error level logging."""
        self.logger.error("Error message", error_code="E001")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Error message"
        assert log_data["extra"]["ctx_error_code"] == "E001"

    def test_critical_logging(self):
        """Test critical level logging."""
        self.logger.critical("Critical message", system="database")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "CRITICAL"
        assert log_data["message"] == "Critical message"
        assert log_data["extra"]["ctx_system"] == "database"

    def test_exception_logging_with_mcp_error(self):
        """Test exception logging with MCPServerAnimeError."""
        error = MCPServerAnimeError(
            "Test error",
            code="TEST_ERROR",
            details="Error details",
            context={"key": "value"},
        )

        self.logger.exception("Exception occurred", exc=error, operation="test")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Exception occurred"
        assert log_data["extra"]["ctx_key"] == "value"
        assert log_data["extra"]["ctx_error_code"] == "TEST_ERROR"
        assert log_data["extra"]["ctx_error_details"] == "Error details"
        assert log_data["extra"]["ctx_operation"] == "test"

    def test_exception_logging_without_exc(self):
        """Test exception logging without explicit exception."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            self.logger.exception("Exception occurred", operation="test")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Exception occurred"
        assert log_data["extra"]["ctx_operation"] == "test"
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"


class TestContextManagement:
    """Test request context management."""

    def test_set_request_context(self):
        """Test setting request context."""
        set_request_context(
            request_id="req-123",
            operation="test_op",
            user_context={"user_id": "user-456"},
        )

        assert request_id_var.get() == "req-123"
        assert operation_var.get() == "test_op"
        assert user_context_var.get() == {"user_id": "user-456"}

        clear_request_context()

    def test_clear_request_context(self):
        """Test clearing request context."""
        set_request_context(
            request_id="req-123",
            operation="test_op",
            user_context={"user_id": "user-456"},
        )

        clear_request_context()

        assert request_id_var.get() is None
        assert operation_var.get() is None
        assert user_context_var.get() is None

    def test_partial_context_setting(self):
        """Test setting only some context variables."""
        set_request_context(request_id="req-123")

        assert request_id_var.get() == "req-123"
        assert operation_var.get() is None
        assert user_context_var.get() is None

        clear_request_context()


class TestLoggingHelpers:
    """Test logging helper functions."""

    def setup_method(self):
        """Set up test environment."""
        # Capture log output
        self.log_capture = StringIO()
        handler = logging.StreamHandler(self.log_capture)
        handler.setFormatter(StructuredFormatter())

        # Set up root logger for testing
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

    def test_log_performance(self):
        """Test performance logging."""
        log_performance("test_operation", 1.5, result_count=10)

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert "Performance: test_operation" in log_data["message"]
        assert log_data["extra"]["ctx_operation"] == "test_operation"
        assert log_data["extra"]["ctx_duration"] == 1.5
        assert log_data["extra"]["ctx_result_count"] == 10

    def test_log_api_request(self):
        """Test API request logging."""
        log_api_request(
            "GET",
            "https://api.example.com/test",
            status_code=200,
            duration=0.5,
            param1="value1",
        )

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert "API GET https://api.example.com/test" in log_data["message"]
        assert log_data["extra"]["ctx_method"] == "GET"
        assert log_data["extra"]["ctx_url"] == "https://api.example.com/test"
        assert log_data["extra"]["ctx_status_code"] == 200
        assert log_data["extra"]["ctx_duration"] == 0.5
        assert log_data["extra"]["ctx_param1"] == "value1"

    def test_log_cache_operation(self):
        """Test cache operation logging."""
        log_cache_operation("get", "cache:key:123", hit=True, ttl=3600)

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert "Cache get: cache:key:123" in log_data["message"]
        assert log_data["extra"]["ctx_operation"] == "get"
        assert log_data["extra"]["ctx_key"] == "cache:key:123"
        assert log_data["extra"]["ctx_hit"] is True
        assert log_data["extra"]["ctx_ttl"] == 3600

    def test_log_error_with_context(self):
        """Test error logging with context."""
        error = ValueError("Test error")
        log_error_with_context(error, operation="test_op", user_id="user-123")

        output = self.log_capture.getvalue()
        log_data = json.loads(output.strip())

        assert "Error in test_op: Test error" in log_data["message"]
        assert log_data["extra"]["ctx_user_id"] == "user-123"
        assert "exception" in log_data


class TestSetupLogging:
    """Test logging setup functions."""

    @patch("sys.stderr", new_callable=StringIO)
    def test_setup_logging_basic(self, mock_stderr):
        """Test basic logging setup."""
        setup_logging(log_level="DEBUG")

        # Test that logging works
        logger = logging.getLogger("test")
        logger.info("Test message")

        # Should have output to stderr
        assert len(mock_stderr.getvalue()) > 0

    @patch("sys.stderr", new_callable=StringIO)
    def test_setup_logging_structured(self, mock_stderr):
        """Test structured logging setup."""
        setup_logging(log_level="INFO", structured=True)

        # Test that logging works
        logger = logging.getLogger("test")
        logger.info("Test message")

        output = mock_stderr.getvalue()
        assert len(output) > 0

        # Should be valid JSON - get the last line which should be our test message
        lines = output.strip().split("\n")
        test_log_line = lines[-1]  # Get the last log line
        log_data = json.loads(test_log_line)
        assert log_data["message"] == "Test message"

    def test_setup_logging_for_environment(self):
        """Test environment-specific logging setup."""
        # Test development environment
        setup_logging_for_environment("development")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Test production environment
        setup_logging_for_environment("production")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

        # Test testing environment
        setup_logging_for_environment("testing")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

        # Test unknown environment (should default to development)
        setup_logging_for_environment("unknown")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


class TestGetLogger:
    """Test logger factory function."""

    def test_get_logger(self):
        """Test getting enhanced logger instance."""
        logger = get_logger("test.module")

        assert isinstance(logger, MCPServerAnimeLogger)
        assert logger.name == "test.module"
        assert logger.logger.name == "test.module"

    def test_get_logger_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1.logger is not logger2.logger
