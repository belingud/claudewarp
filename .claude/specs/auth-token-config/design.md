# Auth Token Configuration Design

## Overview

This document outlines the technical design for implementing auth token configuration support in ClaudeWarp. The feature will add support for `ANTHROPIC_AUTH_TOKEN` as an alternative to `ANTHROPIC_API_KEY`, with mutual exclusivity between the two authentication methods.

## Architecture

### System Architecture Overview

The auth token feature will be implemented as an extension to the existing proxy management system. The design maintains backward compatibility while adding the new authentication method.

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  ┌─────────────────┐          ┌─────────────────────────┐   │
│  │   CLI Interface │          │     GUI Interface       │   │
│  │  (Updated for   │          │   (Updated for auth     │   │
│  │   auth tokens)  │          │    token support)       │   │
│  └─────────────────┘          └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Layer                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               ProxyManager                              ││
│  │  ┌─────────────────┐  ┌─────────────────────────┐      ││
│  │  │  Existing API   │  │   Auth Token Logic     │      ││
│  │  │   Key Logic     │  │   (New Module)         │      ││
│  │  └─────────────────┘  └─────────────────────────┘      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                              │
│┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
││ ProxyServer     │  │  ProxyConfig   │  │   ExportFormat  ││
││  (Extended with │  │   (Updated)    │  │   (Updated)     ││
││   auth_token)   │  │                 │  │                 ││
│└─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Backward Compatibility**: Existing configurations must continue to work without modification
2. **Mutual Exclusivity**: API key and auth token cannot coexist in the same proxy
3. **Validation**: Strong validation for auth token format and mutual exclusivity
4. **User Experience**: Clear feedback and error messages for configuration operations
5. **Security**: Auth tokens receive the same security treatment as API keys

## Components and Interfaces

### 1. ProxyServer Model Extension

The `ProxyServer` model will be extended to include an `auth_token` field:

```python
class ProxyServer(BaseModel):
    # Existing fields...
    auth_token: Optional[str] = Field(
        default=None, 
        description="Auth token for authentication (mutually exclusive with api_key)"
    )
    
    # Validators for mutual exclusivity and format validation
    @validator('auth_token')
    def validate_auth_token(cls, v, values):
        # Validate auth token format and mutual exclusivity with api_key
        pass
    
    @validator('api_token')  # Updated to handle mutual exclusivity
    def validate_api_key(cls, v, values):
        # Updated to validate mutual exclusivity with auth_token
        pass
```

### 2. ProxyManager Extensions

The `ProxyManager` class will be extended with auth token support:

```python
class ProxyManager:
    def add_proxy(self, ..., auth_token: Optional[str] = None):
        """Extended to support auth_token parameter"""
        
    def update_proxy(self, ..., auth_token: Optional[str] = None):
        """Extended to support auth_token updates"""
        
    def _generate_export_content(self, proxy, export_format):
        """Updated to handle auth token export"""
        
    def _merge_claude_code_config(self, existing_config, proxy):
        """Updated to handle auth token in Claude Code integration"""
```

### 3. CLI Command Updates

CLI commands will be updated to support auth token operations:

```python
# Add proxy with auth token
@app.command()
def add(name: str, ..., auth_token: Optional[str] = None):
    """Add proxy with optional auth token"""
    
# Update proxy with auth token
@app.command()
def update(name: str, ..., auth_token: Optional[str] = None):
    """Update proxy with optional auth token"""
```

## Data Models

### ProxyServer Model Changes

```python
class ProxyServer(BaseModel):
    """Extended proxy server model with auth token support"""
    
    # Existing fields remain unchanged
    name: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(...)
    api_key: str = Field(..., min_length=3)  # Will be made optional in implementation
    description: str = Field(default="", max_length=200)
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = Field(default=True)
    bigmodel: Optional[str] = Field(default=None)
    smallmodel: Optional[str] = Field(default=None)
    
    # New field for auth token
    auth_token: Optional[str] = Field(
        default=None,
        description="Auth token for authentication (mutually exclusive with api_key)"
    )
    
    @validator('auth_token')
    def validate_auth_token(cls, v: Optional[str], values: dict) -> Optional[str]:
        """Validate auth token format and mutual exclusivity"""
        if v is None:
            return v
            
        # Check mutual exclusivity with api_key
        api_key = values.get('api_key')
        if api_key and api_key.strip():
            raise ValueError("Cannot configure both api_key and auth_token")
            
        # Validate auth token format (similar to api_key)
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Auth token length must be at least 10 characters")
        if re.search(r'\s', v):
            raise ValueError("Auth token cannot contain whitespace")
            
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v: str, values: dict) -> str:
        """Updated to validate mutual exclusivity with auth_token"""
        # Existing validation logic
        v = v.strip()
        if len(v) < 10:
            raise ValueError("API key length must be at least 10 characters")
        if re.search(r'\s', v):
            raise ValueError("API key cannot contain whitespace")
            
        # Check mutual exclusivity with auth_token
        auth_token = values.get('auth_token')
        if auth_token and auth_token.strip():
            raise ValueError("Cannot configure both api_key and auth_token")
            
        return v
    
    # Helper method to get active authentication method
    def get_auth_method(self) -> str:
        """Get the active authentication method"""
        if self.auth_token:
            return "auth_token"
        elif self.api_key:
            return "api_key"
        else:
            return "none"
    
    # Helper method to get active credential
    def get_active_credential(self) -> Optional[str]:
        """Get the active authentication credential"""
        if self.auth_token:
            return self.auth_token
        return self.api_key
```

### ExportFormat Updates

```python
class ExportFormat(BaseModel):
    """Updated export format to handle auth tokens"""
    
    # Existing fields remain unchanged
    shell_type: str = Field(default="bash")
    include_comments: bool = Field(default=True)
    prefix: str = Field(default="ANTHROPIC_")
    export_all: bool = Field(default=False)
    
    # No changes needed for auth token support
```

## Error Handling

### Custom Exceptions

```python
class AuthTokenError(ValidationError):
    """Raised when auth token validation fails"""
    pass

class MutualExclusivityError(ValidationError):
    """Raised when both api_key and auth_token are configured"""
    pass
```

### Error Scenarios and Messages

1. **Both API Key and Auth Token Configured**
   ```
   Error: Cannot configure both api_key and auth_token for proxy 'my-proxy'
   Solution: Remove the api_key to use auth_token, or remove the auth_token to use api_key
   ```

2. **Invalid Auth Token Format**
   ```
   Error: Auth token format validation failed: Auth token length must be at least 10 characters
   ```

3. **Auth Token with Whitespace**
   ```
   Error: Auth token format validation failed: Auth token cannot contain whitespace
   ```

4. **No Authentication Method Configured**
   ```
   Error: Proxy 'my-proxy' must have either api_key or auth_token configured
   ```

## Testing Strategy

### Unit Tests

1. **Auth Token Validation**
   - Test valid auth token formats
   - Test minimum length validation
   - Test whitespace validation
   - Test mutual exclusivity validation

2. **ProxyServer Model Tests**
   - Test auth_token field serialization/deserialization
   - Test get_auth_method() helper method
   - Test get_active_credential() helper method

3. **ProxyManager Tests**
   - Test add_proxy with auth_token
   - Test update_proxy with auth_token
   - Test mutual exclusivity enforcement
   - Test Claude Code integration with auth tokens

### Integration Tests

1. **CLI Integration**
   - Test CLI commands with auth token parameters
   - Test error messages for invalid configurations
   - Test configuration display with auth tokens

2. **Configuration File Tests**
   - Test loading configurations with auth tokens
   - Test backward compatibility with existing configurations
   - Test configuration migration scenarios

3. **Export Functionality Tests**
   - Test environment variable export with auth tokens
   - Test Claude Code configuration export
   - Test mutual exclusivity in exported configurations

### Edge Cases

1. **Configuration Migration**
   - Loading existing configurations without auth_token field
   - Upgrading from old format to new format
   - Handling corrupted configuration files

2. **Empty/Null Values**
   - Empty auth token strings
   - Null auth token values
   - Whitespace-only auth tokens

3. **Concurrent Operations**
   - Multiple operations on the same proxy
   - Configuration file locking scenarios
   - Race conditions in configuration updates

## Security Considerations

### Data Protection

1. **Token Storage**
   - Auth tokens stored in configuration files with same protection as API keys
   - No logging of auth token values
   - Secure file permissions on configuration files

2. **Memory Management**
   - Clear auth tokens from memory when no longer needed
   - Secure string handling for sensitive data
   - Minimal exposure of token values in error messages

3. **Access Control**
   - Configuration file permissions restricted to user
   - No world-readable configuration files
   - Secure temporary file handling

### Validation

1. **Input Validation**
   - Strict format validation for auth tokens
   - Prevention of injection attacks
   - Sanitization of user inputs

2. **Output Sanitization**
   - Masking of auth tokens in logs and display
   - Secure error message generation
   - Prevention of information leakage

## Performance Considerations

### Configuration Loading

1. **Backward Compatibility**
   - Minimal performance impact for existing configurations
   - Efficient handling of missing auth_token field
   - No additional parsing overhead for old format

2. **Validation Performance**
   - Efficient validation algorithms
   - Minimal computational overhead
   - Caching of validation results where appropriate

### Memory Usage

1. **Field Overhead**
   - Single additional field per proxy
   - Minimal memory footprint increase
   - Efficient string handling for tokens

## Migration Strategy

### Automatic Migration

1. **Existing Configurations**
   - No changes required for existing proxy configurations
   - auth_token field defaults to None for existing proxies
   - Existing functionality remains unchanged

2. **Configuration File Format**
   - Backward compatible JSON format
   - New auth_token field added when first used
   - Old configuration files remain valid

### User Experience

1. **Transparent Upgrade**
   - Users see no immediate changes to existing functionality
   - New auth token features available when explicitly used
   - No forced migration or configuration changes

2. **Feature Adoption**
   - Gradual adoption of auth token feature
   - Mixed usage of API keys and auth tokens supported
   - Clear documentation and examples provided

## Rollback Plan

### Version Compatibility

1. **Configuration Downgrade**
   - New configuration files with auth_token cannot be used with older versions
   - Clear error message for version incompatibility
   - Backup of original configuration before upgrade

2. **Feature Disabling**
   - Auth token validation can be disabled if needed
   - Fallback to API key only mode
   - Graceful degradation of functionality

## Success Criteria

### Functional Requirements

1. ✅ Auth tokens can be configured for proxy servers
2. ✅ Mutual exclusivity between API key and auth token is enforced
3. ✅ Claude Code integration works with auth tokens
4. ✅ Environment variable export supports auth tokens
5. ✅ Existing configurations remain compatible
6. ✅ CLI commands support auth token operations

### Quality Requirements

1. ✅ All validation rules are properly implemented
2. ✅ Error messages are clear and actionable
3. ✅ Performance impact is minimal
4. ✅ Security requirements are met
5. ✅ Test coverage is comprehensive
6. ✅ Documentation is updated and accurate