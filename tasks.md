# Custom Model Configuration Implementation Tasks

## Task Overview

Implementation of custom model configuration functionality for ClaudeWarp, allowing users to set bigmodel and smallmodel values that map to ANTHROPIC_MODEL and ANTHROPIC_SMALL_FAST_MODEL in Claude Code settings.

## Phase 1: Data Model Enhancement

### Task 1.1: Update ProxyServer Model
**Component**: Core / Data Models  
**Estimated Time**: 2 hours  
**Priority**: High  

**Description**: Enhance the ProxyServer Pydantic model to support optional model configuration fields.

**Implementation Details**:
- Add `bigmodel: Optional[str]` field with 100 character limit
- Add `smallmodel: Optional[str]` field with 100 character limit  
- Add Pydantic validator for model name format validation
- Update field descriptions and examples in model Config

**Files to Modify**:
- `/claudewarp/core/models.py`

**Acceptance Criteria**:
- [ ] ProxyServer model accepts optional bigmodel and smallmodel fields
- [ ] Model validation rejects invalid characters and length
- [ ] Model validation accepts None/empty values
- [ ] Model validation accepts valid model names
- [ ] Backward compatibility maintained for existing model instances

**Testing Requirements**:
- Unit tests for model validation with valid names
- Unit tests for model validation with invalid names
- Unit tests for None/empty value handling
- Unit tests for backward compatibility

### Task 1.2: Update Configuration Serialization
**Component**: Core / Configuration  
**Estimated Time**: 1 hour  
**Priority**: High  

**Description**: Ensure TOML serialization/deserialization handles new optional model fields correctly.

**Implementation Details**:
- Verify TOML serialization includes model fields when present
- Verify TOML serialization omits model fields when None
- Test configuration loading with and without model fields
- Ensure backward compatibility for existing config files

**Files to Modify**:
- `/claudewarp/core/config.py` (if needed)

**Acceptance Criteria**:
- [ ] TOML serialization includes configured model values
- [ ] TOML serialization omits unconfigured model values
- [ ] Configuration loading works with model fields present
- [ ] Configuration loading works with model fields absent
- [ ] Existing configurations load without errors

**Testing Requirements**:
- Integration tests for TOML serialization
- Integration tests for configuration loading
- Backward compatibility tests

## Phase 2: Business Logic Updates

### Task 2.1: Enhance ProxyManager add_proxy Method
**Component**: Core / Manager  
**Estimated Time**: 1.5 hours  
**Priority**: High  

**Description**: Update the add_proxy method to accept and handle optional model configuration parameters.

**Implementation Details**:
- Add bigmodel and smallmodel parameters to method signature
- Pass model parameters to ProxyServer constructor
- Update method documentation
- Ensure existing tests continue to pass

**Files to Modify**:
- `/claudewarp/core/manager.py`

**Acceptance Criteria**:
- [ ] add_proxy method accepts bigmodel and smallmodel parameters
- [ ] Parameters are correctly passed to ProxyServer constructor
- [ ] Method works with None values for model parameters
- [ ] Method works with valid model names
- [ ] Existing functionality remains unchanged

**Testing Requirements**:
- Unit tests for add_proxy with model parameters
- Unit tests for add_proxy without model parameters
- Regression tests for existing functionality

### Task 2.2: Enhance ProxyManager update_proxy Method
**Component**: Core / Manager  
**Estimated Time**: 1.5 hours  
**Priority**: High  

**Description**: Update the update_proxy method to support updating model configuration.

**Implementation Details**:
- Add bigmodel and smallmodel parameters to method signature
- Update the update logic to handle model fields
- Preserve existing model values when parameters not provided
- Update method documentation

**Files to Modify**:
- `/claudewarp/core/manager.py`

**Acceptance Criteria**:
- [ ] update_proxy method accepts bigmodel and smallmodel parameters
- [ ] Method updates model values when provided
- [ ] Method preserves existing model values when not provided
- [ ] Method can clear model values with empty strings
- [ ] Existing functionality remains unchanged

**Testing Requirements**:
- Unit tests for updating model values
- Unit tests for preserving existing model values
- Unit tests for clearing model values
- Regression tests for existing functionality

### Task 2.3: Update Claude Code Configuration Merge Logic
**Component**: Core / Manager  
**Estimated Time**: 2 hours  
**Priority**: High  

**Description**: Enhance the _merge_claude_code_config method to conditionally include model environment variables.

**Implementation Details**:
- Modify _merge_claude_code_config to check for configured models
- Add ANTHROPIC_MODEL when bigmodel is configured
- Add ANTHROPIC_SMALL_FAST_MODEL when smallmodel is configured
- Omit model variables when not configured
- Update existing tests and add new test cases

**Files to Modify**:
- `/claudewarp/core/manager.py`

**Acceptance Criteria**:
- [ ] ANTHROPIC_MODEL included when bigmodel configured
- [ ] ANTHROPIC_SMALL_FAST_MODEL included when smallmodel configured
- [ ] Model variables omitted when not configured
- [ ] Existing Claude Code configuration preserved
- [ ] Generated JSON matches expected format

**Testing Requirements**:
- Unit tests for Claude Code generation with models
- Unit tests for Claude Code generation without models
- Integration tests for complete configuration flow
- JSON format validation tests

## Phase 3: CLI Implementation

### Task 3.1: Add Model Parameters to CLI add Command
**Component**: CLI / Commands  
**Estimated Time**: 1.5 hours  
**Priority**: Medium  

**Description**: Add bigmodel and smallmodel options to the CLI add command.

**Implementation Details**:
- Add --bigmodel and --smallmodel Typer options
- Update command help text and descriptions
- Pass model parameters to ProxyManager.add_proxy
- Update success message to include model information

**Files to Modify**:
- `/claudewarp/cli/commands.py`

**Acceptance Criteria**:
- [ ] CLI add command accepts --bigmodel option
- [ ] CLI add command accepts --smallmodel option
- [ ] Options are properly documented in help text
- [ ] Model parameters passed to add_proxy method
- [ ] Success message includes model configuration info

**Testing Requirements**:
- CLI tests for add command with model options
- CLI tests for add command without model options
- Help text validation tests

### Task 3.2: Add Model Parameters to CLI update Command
**Component**: CLI / Commands  
**Estimated Time**: 1.5 hours  
**Priority**: Medium  

**Description**: Add bigmodel and smallmodel options to the CLI update command.

**Implementation Details**:
- Add --bigmodel and --smallmodel Typer options to update command
- Update command help text and descriptions
- Pass model parameters to ProxyManager.update_proxy
- Update success message to show model configuration changes

**Files to Modify**:
- `/claudewarp/cli/commands.py`

**Acceptance Criteria**:
- [ ] CLI update command accepts --bigmodel option
- [ ] CLI update command accepts --smallmodel option
- [ ] Options support clearing values with empty strings
- [ ] Success message shows model configuration changes
- [ ] Help text clearly explains model options

**Testing Requirements**:
- CLI tests for update command with model options
- CLI tests for clearing model values
- Integration tests for complete update workflow

### Task 3.3: Enhance CLI Output Formatting
**Component**: CLI / Formatters  
**Estimated Time**: 1 hour  
**Priority**: Medium  

**Description**: Update CLI output formatters to display model configuration information.

**Implementation Details**:
- Update format_proxy_info to include model configuration
- Add model information to proxy list display
- Use appropriate icons/symbols for model display
- Handle cases where models are not configured

**Files to Modify**:
- `/claudewarp/cli/formatters.py`

**Acceptance Criteria**:
- [ ] Proxy information displays model configuration
- [ ] Model values shown when configured
- [ ] "Not configured" shown when models not set
- [ ] Consistent formatting with existing output
- [ ] Appropriate visual indicators used

**Testing Requirements**:
- Unit tests for formatter functions
- Visual output validation tests
- Edge case handling tests

## Phase 4: GUI Implementation

### Task 4.1: Update Add Proxy Dialog
**Component**: GUI / Dialogs  
**Estimated Time**: 3 hours  
**Priority**: Medium  

**Description**: Add model configuration fields to the Add Proxy dialog.

**Implementation Details**:
- Add model configuration section to dialog layout
- Create input fields for bigmodel and smallmodel
- Add placeholder text with example model names
- Add help text explaining model configuration
- Implement form validation for model fields

**Files to Modify**:
- `/claudewarp/gui/dialogs.py`

**Acceptance Criteria**:
- [ ] Dialog includes model configuration section
- [ ] Input fields have appropriate labels and placeholders
- [ ] Help text explains model purpose and optional nature
- [ ] Form validation provides clear error messages
- [ ] Model data included in dialog output

**Testing Requirements**:
- GUI tests for dialog layout and functionality
- Validation tests for model input fields
- User interaction tests

### Task 4.2: Update Edit Proxy Dialog
**Component**: GUI / Dialogs  
**Estimated Time**: 2 hours  
**Priority**: Medium  

**Description**: Add model configuration fields to the Edit Proxy dialog and populate with existing values.

**Implementation Details**:
- Extend edit dialog with same model fields as add dialog
- Populate model fields with existing proxy values
- Handle None values gracefully
- Update dialog's data collection methods

**Files to Modify**:
- `/claudewarp/gui/dialogs.py`

**Acceptance Criteria**:
- [ ] Edit dialog shows existing model values
- [ ] Empty fields displayed for unconfigured models
- [ ] Model fields can be updated independently
- [ ] Form validation works correctly
- [ ] Changes properly saved to proxy

**Testing Requirements**:
- GUI tests for edit dialog with model data
- Tests for editing existing model configuration
- Tests for adding model configuration to existing proxy

### Task 4.3: Update Main Window Information Display
**Component**: GUI / Main Window  
**Estimated Time**: 1.5 hours  
**Priority**: Medium  

**Description**: Enhance the main window to display current proxy model configuration.

**Implementation Details**:
- Update current proxy information panel
- Add model configuration section to display
- Show configured models or "Not configured" message
- Ensure layout scales properly with content

**Files to Modify**:
- `/claudewarp/gui/main_window.py`

**Acceptance Criteria**:
- [ ] Current proxy info shows model configuration
- [ ] Model section displays when models configured
- [ ] Appropriate message when models not configured
- [ ] Information updates when proxy switched
- [ ] Layout remains clean and readable

**Testing Requirements**:
- GUI tests for information display
- Tests for proxy switching with different model configs
- Layout and visual consistency tests

## Phase 5: Testing & Integration

### Task 5.1: Unit Test Implementation
**Component**: Tests  
**Estimated Time**: 4 hours  
**Priority**: High  

**Description**: Implement comprehensive unit tests for all model configuration functionality.

**Implementation Details**:
- Create test cases for ProxyServer model validation
- Create test cases for ProxyManager model methods
- Create test cases for Claude Code configuration generation
- Create test cases for CLI command parsing
- Ensure good test coverage for all new code

**Files to Modify**:
- `/tests/test_models.py`
- `/tests/test_manager.py`
- `/tests/test_cli.py`
- Create new test files as needed

**Acceptance Criteria**:
- [ ] All new model validation logic tested
- [ ] All ProxyManager method enhancements tested
- [ ] Claude Code generation thoroughly tested
- [ ] CLI parameter handling tested
- [ ] Test coverage ≥90% for new functionality

**Testing Requirements**:
- Unit tests pass consistently
- Test coverage reports generated
- Edge cases and error conditions tested

### Task 5.2: Integration Test Implementation
**Component**: Tests  
**Estimated Time**: 3 hours  
**Priority**: High  

**Description**: Implement integration tests for end-to-end model configuration workflows.

**Implementation Details**:
- Test complete add proxy with models workflow
- Test complete update proxy models workflow
- Test proxy switching with model configuration
- Test Claude Code file generation and validation
- Test configuration persistence across sessions

**Files to Modify**:
- `/tests/test_integration.py`
- Create additional integration test files as needed

**Acceptance Criteria**:
- [ ] End-to-end workflows tested
- [ ] Configuration persistence verified
- [ ] Claude Code integration tested
- [ ] Backward compatibility verified
- [ ] All test scenarios pass

**Testing Requirements**:
- Integration tests run in clean environments
- File system operations tested safely
- Configuration rollback tested

### Task 5.3: GUI Test Implementation
**Component**: Tests  
**Estimated Time**: 2 hours  
**Priority**: Medium  

**Description**: Implement GUI tests for model configuration interface elements.

**Implementation Details**:
- Test add proxy dialog with model fields
- Test edit proxy dialog with model fields
- Test main window model information display
- Test form validation and error handling
- Ensure GUI tests are stable and reliable

**Files to Modify**:
- Create GUI-specific test files
- Update existing GUI test infrastructure if needed

**Acceptance Criteria**:
- [ ] Dialog functionality tested
- [ ] Form validation tested
- [ ] Information display tested
- [ ] User interaction scenarios covered
- [ ] GUI tests pass consistently

**Testing Requirements**:
- GUI tests use pytest-qt framework
- Tests isolated and independent
- Visual elements properly validated

## Phase 6: Documentation & Finalization

### Task 6.1: Update Documentation
**Component**: Documentation  
**Estimated Time**: 2 hours  
**Priority**: Low  

**Description**: Update all relevant documentation to reflect model configuration functionality.

**Implementation Details**:
- Update README.md with model configuration examples
- Update CLI help text and examples
- Update code comments and docstrings
- Create user guide sections for model configuration

**Files to Modify**:
- `/README.md`
- `/BUILD.md` (if needed)
- Inline documentation in code files

**Acceptance Criteria**:
- [ ] Documentation accurately describes model configuration
- [ ] Examples provided for CLI and GUI usage
- [ ] Code documentation updated
- [ ] User guide includes model configuration section

### Task 6.2: Final Integration Testing
**Component**: Integration  
**Estimated Time**: 2 hours  
**Priority**: High  

**Description**: Perform final integration testing and validation before release.

**Implementation Details**:
- Run complete test suite
- Test with real Claude Code integration
- Validate backward compatibility
- Test on different platforms if possible
- Performance testing for new functionality

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] Real-world usage scenarios validated
- [ ] Performance remains acceptable
- [ ] No regressions identified
- [ ] Ready for release

## Task Dependencies

### Sequential Dependencies
1. Phase 1 must complete before Phase 2
2. Phase 2 must complete before Phases 3 & 4
3. Phases 3 & 4 can run in parallel
4. Phase 5 requires completion of relevant phases
5. Phase 6 runs after all implementation phases

### Critical Path
1. Task 1.1 → Task 1.2 → Task 2.1 → Task 2.2 → Task 2.3 → Task 5.1 → Task 5.2 → Task 6.2

### Parallel Work Opportunities
- CLI implementation (Phase 3) and GUI implementation (Phase 4) can be done simultaneously
- Testing (Phase 5) can begin as soon as relevant implementation phases complete
- Documentation (Task 6.1) can be written during implementation phases

## Risk Mitigation

### Technical Risks
- **Model validation complexity**: Mitigated by comprehensive unit tests
- **Claude Code integration**: Mitigated by thorough integration testing
- **Backward compatibility**: Mitigated by extensive regression testing

### Schedule Risks
- **GUI complexity**: Allocated extra time for GUI implementation
- **Testing thoroughness**: Prioritized testing tasks highly
- **Integration issues**: Built buffer time into final phase

## Success Metrics

### Functional Metrics
- All acceptance criteria met
- Test coverage ≥90% for new functionality
- Zero regression in existing functionality
- Successful Claude Code integration

### Quality Metrics
- All automated tests passing
- Code review approval
- Performance impact <5% for existing operations
- User acceptance testing successful

## Total Estimated Time

- **Phase 1**: 3 hours
- **Phase 2**: 5 hours  
- **Phase 3**: 4 hours
- **Phase 4**: 6.5 hours
- **Phase 5**: 9 hours
- **Phase 6**: 4 hours

**Total**: ~31.5 hours

## Resource Requirements

### Development Skills Needed
- Python/Pydantic expertise
- PySide6/Qt GUI development
- Typer CLI framework knowledge
- Testing framework experience (pytest, pytest-qt)

### Tools and Environment
- Python development environment with uv
- GUI testing capabilities
- Access to Claude Code for integration testing
- Cross-platform testing capability (preferred)