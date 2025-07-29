# Auth Token Configuration Requirements

## Introduction

This document outlines the requirements for adding auth token configuration support to ClaudeWarp. The feature will allow users to configure an `ANTHROPIC_AUTH_TOKEN` as an alternative to `ANTHROPIC_API_KEY` for Claude Code integration, with mutual exclusivity between the two authentication methods.

## Requirements

### 1. Auth Token Support

1.1 **As a ClaudeWarp user, I want to configure an auth token for proxy servers, so that I can use ANTHROPIC_AUTH_TOKEN instead of ANTHROPIC_API_KEY for Claude Code integration.**

   - The system must support storing auth tokens in proxy server configurations
   - Auth tokens must be validated similarly to API keys (minimum length, format validation)
   - Auth tokens must be securely stored in the configuration file
   - The system must support auth tokens for all existing proxy management operations

### 2. Mutual Exclusivity Validation

2.1 **As a ClaudeWarp user, I want the system to prevent having both API key and auth token configured simultaneously, so that I avoid authentication conflicts and ensure clear credential management.**

   - The system must validate that only one authentication method is configured per proxy
   - When adding an API key to a proxy with an existing auth token, the auth token must be automatically cleared
   - When adding an auth token to a proxy with an existing API key, the API key must be automatically cleared
   - The system must provide clear error messages when attempting to set both credentials simultaneously

### 3. Claude Code Integration

3.1 **As a ClaudeWarp user, I want the system to correctly export auth tokens to Claude Code configuration, so that Claude Code can use the auth token for authentication when API key is not available.**

   - When applying proxy settings to Claude Code, the system must use ANTHROPIC_AUTH_TOKEN if configured
   - When applying proxy settings to Claude Code, the system must use ANTHROPIC_API_KEY if configured
   - The system must not include both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN in the Claude Code configuration
   - The existing Claude Code configuration merging logic must be updated to handle auth tokens

### 4. Environment Variable Export

4.1 **As a ClaudeWarp user, I want to export auth tokens as environment variables, so that I can use them in shell environments and scripts.**

   - The system must support exporting ANTHROPIC_AUTH_TOKEN in addition to ANTHROPIC_API_KEY
   - Environment variable export must respect the mutual exclusivity principle
   - The export functionality must work across all supported shell types (bash, fish, powershell, zsh)
   - Export comments must indicate which authentication method is being used

### 5. Data Model Extensions

5.1 **As a ClaudeWarp user, I want the proxy server data model to support auth tokens, so that I can store and manage auth tokens alongside existing proxy configuration.**

   - The ProxyServer model must include an optional auth_token field
   - The auth_token field must have appropriate validation rules
   - The auth_token field must be included in JSON serialization/deserialization
   - The model must enforce mutual exclusivity between api_key and auth_token

### 6. Management Interface Updates

6.1 **As a ClaudeWarp user, I want to manage auth tokens through CLI commands, so that I can add, update, and remove auth tokens using the same interface as API keys.**

   - CLI commands must support auth token operations (add, update, remove)
   - The CLI must provide clear feedback when auth tokens are set or cleared
   - Help text must document the auth token functionality and mutual exclusivity
   - Command completion must work with auth token parameters

### 7. Validation and Error Handling

7.1 **As a ClaudeWarp user, I want clear validation and error messages for auth token operations, so that I can understand and resolve configuration issues quickly.**

   - Auth token format validation must provide specific error messages
   - Mutual exclusivity violations must provide clear guidance on how to resolve
   - The system must validate auth tokens during proxy creation and updates
   - Error messages must be consistent with existing error handling patterns

### 8. Backward Compatibility

8.1 **As a ClaudeWarp user, I want existing configurations to remain compatible, so that I can upgrade without losing my current proxy settings.**

   - Existing proxy configurations without auth tokens must continue to work
   - The system must handle missing auth_token field gracefully
   - Configuration file upgrades must not break existing functionality
   - Migration must be automatic and transparent to users

### 9. Configuration Display

9.1 **As a ClaudeWarp user, I want to see which authentication method is configured for each proxy, so that I can easily understand my current setup.**

   - Proxy listing must display the authentication method (API key or auth token)
   - Proxy status must indicate which credential is in use
   - Display must mask sensitive information while showing the credential type
   - The display must be consistent across CLI and GUI interfaces

### 10. Testing Requirements

10.1 **As a ClaudeWarp user, I want the auth token functionality to be thoroughly tested, so that I can rely on it for production use.**

    - Unit tests must cover auth token validation logic
    - Integration tests must verify Claude Code integration with auth tokens
    - Tests must verify mutual exclusivity enforcement
    - Tests must cover error scenarios and edge cases