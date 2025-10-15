#!/usr/bin/env python3
"""
Delete Entities
Bulk delete entities by ID list.
NOTE: Uses /entities endpoint (not /auditable_entities)
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


def delete_entities_bulk(entity_ids: list, client: AuditBoardClient, logger, config, dry_run: bool):
    """Delete entities in bulk."""
    safety = SafetyChecker(logger, dry_run)

    logger.section(f"ENTITIES DELETION - {'DRY RUN' if dry_run else 'LIVE MODE'}")

    # Fetch entity details
    logger.info("Fetching entity details...")
    entities = []
    for entity_id in entity_ids:
        entity = client.get_entity(entity_id)
        if entity:
            entities.append(entity)
        else:
            logger.warning(f"Entity {entity_id} not found")

    if not entities:
        logger.warning("No entities found to delete")
        return {"timestamp": datetime.now().isoformat(), "dry_run": dry_run, "total": 0, "deleted": [], "failed": []}

    total = len(entities)

    # Confirmation
    if not dry_run:
        if not safety.confirm_deletion("entities", total):
            sys.exit(0)
        safety.countdown_warning(config.safety.countdown_seconds)

    logger.info(f"Starting deletion of {total} entities...")
    logger.subsection("")

    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "total": total,
        "deleted": [],
        "failed": []
    }

    for i, entity in enumerate(entities, 1):
        entity_id = entity.get('id')
        entity_uid = entity.get('uid', 'N/A')
        entity_name = entity.get('name', 'N/A')

        logger.info(f"[{i}/{total}] Entity {entity_id}: {entity_uid}")
        logger.info(f"          Name: {entity_name[:60]}")

        if dry_run:
            logger.info(f"[DRY-RUN] Would delete entity {entity_id}")
            results['deleted'].append({'id': entity_id, 'uid': entity_uid, 'name': entity_name})
        else:
            try:
                success = client.delete_entity(entity_id)
                if success:
                    logger.info(f"✅ Deleted entity {entity_id}")
                    results['deleted'].append({'id': entity_id, 'uid': entity_uid, 'name': entity_name})
                else:
                    logger.error(f"❌ Failed to delete entity {entity_id}")
                    results['failed'].append({'id': entity_id, 'uid': entity_uid, 'name': entity_name})
            except Exception as e:
                logger.error(f"❌ Exception: {e}")
                results['failed'].append({'id': entity_id, 'uid': entity_uid, 'name': entity_name, 'error': str(e)})

            if i % config.deletion.pause_every_n == 0 and i < total:
                time.sleep(config.safety.rate_limit_delay)

    logger.section("DELETION SUMMARY")
    logger.info(f"Total: {total} | Deleted: {len(results['deleted'])} | Failed: {len(results['failed'])}")
    return results


def main():
    parser = argparse.ArgumentParser(description='Delete entities by ID list')
    parser.add_argument('--ids', type=int, nargs='+', required=True, help='Entity IDs to delete')
    parser.add_argument('--live', action='store_true', help='Execute live deletion')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--config', type=str, help='Config file path')
    args = parser.parse_args()

    dry_run = not args.live
    config = Config.load_from_file(args.config) if args.config else Config.load_from_env()
    logger = get_logger('delete_entities')
    client = AuditBoardClient(config.auditboard.base_url, config.auditboard.api_token)

    results = delete_entities_bulk(args.ids, client, logger, config, dry_run)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "dryrun" if dry_run else "live"
    output_file = args.output or f"{config.deletion.results_dir}/entities_deletion_{mode}_{timestamp}.json"
    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
