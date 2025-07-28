# Custom Model Configuration Feature Requirements

## 1. Overview

This feature adds custom model configuration functionality to ClaudeWarp, allowing users to specify custom `bigmodel` and `smallmodel` values that map to `ANTHROPIC_MODEL` and `ANTHROPIC_SMALL_FAST_MODEL` respectively in Claude Code settings. The feature will be integrated into both GUI and CLI interfaces following existing architectural patterns.


的项目遇到了问题,首先是没有主题切换的按钮,其次是目前的黑色主题情况下,背景是白的.
我刚刚增加了配置在目录@claudewarp/gui/resources/qss/ 中,我要求能自动切换主题,并且能按主题切换按钮切换亮色暗色,系统颜色的检测使用darkdetect,文档: https://github.com/albertosottile/darkdetect,我已经安装了必要的依赖,另外可以参考 @claudewarp/gui/theme_manager.py

## 2. Functional Requirements

### 2.1 Core Functionality

#### FR-001: Model Configuration Storage
- The system SHALL store custom `bigmodel` and `smallmodel` values as optional fields in proxy server configurations
- Model values SHALL be validated as non-empty strings when provided
- Model values SHALL be optional (nullable) and not required for proxy server creation

#### FR-002: Claude Code Integration  
- When applying proxy settings to Claude Code, the system SHALL include `ANTHROPIC_MODEL` if `bigmodel` is configured
- When applying proxy settings to Claude Code, the system SHALL include `ANTHROPIC_SMALL_FAST_MODEL` if `smallmodel` is configured
- The system SHALL omit unset model values from the Claude Code JSON output
- The system SHALL preserve existing Claude Code configuration while merging model settings

#### FR-003: GUI Model Configuration
- The GUI SHALL provide input fields for `bigmodel` and `smallmodel` in the Add Proxy dialog
- The GUI SHALL provide input fields for `bigmodel` and `smallmodel` in the Edit Proxy dialog
- The GUI SHALL display current model values in the proxy information panel
- Model fields SHALL be optional and allow empty values

#### FR-004: CLI Model Configuration
- The CLI `add` command SHALL accept optional `--bigmodel` and `--smallmodel` parameters
- The CLI `update` command SHALL accept optional `--bigmodel` and `--smallmodel` parameters
- The CLI `list` and `info` commands SHALL display model configuration when present
- The CLI SHALL support clearing model values by passing empty strings

### 2.2 Data Management

#### FR-005: Data Persistence
- Model configuration SHALL be persisted in the TOML configuration file
- Model values SHALL be stored as optional string fields in proxy server objects
- The system SHALL maintain backward compatibility with existing configurations

#### FR-006: Data Validation
- Model names SHALL be validated as non-empty strings when provided
- Model names SHALL allow alphanumeric characters, hyphens, underscores, and periods
- Model names SHALL have a maximum length of 100 characters
- Invalid model names SHALL trigger appropriate validation errors

### 2.3 User Interface Requirements

#### FR-007: GUI Interface
- Model configuration fields SHALL be clearly labeled as "Big Model" and "Small Model"
- Fields SHALL include placeholder text indicating they are optional
- The proxy information panel SHALL display model values in a dedicated section
- Model values SHALL be displayed as "Not configured" when empty

#### FR-008: CLI Interface
- Help text SHALL clearly indicate model parameters are optional
- Output formatting SHALL include model information in proxy listings
- The CLI SHALL provide clear feedback when model values are updated

## 3. Non-Functional Requirements

### 3.1 Performance
- Adding model configuration SHALL NOT impact application startup time
- Model validation SHALL complete within 50ms for typical values
- Claude Code configuration generation SHALL remain under 100ms

### 3.2 Compatibility
- The feature SHALL maintain backward compatibility with existing proxy configurations
- Existing proxy servers without model configuration SHALL continue to function normally
- The feature SHALL work with all supported platforms (Windows, macOS, Linux)

### 3.3 Reliability
- Model configuration SHALL be validated before saving
- Invalid model values SHALL be rejected with clear error messages
- The system SHALL handle missing or corrupted model configuration gracefully

### 3.4 Usability
- Model configuration SHALL be intuitive for users familiar with Claude models
- Error messages SHALL be clear and actionable
- The feature SHALL follow existing UI/UX patterns in the application

## 4. Technical Requirements

### 4.1 Data Model
- Model fields SHALL be added to the `ProxyServer` Pydantic model
- Fields SHALL be optional with proper type hints
- Validation SHALL use Pydantic validators

### 4.2 API Consistency
- The feature SHALL follow existing ProxyManager patterns
- Method signatures SHALL maintain consistency with existing update methods
- Error handling SHALL use existing exception hierarchy

### 4.3 Testing
- Unit tests SHALL cover model validation logic
- Integration tests SHALL verify Claude Code configuration generation
- GUI tests SHALL verify model field functionality
- CLI tests SHALL verify parameter handling

## 5. Security Requirements

### 5.1 Input Validation
- All model input SHALL be validated before processing
- SQL injection and XSS protection SHALL be maintained
- Input length limits SHALL be enforced

### 5.2 Data Storage
- Model configuration SHALL use existing secure storage mechanisms
- No additional security vulnerabilities SHALL be introduced

## 6. Acceptance Criteria

### 6.1 Core Functionality
- [ ] Users can add proxies with custom model configuration
- [ ] Users can update model configuration for existing proxies  
- [ ] Model values are correctly mapped to Claude Code environment variables
- [ ] Unset model values are omitted from Claude Code configuration
- [ ] Existing proxy configurations continue to work without model settings

### 6.2 User Interface
- [ ] GUI provides intuitive model configuration fields
- [ ] CLI supports model parameters with proper help text
- [ ] Model values are displayed clearly in proxy information
- [ ] Error messages are clear and actionable

### 6.3 Data Management
- [ ] Model configuration is persisted correctly
- [ ] Validation prevents invalid model names
- [ ] Backward compatibility is maintained
- [ ] Configuration migration works properly

### 6.4 Integration
- [ ] Claude Code configuration includes correct environment variables
- [ ] Existing Claude Code settings are preserved
- [ ] Proxy switching updates model configuration correctly
- [ ] Export functionality includes model information

## 7. Success Metrics

- Zero regression in existing functionality
- Model configuration setup time under 30 seconds
- User error rate for model configuration under 5%
- 100% backward compatibility with existing configurations
- All automated tests passing

## 8. Dependencies

- Existing ProxyServer and ProxyConfig models
- ConfigManager and ProxyManager classes
- GUI dialog infrastructure (PySide6 + QFluentWidgets)
- CLI command infrastructure (Typer)
- Claude Code settings integration mechanism

## 9. Constraints

- Must maintain existing API compatibility
- Must not break existing proxy configurations
- Must follow established code patterns and conventions
- Must support all existing platforms
- Must complete within current development sprint