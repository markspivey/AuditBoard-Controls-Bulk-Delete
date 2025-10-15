#!/usr/bin/env python3
"""
Delete Controls
Bulk delete controls by ID list or pattern filter.
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
from core.safety import SafetyChecker, is_dry_run


def get_controls_by_ids(control_ids: list, client: AuditBoardClient, logger):
    """Get controls by ID list."""
    logger.info(f"Fetching {len(control_ids)} controls by ID...")

    controls = []
    for ctrl_id in control_ids:
        ctrl = client.get_control(ctrl_id)
        if ctrl:
            controls.append(ctrl)
        else:
            logger.warning(f"Control {ctrl_id} not found")

    logger.info(f"Found {len(controls)} of {len(control_ids)} controls")
    return controls


def get_controls_by_pattern(pattern: str, client: AuditBoardClient, logger, case_sensitive: bool = False):
    """Get controls matching a pattern in UID or name."""
    logger.info(f"Fetching controls matching pattern: '{pattern}'")

    all_controls = client.get_controls()
    matching = []

    for ctrl in all_controls:
        ctrl_uid = ctrl.get('uid', '')
        ctrl_name = ctrl.get('name', '')

        if not case_sensitive:
            ctrl_uid = ctrl_uid.lower()
            ctrl_name = ctrl_name.lower()
            search_pattern = pattern.lower()
        else:
            search_pattern = pattern

        if search_pattern in ctrl_uid or search_pattern in ctrl_name:
            matching.append(ctrl)

    logger.info(f"Found {len(matching)} controls matching pattern")
    return matching


def delete_controls_bulk(controls: list, client: AuditBoardClient, logger, config, dry_run: bool):
    """
    Delete controls in bulk.

    Args:
        controls: List of control dicts to delete
        client: AuditBoard API client
        logger: Logger instance
        config: Configuration object
        dry_run: Whether in dry-run mode

    Returns:
        Results dict
    """
    safety = SafetyChecker(logger, dry_run)

    logger.section(f"CONTROLS DELETION - {'DRY RUN' if dry_run else 'LIVE MODE'}")

    if not controls:
        logger.warning("No controls to delete")
        return {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "total_controls": 0,
            "deleted": [],
            "failed": []
        }

    total = len(controls)

    # Confirmation and countdown
    if not dry_run:
        if not safety.confirm_deletion("controls", total, confirmation_text=f"DELETE {total} CONTROLS"):
            logger.info("Deletion cancelled")
            sys.exit(0)
        safety.countdown_warning(config.safety.countdown_seconds)

    logger.info(f"Starting deletion of {total} controls...")
    logger.subsection("")

    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "total_controls": total,
        "deleted": [],
        "failed": []
    }

    # Delete each control
    for i, ctrl in enumerate(controls, 1):
        ctrl_id = ctrl.get('id')
        ctrl_uid = ctrl.get('uid')
        ctrl_name = ctrl.get('name', 'N/A')

        logger.info(f"[{i}/{total}] Control {ctrl_id}: {ctrl_uid}")
        logger.info(f"          Name: {ctrl_name[:60]}")

        if dry_run:
            logger.info(f"[DRY-RUN] Would delete control {ctrl_id}")
            results['deleted'].append({
                'id': ctrl_id,
                'uid': ctrl_uid,
                'name': ctrl_name
            })
        else:
            try:
                success = client.delete_control(ctrl_id)
                if success:
                    logger.info(f"✅ Deleted control {ctrl_id}")
                    results['deleted'].append({
                        'id': ctrl_id,
                        'uid': ctrl_uid,
                        'name': ctrl_name
                    })
                else:
                    logger.error(f"❌ Failed to delete control {ctrl_id}")
                    results['failed'].append({
                        'id': ctrl_id,
                        'uid': ctrl_uid,
                        'name': ctrl_name
                    })
            except Exception as e:
                logger.error(f"❌ Exception deleting control {ctrl_id}: {e}")
                results['failed'].append({
                    'id': ctrl_id,
                    'uid': ctrl_uid,
                    'name': ctrl_name,
                    'error': str(e)
                })

        # Rate limiting
        if not dry_run and i % config.deletion.pause_every_n == 0 and i < total:
            logger.info(f"  ... pausing for rate limiting ...")
            time.sleep(config.safety.rate_limit_delay)

    # Summary
    logger.section("DELETION SUMMARY")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE DELETION'}")
    logger.info(f"Total controls: {total}")
    logger.info(f"Successfully deleted: {len(results['deleted'])}")
    logger.info(f"Failed: {len(results['failed'])}")

    if results['failed']:
        logger.error("\nFailed deletions:")
        for item in results['failed'][:10]:
            logger.error(f"  - Control {item['id']}: {item['uid']}")
        if len(results['failed']) > 10:
            logger.error(f"  ... and {len(results['failed']) - 10} more")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Delete controls in bulk by ID list or pattern',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete controls by ID list (dry-run)
  python delete_controls.py --ids 100 101 102

  # Delete controls by pattern (dry-run)
  python delete_controls.py --pattern "CC"

  # Delete controls by pattern (LIVE)
  python delete_controls.py --pattern "CC" --live

  # Delete from JSON file
  python delete_controls.py --ids-file control_ids.json --live
        """
    )

    parser.add_argument('--ids', type=int, nargs='+',
                        help='List of control IDs to delete')
    parser.add_argument('--ids-file', type=str,
                        help='JSON file containing list of control IDs')
    parser.add_argument('--pattern', type=str,
                        help='Pattern to match in UID or name')
    parser.add_argument('--case-sensitive', action='store_true',
                        help='Enable case-sensitive pattern matching')
    parser.add_argument('--live', action='store_true',
                        help='Execute live deletion (default is dry-run)')
    parser.add_argument('--output', type=str,
                        help='Output file path')
    parser.add_argument('--config', type=str,
                        help='Path to config file (optional)')

    args = parser.parse_args()

    # Validate arguments
    if not args.ids and not args.ids_file and not args.pattern:
        parser.error("Must specify --ids, --ids-file, or --pattern")

    # Determine dry-run mode
    dry_run = not args.live

    # Load configuration
    if args.config:
        config = Config.load_from_file(args.config)
    else:
        config = Config.load_from_env()

    # Initialize logger
    logger = get_logger('delete_controls')

    # Initialize API client
    client = AuditBoardClient(
        base_url=config.auditboard.base_url,
        api_token=config.auditboard.api_token,
        timeout=config.auditboard.timeout,
        max_retries=config.auditboard.max_retries,
        retry_delay=config.auditboard.retry_delay
    )

    # Production warning
    safety = SafetyChecker(logger, dry_run)
    if not dry_run:
        if not safety.confirm_production(config.auditboard.base_url):
            sys.exit(1)

    # Get controls to delete
    controls = []

    if args.ids:
        controls = get_controls_by_ids(args.ids, client, logger)
    elif args.ids_file:
        with open(args.ids_file, 'r') as f:
            control_ids = json.load(f)
        controls = get_controls_by_ids(control_ids, client, logger)
    elif args.pattern:
        controls = get_controls_by_pattern(args.pattern, client, logger, args.case_sensitive)

    # Delete controls
    results = delete_controls_bulk(controls, client, logger, config, dry_run)

    # Save results
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "dryrun" if dry_run else "live"
        output_file = f"{config.deletion.results_dir}/controls_deletion_{mode}_{timestamp}.json"

    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")

    if dry_run:
        logger.info("\n💡 To execute for real, add --live flag")


if __name__ == "__main__":
    main()
