# Test Weather Bad Server - Intentional Flaws Documentation

This document details all intentional flaws in the `test_weather_bad` server. These flaws are designed to test the Kahuna Testing Framework's ability to detect various security, quality, and performance issues.

## 1. Security Vulnerabilities

### 1.1 Input Validation Issues

- **No input sanitization**: Accepts any input without proper validation
- **No length validation enforcement**: Crashes on inputs > 100 characters (buffer overflow simulation)
- **Logs unsanitized input**: Debug logs contain raw user input (line 92)
- **Weak validation**: Only checks if input is non-empty

### 1.2 Information Disclosure

- **Exposes stack traces**: Returns full traceback in error responses (line 260-269)
- **Reveals internal structure**: Shows file paths in error messages (line 207-211)
- **Exposes debug information**: Sometimes includes internal state in responses (line 240-244)
- **Lists available tools incorrectly**: Error messages expose internal data structure (line 171)

### 1.3 Injection Vulnerabilities

- **SQL injection simulation**: Logs SQL-like commands as if executed (line 200-202)
- **Path traversal simulation**: Processes "../" in input (line 205-211)
- **No escaping of special characters**: Accepts and processes injection attempts

## 2. Quality Issues

### 2.1 Response Inconsistency

- **Inconsistent error formats**: Different error message structures throughout
- **Random response structures**:
  - 20% chance of missing fields (line 219-224)
  - 10% chance of wrong structure (line 225-230)
  - Sometimes includes debug info (line 240-244)
  - Inconsistently removes None values (line 247-248)
- **Missing timestamps**: 30% chance of forgetting timestamp (line 251-252)

### 2.2 Schema Issues

- **Incomplete tool schemas**: 10% chance of returning bad schema (line 106-122)
- **Missing required fields**: Sometimes omits "required" field in schema
- **Vague descriptions**: Tool descriptions are sometimes too brief

### 2.3 Data Validity

- **Invalid data ranges**: Humidity can be > 100% (line 215)
- **Null values in responses**: Conditions can be None (line 214)
- **Random data for unknown cities**: Returns random values instead of consistent defaults

### 2.4 State Management

- **Race conditions**: Global state without synchronization (REQUEST_COUNTER, line 148)
- **Memory leak**: MEMORY_LEAK_BUFFER grows without bounds (line 151-156)
- **No cleanup**: Never releases accumulated memory

## 3. Performance Issues

### 3.1 Response Time Problems

- **Random delays**: 100ms to 5 seconds (line 159)
- **Timeout simulation**: 5% chance of 30-second delay (line 160-161)
- **Performance degradation**: Gets slower as memory leak grows (line 164-165)

### 3.2 Resource Management

- **Memory leak**: Stores all request history (line 151-156)
- **No resource limits**: Unbounded memory growth
- **Debug logging overhead**: Logs at DEBUG level for all operations

## 4. Reliability Issues

### 4.1 Crash Conditions

- **Unhandled exceptions**: Crashes on inputs > 100 characters (line 88-90)
- **Type errors possible**: Sometimes skips validation (line 179-180)

### 4.2 Validation Bypass

- **10% chance to skip validation**: Random validation bypass (line 179-180)
- **Accepts empty strings after trimming**: No proper empty check after processing

## Test Detection Expectations

The Kahuna Testing Framework should detect:

1. **Security Score < 0.5**: Due to injection vulnerabilities and information disclosure
2. **Quality Score < 0.6**: Due to inconsistent responses and schema issues
3. **Performance Score < 0.7**: Due to random delays and degradation
4. **Reliability < 90%**: Due to random failures and crashes

## Usage for Testing

This server is used to validate that our testing framework can:

- Detect security vulnerabilities through black-box testing
- Identify response inconsistencies
- Measure performance degradation
- Catch reliability issues
- Validate proper error handling

## Comparison with Good Server

| Aspect            | Good Server      | Bad Server               |
| ----------------- | ---------------- | ------------------------ |
| Input Validation  | Comprehensive    | Minimal/None             |
| Error Handling    | Structured       | Exposes internals        |
| Response Format   | Consistent       | Random variations        |
| Performance       | Consistent 100ms | 100ms - 30s random       |
| Memory Management | Clean            | Memory leak              |
| Security          | Sanitized        | Multiple vulnerabilities |
