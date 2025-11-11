# Test Fixes Needed

## Current Status

**Tests Passing**: 725 / 801 (90.5%)
**Tests Failing**: 76 (9.5%)
**Test Collection**: ✅ All tests can be collected

## Fixed Issues

### 1. Import Errors ✅
Fixed incorrect imports of `APIError` from `models` instead of `exceptions`:
- `tests/core/test_http_client.py`
- `tests/core/test_models.py`
- `tests/providers/anidb/test_service.py`
- `tests/test_tools.py`

### 2. MyPy Duplicate Module Error ✅
Fixed CLI files that had mixed import styles:
- `src/mcp_server_anime/cli/analytics_cli.py`
- `src/mcp_server_anime/cli/database_cli.py`

Changed fallback imports from `from src.mcp_server_anime...` to `from mcp_server_anime...`

## Remaining Issues

### Test Failures (76 tests)

Most failures appear to be related to:

1. **Cache Isolation Issues**
   - Tests are not properly isolated from each other
   - Cached results from one test affecting another
   - Need to ensure cache is cleared between tests

2. **Mock/Fixture Issues**
   - Some mocks may not be properly set up
   - Fixtures may need better isolation

3. **Service Tests**
   - `tests/providers/anidb/test_service.py` - 15 failures
   - Related to caching and API error handling

4. **Tools Tests**
   - `tests/test_tools.py` - Multiple failures
   - Related to error handling and API responses

## Type Errors (163 errors)

MyPy found 163 type errors that need fixing:

### Common Issues:
1. **Missing Type Annotations**
   - Variables need explicit type hints
   - Function parameters missing types

2. **Incompatible Types**
   - Type mismatches in assignments
   - Return type mismatches

3. **Optional Types**
   - Missing `Optional[]` or `| None` annotations

## Recommended Fix Order

### Priority 1: Test Isolation
1. Fix cache isolation in test fixtures
2. Ensure proper cleanup between tests
3. Update `conftest.py` to handle cache clearing

### Priority 2: Failing Tests
1. Fix service tests (15 failures)
2. Fix tools tests (multiple failures)
3. Fix remaining test failures

### Priority 3: Type Errors
1. Add missing type annotations
2. Fix incompatible type assignments
3. Add Optional types where needed
4. Fix return type mismatches

## Commands for Testing

```bash
# Run all unit tests
poetry run pytest -m "not integration" -v

# Run specific test file
poetry run pytest tests/providers/anidb/test_service.py -v

# Run with coverage
poetry run pytest -m "not integration" --cov

# Check types
poetry run mypy src

# Run pre-commit checks
poetry run pre-commit run --all-files
```

## Notes

- Pre-commit hooks are configured but set to non-blocking for mypy and pytest
- This allows commits while we fix the issues
- Once all issues are fixed, we can make them blocking again

## Progress Tracking

- [x] Fix import errors
- [x] Fix mypy duplicate module error
- [ ] Fix test isolation issues
- [ ] Fix 76 failing tests
- [ ] Fix 163 type errors
- [ ] Make pre-commit hooks blocking

## Estimated Effort

- Test isolation fixes: 1-2 hours
- Failing tests: 2-3 hours
- Type errors: 3-4 hours
- **Total**: 6-9 hours

## Success Criteria

- ✅ All tests passing (801/801)
- ✅ Zero mypy errors
- ✅ 90%+ test coverage
- ✅ Pre-commit hooks passing (blocking mode)
- ✅ Clean codebase ready for production
