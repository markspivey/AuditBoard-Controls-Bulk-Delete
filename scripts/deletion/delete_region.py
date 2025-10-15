#!/usr/bin/env python3
"""
Delete Region
Delete a region after checking for dependencies.
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_client import AuditBoardClient
from core.logger import get_logger
from core.config import Config, save_results
from core.safety import SafetyChecker


def check_region_dependencies(region_id: int, client: AuditBoardClient, logger):
    """Check if region has any dependencies."""
    logger.info("Checking for dependencies...")

    dependencies = {
        "entities": [],
        "processes": []
    }

    # Check entities
    all_entities = client.get_entities()
    dependencies['entities'] = [e for e in all_entities if e.get('region_id') == region_id]

    # Check processes
    all_processes = client.get_processes()
    dependencies['processes'] = [p for p in all_processes if p.get('region_id') == region_id]

    has_dependencies = len(dependencies['entities']) > 0 or len(dependencies['processes']) > 0

    if has_dependencies:
        logger.warning(f"\n⚠️  WARNING: Region {region_id} has dependencies!")
        logger.warning(f"  Entities: {len(dependencies['entities'])}")
        logger.warning(f"  Processes: {len(dependencies['processes'])}")
        logger.warning("\nThese must be deleted first before deleting the region.")
        return False, dependencies

    logger.info("✅ No dependencies found - safe to delete")
    return True, dependencies


def delete_region(region_id: int, client: AuditBoardClient, logger, config, dry_run: bool, force: bool = False):
    """Delete a region."""
    safety = SafetyChecker(logger, dry_run)

    logger.section(f"REGION DELETION - {'DRY RUN' if dry_run else 'LIVE MODE'}")

    # Get region details
    logger.info(f"Fetching region {region_id}...")
    region = client.get_region(region_id)

    if not region:
        logger.error(f"Region {region_id} not found")
        return {"timestamp": datetime.now().isoformat(), "dry_run": dry_run, "success": False, "error": "Region not found"}

    region_name = region.get('name')
    logger.info(f"Region {region_id}: {region_name}")

    # Check dependencies unless forced
    if not force:
        safe, dependencies = check_region_dependencies(region_id, client, logger)
        if not safe:
            logger.error(f"\n❌ CANNOT DELETE REGION - Dependencies exist!")
            logger.error("Delete all entities and processes first, or use --force to skip check.")
            return {
                "timestamp": datetime.now().isoformat(),
                "dry_run": dry_run,
                "success": False,
                "error": "Dependencies exist",
                "dependencies": dependencies
            }
    else:
        logger.warning("⚠️  Force mode enabled - skipping dependency check")

    # Confirmation
    if not dry_run:
        if not safety.confirm_deletion("region", 1, confirmation_text=f"DELETE REGION {region_id}"):
            sys.exit(0)
        safety.countdown_warning(config.safety.countdown_seconds)

    logger.subsection("")

    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "region_id": region_id,
        "region_name": region_name,
        "success": False
    }

    if dry_run:
        logger.info(f"[DRY-RUN] Would delete region {region_id}: {region_name}")
        results['success'] = True
    else:
        try:
            success = client.delete_region(region_id)
            if success:
                logger.info(f"✅ Deleted region {region_id}: {region_name}")
                results['success'] = True
            else:
                logger.error(f"❌ Failed to delete region {region_id}")
                results['error'] = "API deletion failed"
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            results['error'] = str(e)

    logger.section("DELETION SUMMARY")
    logger.info(f"Region: {region_name} (ID: {region_id})")
    logger.info(f"Status: {'SUCCESS' if results['success'] else 'FAILED'}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Delete a region after checking dependencies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete region (dry-run with dependency check)
  python delete_region.py --region-id 15

  # Delete region (LIVE)
  python delete_region.py --region-id 15 --live

  # Force delete without dependency check (dangerous!)
  python delete_region.py --region-id 15 --live --force
        """
    )
    parser.add_argument('--region-id', type=int, required=True, help='Region ID to delete')
    parser.add_argument('--live', action='store_true', help='Execute live deletion')
    parser.add_argument('--force', action='store_true', help='Skip dependency check (dangerous!)')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--config', type=str, help='Config file path')
    args = parser.parse_args()

    dry_run = not args.live
    config = Config.load_from_file(args.config) if args.config else Config.load_from_env()
    logger = get_logger('delete_region')
    client = AuditBoardClient(config.auditboard.base_url, config.auditboard.api_token)

    # Production warning
    safety = SafetyChecker(logger, dry_run)
    if not dry_run:
        if not safety.confirm_production(config.auditboard.base_url):
            sys.exit(1)

    results = delete_region(args.region_id, client, logger, config, dry_run, args.force)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "dryrun" if dry_run else "live"
    output_file = args.output or f"{config.deletion.results_dir}/region_deletion_{mode}_{timestamp}.json"
    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")

    if not results['success']:
        sys.exit(1)


if __name__ == "__main__":
    main()
