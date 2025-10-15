# Security Policy

## Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Instead, please use GitHub's private vulnerability reporting feature or contact the repository maintainer directly.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

## Security Best Practices

### API Token Management
- Never commit tokens to version control
- Use `.env` files (already in `.gitignore`)
- Rotate tokens regularly
- Use read-only tokens for discovery scripts when possible

### Data Safety
- Always test in sandbox environment first
- Use dry-run mode before live operations
- Maintain backups before bulk deletions
- Review dependency checks before proceeding

### Production Environments
- Enable all safety confirmations
- Use dedicated service accounts with minimal permissions
- Log all operations for audit trail
- Implement change management processes

## Known Limitations

This toolkit:
- ❌ Does NOT provide data recovery (deletions are permanent)
- ❌ Does NOT validate business logic (user responsibility)
- ❌ Is NOT affiliated with or supported by AuditBoard, Inc.

Always test thoroughly and maintain backups.
