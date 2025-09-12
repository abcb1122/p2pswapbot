# Implement Comprehensive Logging System for Debugging

## Description
The P2P Bitcoin Swap Bot currently lacks proper logging infrastructure, making it difficult to debug user interactions, timeout events, and payment verification issues. This is critical since the bot handles real Bitcoin transactions on testnet and needs reliable monitoring.

## Problem Statement
- No visibility into user interaction flows
- Difficult to debug timeout scenarios
- Cannot track payment verification attempts
- No monitoring of background processes
- Hard to troubleshoot when deals fail

## Objectives
Implement a comprehensive logging system that captures critical events while filtering out noise.

## Technical Specifications

### Log Levels
- **ERROR**: Critical failures, exceptions
- **WARNING**: Timeout events, failed verifications
- **INFO**: User interactions, state changes
- **DEBUG**: Detailed flow information

### Events to Log

#### User Interactions
- Command executions (`/start`, `/swapout`, `/take`, etc.)
- Button clicks and responses
- User registrations and profile updates

#### Deal Management
- Deal creation and state transitions
- Timeout events with specific reasons
- Deal completions and cancellations
- Offer matching and acceptance

#### Payment Verification
- Bitcoin TXID verification attempts
- Lightning payment status checks
- Confirmation monitoring results
- Batch processing events

#### System Events
- Background monitor activity
- API calls to blockchain services
- Database operations (create, update, delete)
- Error conditions and recovery attempts

### Information to Filter (NOT log)
- Full message content (only log message type)
- API keys or sensitive credentials
- Repetitive health check pings
- Internal Telegram Bot API debug spam
- User personal information

## Implementation Structure

### File Organization
```
logs/
├── bot.log              # Main application log
├── user_interactions.log # User commands and responses
├── payments.log         # Bitcoin/Lightning verifications
├── timeouts.log         # Timeout and expiration events
└── errors.log           # Error-only log for critical issues
```

### Log Format
```
2025-01-15 14:30:25 | INFO | USER_INTERACTION | user_123456 | /swapout | amount=100000
2025-01-15 14:30:26 | INFO | DEAL_CREATED | deal_42 | seller=123456 | buyer=789012
2025-01-15 14:35:00 | WARNING | TIMEOUT_WARNING | deal_42 | stage=txid_required | expires_in=5min
```

### Configuration
- Log rotation: Daily rotation, keep 30 days
- Max file size: 10MB per log file
- Timezone: UTC for consistency
- Format: Timestamp | Level | Category | Entity | Action | Details

## Integration Points

### Files to Modify
- `src/bot.py`: Add logging to all command handlers
- `src/bitcoin_utils.py`: Log verification attempts
- `src/lightning_utils.py`: Log Lightning operations
- Background monitoring functions: Add timeout logging

### New Files to Create
- `src/logger_config.py`: Logging configuration
- `src/log_filters.py`: Custom filters for sensitive data
- `scripts/log_analyzer.py`: Log analysis utilities

## Use Cases

### Debugging Scenarios
1. **Timeout Investigation**: Track why deals expire at specific stages
2. **Payment Issues**: Monitor TXID verification failures
3. **User Flow Analysis**: Understand where users drop off
4. **Performance Monitoring**: Identify slow operations

### Monitoring Dashboards
- Active deals and their stages
- Recent timeout events
- Payment verification success rates
- Error frequency and types

## Acceptance Criteria

- [ ] Logging system captures all user commands and responses
- [ ] Deal state transitions are logged with timestamps
- [ ] Timeout events include specific expiration reasons
- [ ] Bitcoin TXID verifications are tracked with results
- [ ] Lightning payment attempts are logged
- [ ] Sensitive information is properly filtered
- [ ] Log files rotate automatically (daily/size-based)
- [ ] Log format is consistent and parseable
- [ ] Performance impact is minimal (<5% overhead)
- [ ] Log analysis script can generate basic reports

## Priority
**High** - Essential for debugging and production monitoring

## Estimated Effort
2-3 days for full implementation and testing

## Dependencies
- Python `logging` module (built-in)
- Log rotation utilities
- Integration with existing bot architecture

## Testing Requirements
- Verify logs are created for all critical events
- Test log rotation and file management
- Validate sensitive data filtering
- Performance testing with logging enabled
- Log analysis script functionality

## Labels
- `enhancement`
- `priority-high`
- `debugging`
- `infrastructure`

## Related Issues
- Will help resolve debugging difficulties mentioned in previous development sessions
- Foundation for monitoring system implementation

