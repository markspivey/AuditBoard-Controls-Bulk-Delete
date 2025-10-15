#!/usr/bin/env python3
"""
Delete Subprocesses
Bulk delete subprocesses by ID list.
"""
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_client import AuditBoardClient
from core.logger import get_logger
from core.config import Config, save_results
from core.safety import SafetyChecker


def delete_subprocesses_bulk(subprocess_ids: list, client: AuditBoardClient, logger, config, dry_run: bool):
    """Delete subprocesses in bulk."""
    safety = SafetyChecker(logger, dry_run)

    logger.section(f"SUBPROCESSES DELETION - {'DRY RUN' if dry_run else 'LIVE MODE'}")

    # Fetch subprocess details
    logger.info("Fetching subprocess details...")
    subprocesses = []
    for sp_id in subprocess_ids:
        sp = client.get_subprocess(sp_id)
        if sp:
            subprocesses.append(sp)
        else:
            logger.warning(f"Subprocess {sp_id} not found")

    if not subprocesses:
        logger.warning("No subprocesses found to delete")
        return {"timestamp": datetime.now().isoformat(), "dry_run": dry_run, "total": 0, "deleted": [], "failed": []}

    total = len(subprocesses)

    # Confirmation
    if not dry_run:
        if not safety.confirm_deletion("subprocesses", total):
            sys.exit(0)
        safety.countdown_warning(config.safety.countdown_seconds)

    logger.info(f"Starting deletion of {total} subprocesses...")
    logger.subsection("")

    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "total": total,
        "deleted": [],
        "failed": []
    }

    for i, sp in enumerate(subprocesses, 1):
        sp_id = sp.get('id')
        sp_uid = sp.get('uid')
        sp_name = sp.get('name', 'N/A')

        logger.info(f"[{i}/{total}] Subprocess {sp_id}: {sp_uid}")
        logger.info(f"          Name: {sp_name[:60]}")

        if dry_run:
            logger.info(f"[DRY-RUN] Would delete subprocess {sp_id}")
            results['deleted'].append({'id': sp_id, 'uid': sp_uid, 'name': sp_name})
        else:
            try:
                success = client.delete_subprocess(sp_id)
                if success:
                    logger.info(f"✅ Deleted subprocess {sp_id}")
                    results['deleted'].append({'id': sp_id, 'uid': sp_uid, 'name': sp_name})
                else:
                    logger.error(f"❌ Failed to delete subprocess {sp_id}")
                    results['failed'].append({'id': sp_id, 'uid': sp_uid, 'name': sp_name})
            except Exception as e:
                logger.error(f"❌ Exception: {e}")
                results['failed'].append({'id': sp_id, 'uid': sp_uid, 'name': sp_name, 'error': str(e)})

            if i % config.deletion.pause_every_n == 0 and i < total:
                time.sleep(config.safety.rate_limit_delay)

    logger.section("DELETION SUMMARY")
    logger.info(f"Total: {total} | Deleted: {len(results['deleted'])} | Failed: {len(results['failed'])}")
    return results


def main():
    parser = argparse.ArgumentParser(description='Delete subprocesses by ID list')
    parser.add_argument('--ids', type=int, nargs='+', required=True, help='Subprocess IDs to delete')
    parser.add_argument('--live', action='store_true', help='Execute live deletion')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--config', type=str, help='Config file path')
    args = parser.parse_args()

    dry_run = not args.live
    config = Config.load_from_file(args.config) if args.config else Config.load_from_env()
    logger = get_logger('delete_subprocesses')
    client = AuditBoardClient(config.auditboard.base_url, config.auditboard.api_token)

    results = delete_subprocesses_bulk(args.ids, client, logger, config, dry_run)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "dryrun" if dry_run else "live"
    output_file = args.output or f"{config.deletion.results_dir}/subprocesses_deletion_{mode}_{timestamp}.json"
    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
