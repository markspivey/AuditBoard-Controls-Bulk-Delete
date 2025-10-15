# AuditBoard Bulk Deletion Toolkit

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

> Safe, reliable bulk deletion scripts for AuditBoard administrators

## ⚠️ WARNING

These scripts **PERMANENTLY DELETE** data from your AuditBoard instance. Always:
- ✅ Run in **dry-run mode** first (enabled by default)
- ✅ Test in your **sandbox environment** before production
- ✅ **Back up** critical data before deletion
- ✅ **Understand dependencies** (delete in correct order)
- ✅ **Verify** what will be deleted before executing

**There is NO undo button.** Deleted data cannot be recovered without AuditBoard support intervention.

---

## Features

- ✅ **Safe by default** - Dry-run mode prevents accidental deletion
- ✅ **Dependency checking** - Verifies safe deletion order
- ✅ **Comprehensive logging** - Full audit trail of all operations
- ✅ **Restoration verification** - Confirm successful restoration
- ✅ **Configurable** - YAML config files and environment variables
- ✅ **No hardcoded credentials** - All sensitive data in `.env`
- ✅ **Production warnings** - Extra confirmations for production environments

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
AUDITBOARD_BASE_URL=https://your-org.auditboardapp.com/api/v1
AUDITBOARD_API_TOKEN=your_token_here
DRY_RUN=true  # Keep as 'true' until ready for live deletion!
LOG_LEVEL=INFO
```

**IMPORTANT:** Start with your **sandbox** URL for testing!

### 3. Run Your First Analysis

Analyze a region to see what would be deleted:

```bash
python scripts/discovery/analyze_region.py --region-id 15
```

This will:
- Show all entities, processes, subprocesses, and controls
- Display the hierarchy and relationships
- Save results to `results/region_analysis_*.json`
- **NOT delete anything** (analysis only)

---

## Usage Examples

### Discovery Scripts

**Analyze a region:**
```bash
python scripts/discovery/analyze_region.py --region-id 15
```

**Search for entities:**
```bash
# Search controls by pattern
python scripts/discovery/search_entities.py --type controls --pattern "CC"

# Search processes (case-sensitive)
python scripts/discovery/search_entities.py --type processes --pattern "Compliance" --case-sensitive
```

**Check dependencies:**
```bash
# Check if entities can be safely deleted
python scripts/discovery/find_dependencies.py --type entities --ids 25 26 27 28

# Check process dependencies
python scripts/discovery/find_dependencies.py --type processes --ids 48 49 50

# Check region dependencies
python scripts/discovery/find_dependencies.py --type region --id 15
```

### Deletion Scripts

**All deletion scripts run in dry-run mode by default!**

**Delete controls:**
```bash
# Dry-run (shows what would be deleted)
python scripts/deletion/delete_controls.py --ids 100 101 102

# Delete by pattern (dry-run)
python scripts/deletion/delete_controls.py --pattern "CC"

# LIVE deletion (⚠️ PERMANENT!)
python scripts/deletion/delete_controls.py --pattern "CC" --live
```

**Delete subprocesses:**
```bash
# Dry-run
python scripts/deletion/delete_subprocesses.py --ids 86 87 88

# LIVE deletion
python scripts/deletion/delete_subprocesses.py --ids 86 87 88 --live
```

**Delete processes:**
```bash
python scripts/deletion/delete_processes.py --ids 48 49 50 --live
```

**Delete entities:**
```bash
python scripts/deletion/delete_entities.py --ids 25 26 27 28 --live
```

**Delete region:**
```bash
# With dependency check (safe)
python scripts/deletion/delete_region.py --region-id 15 --live

# Force delete without dependency check (⚠️ DANGEROUS!)
python scripts/deletion/delete_region.py --region-id 15 --live --force
```

### Verification Scripts

**Check if entities were restored:**
```bash
python scripts/verification/check_restoration.py --type entities --ids 25 26 27 28
```

**Verify perfect restoration:**
```bash
python scripts/verification/verify_restoration.py \
    --type controls \
    --original-file results/controls_deletion_live_20241011.json
```

---

## Deletion Order (Important!)

AuditBoard has a strict hierarchy. **You must delete in this order:**

```
1. Controls           (bottom of hierarchy)
2. Subprocesses
3. Processes
4. Entities
5. Region             (top of hierarchy)
```

**Deleting out of order will fail!** Use `find_dependencies.py` to check before deleting.

---

## Safety Features

### 1. Dry-Run Mode (Default)

All deletion scripts run in dry-run mode by default. They show what **would** be deleted without actually deleting anything.

To execute live deletion, add the `--live` flag.

### 2. Production Warnings

When operating on production (detected by URL not containing "sandbox"), you'll get extra confirmation prompts.

### 3. Dependency Checking

Before deleting regions or processes, the scripts check for dependencies and refuse to delete if any exist.

### 4. Comprehensive Logging

All operations are logged with timestamps to:
- Console output
- Log files in `results/`
- JSON result files for audit trail

### 5. Rate Limiting

Automatic pauses between deletions to avoid API throttling.

---

## Configuration

### Environment Variables (.env)

```bash
# Required
AUDITBOARD_BASE_URL=https://your-org.auditboardapp.com/api/v1
AUDITBOARD_API_TOKEN=your_token_here

# Optional
DRY_RUN=true           # Default: true (safe!)
LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=results        # Where to save logs
RESULTS_DIR=results    # Where to save result files
```

### YAML Configuration (config/config.yaml)

For advanced configuration, copy `config/config.example.yaml` to `config/config.yaml`:

```yaml
auditboard:
  timeout: 30
  max_retries: 3
  retry_delay: 2.0

safety:
  dry_run_default: true
  require_confirmation: true
  rate_limit_delay: 1.0
  countdown_seconds: 5

deletion:
  batch_size: 10
  pause_every_n: 5
```

---

## Common Workflows

### Workflow 1: Delete an Entire Region

```bash
# 1. Analyze the region
python scripts/discovery/analyze_region.py --region-id 15

# 2. Review the output - note the hierarchy

# 3. Delete in order (all in dry-run first)
python scripts/deletion/delete_controls.py --pattern "CC"
python scripts/deletion/delete_subprocesses.py --ids 86 87 88 89 90
python scripts/deletion/delete_processes.py --ids 48 49 50 51 52
python scripts/deletion/delete_entities.py --ids 25 26 27 28
python scripts/deletion/delete_region.py --region-id 15

# 4. If dry-run looks good, add --live to each command
python scripts/deletion/delete_controls.py --pattern "CC" --live
# ... etc
```

### Workflow 2: Delete Specific Controls

```bash
# 1. Search for controls
python scripts/discovery/search_entities.py --type controls --pattern "TEST"

# 2. Review the list, note the IDs

# 3. Delete (dry-run first)
python scripts/deletion/delete_controls.py --ids 100 101 102

# 4. If correct, delete for real
python scripts/deletion/delete_controls.py --ids 100 101 102 --live
```

### Workflow 3: Verify Restoration

```bash
# 1. Check if entities exist
python scripts/verification/check_restoration.py --type entities --ids 25 26 27 28

# 2. Deep comparison against original data
python scripts/verification/verify_restoration.py \
    --type entities \
    --original-file results/entities_deletion_live_20241011.json
```

---

## Project Structure

```
auditboard-bulk-delete/
├── scripts/
│   ├── core/                    # Core infrastructure
│   │   ├── api_client.py       # Centralized API client
│   │   ├── logger.py           # Logging utilities
│   │   ├── safety.py           # Safety checks
│   │   └── config.py           # Configuration management
│   ├── discovery/               # Discovery & analysis
│   │   ├── analyze_region.py   # Comprehensive region analysis
│   │   ├── search_entities.py  # Search by pattern
│   │   └── find_dependencies.py # Dependency checker
│   ├── deletion/                # Deletion scripts
│   │   ├── delete_controls.py
│   │   ├── delete_subprocesses.py
│   │   ├── delete_processes.py
│   │   ├── delete_entities.py
│   │   └── delete_region.py
│   └── verification/            # Restoration verification
│       ├── check_restoration.py
│       └── verify_restoration.py
├── config/
│   └── config.example.yaml     # Configuration template
├── results/                     # Output files (git-ignored)
├── .env.example                 # Environment template
├── .gitignore                   # Prevents committing secrets
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## Troubleshooting

### "Missing required environment variables"

Make sure you've created `.env` and filled in `AUDITBOARD_BASE_URL` and `AUDITBOARD_API_TOKEN`.

### "Failed to delete: dependencies exist"

You're trying to delete something that has dependent items. Delete the dependencies first:
- Before deleting subprocesses: delete controls
- Before deleting processes: delete subprocesses
- Before deleting entities: delete processes_data links
- Before deleting regions: delete entities and processes

Use `find_dependencies.py` to identify what needs deleting first.

### "403 Forbidden" or "401 Unauthorized"

Your API token is invalid or expired. Generate a new token in AuditBoard under Settings → API Tokens.

### "Rate limit exceeded"

The scripts have built-in rate limiting, but if you still hit limits, increase the `rate_limit_delay` in your config file.

---

## FAQ

**Q: Can I undo a deletion?**
A: No. Deletions are permanent. Contact AuditBoard support immediately if you need restoration.

**Q: What's the difference between /entities and /auditable_entities?**
A: They're different API endpoints. Most bulk operations use `/entities`. Always test in sandbox first.

**Q: How do I know if I'm in production or sandbox?**
A: Check your `AUDITBOARD_BASE_URL`. Sandbox URLs contain "sandbox": `https://org.auditboardsandbox.com`

**Q: Can I run multiple deletions in parallel?**
A: Not recommended. Run deletions sequentially to avoid race conditions and dependency errors.

**Q: Do I need to delete controls_data separately?**
A: No. When you delete controls via API, controls_data is automatically cleaned up.

---

## Getting API Token

1. Log into your AuditBoard instance
2. Go to **Settings** → **API Tokens**
3. Click **Generate New Token**
4. Copy the token immediately (it won't be shown again!)
5. Add it to your `.env` file

---

## Support

- **Issues:** [GitHub Issues](https://github.com/markspivey/AuditBoard-Controls-Bulk-Delete/issues)
- **Discussions:** [GitHub Discussions](https://github.com/markspivey/AuditBoard-Controls-Bulk-Delete/discussions)
- **AuditBoard Support:** For data restoration or API issues

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Acknowledgments

This toolkit was created to safely manage bulk deletions in AuditBoard. It emerged from real-world needs during a compliance region cleanup operation.

Special thanks to the AuditBoard community for feedback and testing.

---

## Disclaimer

This is an unofficial, community-created tool. It is not affiliated with, endorsed by, or supported by AuditBoard, Inc.

**Use at your own risk.** Always test in sandbox first. Always maintain backups. Always verify before executing live deletions.
