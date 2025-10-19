# Security Guidelines

## Overview

This document outlines the security measures implemented in the MCP Server Anime project and provides guidelines for secure development practices.

## Security Fixes Implemented

### SQL Injection Prevention

**Status**: ✅ **RESOLVED**

All SQL injection vulnerabilities have been addressed through:

1. **Table Name Validation**: All dynamic table names are validated through `TableNameValidator` class
2. **Parameterized Queries**: All user input is handled through parameterized queries
3. **Secure Query Helpers**: `SecureQueryHelper` class provides safe query construction methods

**Files Fixed**:
- `src/mcp_server_anime/core/multi_provider_db.py` - 8 SQL injection issues resolved
- `src/mcp_server_anime/core/index_optimization.py` - 8 SQL injection issues resolved

### Hash Function Security

**Status**: ✅ **RESOLVED**

MD5 usage has been updated to specify non-cryptographic purpose:

- **File**: `src/mcp_server_anime/core/cache.py`
- **Fix**: Added `usedforsecurity=False` parameter to `hashlib.md5()`
- **Justification**: MD5 is only used for cache key generation, not cryptographic security

### Exception Handling

**Status**: ✅ **RESOLVED**

Bare `except: pass` statements have been replaced with proper logging:

- **Files**: `database_config.py`, `search_service.py`
- **Fix**: Added `SecurityLogger.log_exception_with_context()` calls
- **Benefit**: Better error visibility and debugging capabilities

### Assert Statement Replacement

**Status**: ✅ **RESOLVED**

Assert statements have been replaced with runtime validation:

- **File**: `src/mcp_server_anime/providers/anidb/service.py`
- **Fix**: Replaced `assert` with `ensure_not_none()` function
- **Benefit**: Validation works in optimized Python environments

## Security Architecture

### Core Security Components

1. **TableNameValidator**: Validates table names against whitelist patterns
2. **SecureQueryHelper**: Provides safe SQL query construction methods
3. **SecurityLogger**: Enhanced logging for security events
4. **ValidationError**: Custom exceptions for validation failures

### Security Validation Flow

```
User Input → TableNameValidator → SecureQueryHelper → Parameterized Query → Database
```

### Allowed Table Patterns

```python
ALLOWED_TABLE_PATTERNS = {
    "anidb": [
        "{provider}_titles",
        "{provider}_metadata", 
        "{provider}_cache"
    ],
    "general": [
        "system_metadata",
        "provider_status"
    ]
}
```

## Bandit Security Scan Results

### Current Status

- **High Severity**: 0 issues ✅
- **Medium Severity**: 8 issues (all false positives)
- **Low Severity**: 0 issues ✅

### False Positives Explanation

The remaining 8 Medium severity issues are false positives because:

1. **4 issues in `index_optimization.py`**: Table names are pre-validated by `TableNameValidator`
2. **4 issues in `security.py`**: Table names are pre-validated before being passed to helper functions

All table names go through security validation before any SQL construction occurs.

## Development Guidelines

### Secure Coding Practices

1. **Always validate table names** using `TableNameValidator.validate_table_name()`
2. **Use parameterized queries** for all user input
3. **Log security events** using `SecurityLogger` for monitoring
4. **Replace assert statements** with proper runtime validation
5. **Handle exceptions properly** with context logging

### Code Review Checklist

- [ ] All SQL queries use parameterized inputs
- [ ] Dynamic table names are validated
- [ ] No bare `except: pass` statements
- [ ] No assert statements in production code
- [ ] Security events are logged appropriately

### Testing Security

Run security scans regularly:

```bash
# Run bandit security scan
poetry run bandit -r src/

# Run with specific confidence level
poetry run bandit -r src/ --confidence-level medium

# Generate detailed report
poetry run bandit -r src/ -f json -o security-report.json
```

## Monitoring and Alerting

### Security Events

The following events are logged for security monitoring:

1. **Table validation failures**: Invalid table name attempts
2. **Exception contexts**: Detailed error information
3. **Validation errors**: Runtime validation failures

### Log Analysis

Security events can be identified by the `security_event: True` field in log entries.

Example log entry:
```json
{
  "event_type": "table_validation_failure",
  "table_name": "malicious_table",
  "provider": "unknown",
  "security_event": true
}
```

## Incident Response

### Security Issue Reporting

If you discover a security vulnerability:

1. **Do not** create a public issue
2. Contact the maintainers privately
3. Provide detailed reproduction steps
4. Allow time for assessment and patching

### Emergency Response

For critical security issues:

1. Immediately disable affected functionality
2. Apply temporary mitigations
3. Develop and test permanent fixes
4. Deploy fixes with security validation
5. Document lessons learned

## Compliance

This project follows security best practices including:

- **OWASP Top 10** guidelines for web application security
- **CWE (Common Weakness Enumeration)** mitigation strategies
- **Secure coding standards** for Python applications

## Updates

This security documentation is updated with each security-related change. Last updated: 2025-10-18

For questions about security practices, contact the development team.