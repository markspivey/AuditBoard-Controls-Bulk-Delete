# Contributing to AuditBoard Bulk Deletion Toolkit

Thank you for your interest in contributing! This toolkit helps compliance teams safely manage AuditBoard data.

## How to Contribute

### Reporting Issues
- Check existing issues first to avoid duplicates
- Provide AuditBoard version and API endpoint details
- Include sanitized error messages (remove tokens/org names!)
- Describe expected vs actual behavior

### Suggesting Enhancements
- Open an issue with the "enhancement" label
- Describe the use case and business value
- Consider backward compatibility

### Code Contributions
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test in your AuditBoard sandbox environment
4. Ensure no sensitive data in commits
5. Follow existing code patterns (see scripts/core/ modules)
6. Update documentation if needed
7. Submit a pull request

## Development Guidelines

### Safety First
- All deletion operations must default to dry-run
- Production warnings are mandatory
- Never commit credentials or organization-specific data

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for all functions
- Keep functions focused and testable

### Testing
- Test all changes in sandbox first
- Verify with small datasets before large operations
- Test error handling paths

### Documentation
- Update README.md for new features
- Add usage examples
- Document any new configuration options

## Questions?
Open a discussion in the Discussions tab!
