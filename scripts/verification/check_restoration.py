#!/usr/bin/env python3
"""
Check Restoration
Verify that previously deleted entities have been restored.
"""
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_client import AuditBoardClient
from core.logger import get_logger
from core.config import Config, save_results


def check_restoration(entity_type: str, entity_ids: list, expected_names: dict, client: AuditBoardClient, logger):
    """
    Check if entities have been restored.

    Args:
        entity_type: Type of entity (controls, processes, entities, etc.)
        entity_ids: List of entity IDs to check
        expected_names: Dict mapping ID to expected name (optional)
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Dict with restoration status
    """
    logger.section(f"CHECKING {entity_type.upper()} RESTORATION")

    logger.info(f"Checking if {len(entity_ids)} {entity_type} have been restored...")
    logger.subsection("")

    results = {
        "entity_type": entity_type,
        "restored": [],
        "still_missing": []
    }

    # Get appropriate getter method
    getter_map = {
        'controls': client.get_control,
        'processes': client.get_process,
        'subprocesses': client.get_subprocess,
        'entities': client.get_entity,
        'auditable_entities': client.get_auditable_entity,
        'regions': client.get_region
    }

    getter = getter_map.get(entity_type)
    if not getter:
        logger.error(f"Unknown entity type: {entity_type}")
        return results

    for entity_id in entity_ids:
        expected_name = expected_names.get(entity_id, "Unknown") if expected_names else "Unknown"

        logger.info(f"\nChecking {entity_type[:-1]} {entity_id}:")
        if expected_name != "Unknown":
            logger.info(f"  Expected: {expected_name[:60]}")

        entity = getter(entity_id)

        if entity:
            actual_name = entity.get('name', entity.get('uid', 'N/A'))
            logger.info(f"  Status: ✅ RESTORED")
            logger.info(f"  Actual: {actual_name[:60]}")
            results['restored'].append({
                'id': entity_id,
                'name': actual_name,
                'entity': entity
            })
        else:
            logger.warning(f"  Status: ❌ STILL MISSING")
            results['still_missing'].append({
                'id': entity_id,
                'expected_name': expected_name
            })

    # Summary
    logger.section("RESTORATION SUMMARY")
    logger.info(f"Total {entity_type} checked: {len(entity_ids)}")
    logger.info(f"Restored: {len(results['restored'])}")
    logger.info(f"Still missing: {len(results['still_missing'])}")

    if results['restored']:
        logger.info(f"\n✅ Restored {entity_type}:")
        for item in results['restored']:
            logger.info(f"   - {entity_type[:-1].capitalize()} {item['id']}: {item['name'][:60]}")

    if results['still_missing']:
        logger.warning(f"\n❌ Still missing:")
        for item in results['still_missing']:
            logger.warning(f"   - {entity_type[:-1].capitalize()} {item['id']}: {item['expected_name'][:60]}")
        logger.warning("\n⚠️  Action required: Contact AuditBoard support or recreate manually")
    else:
        logger.info(f"\n🎉 All {entity_type} have been successfully restored!")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Check if deleted entities have been restored',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check controls restoration
  python check_restoration.py --type controls --ids 100 101 102

  # Check entities with expected names
  python check_restoration.py --type entities --ids 25 26 --names '{"25": "Entity 25", "26": "Entity 26"}'

  # Load IDs from file
  python check_restoration.py --type controls --ids-file control_ids.json
        """
    )

    parser.add_argument('--type', type=str, required=True,
                        choices=['controls', 'processes', 'subprocesses', 'entities', 'auditable_entities', 'regions'],
                        help='Type of entity to check')
    parser.add_argument('--ids', type=int, nargs='+',
                        help='Entity IDs to check')
    parser.add_argument('--ids-file', type=str,
                        help='JSON file containing list of IDs')
    parser.add_argument('--names', type=str,
                        help='JSON dict mapping ID to expected name')
    parser.add_argument('--names-file', type=str,
                        help='JSON file containing ID to name mapping')
    parser.add_argument('--output', type=str,
                        help='Output file path')
    parser.add_argument('--config', type=str,
                        help='Config file path')

    args = parser.parse_args()

    # Validate arguments
    if not args.ids and not args.ids_file:
        parser.error("Must specify --ids or --ids-file")

    # Load IDs
    if args.ids:
        entity_ids = args.ids
    else:
        with open(args.ids_file, 'r') as f:
            entity_ids = json.load(f)

    # Load expected names
    expected_names = {}
    if args.names:
        expected_names = json.loads(args.names)
        # Convert string keys to int
        expected_names = {int(k): v for k, v in expected_names.items()}
    elif args.names_file:
        with open(args.names_file, 'r') as f:
            expected_names = json.load(f)
            expected_names = {int(k): v for k, v in expected_names.items()}

    # Load configuration
    if args.config:
        config = Config.load_from_file(args.config)
    else:
        config = Config.load_from_env()

    # Initialize logger
    logger = get_logger('check_restoration')

    # Initialize API client
    client = AuditBoardClient(
        base_url=config.auditboard.base_url,
        api_token=config.auditboard.api_token,
        timeout=config.auditboard.timeout,
        max_retries=config.auditboard.max_retries,
        retry_delay=config.auditboard.retry_delay
    )

    # Check restoration
    results = check_restoration(args.type, entity_ids, expected_names, client, logger)

    # Save results
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{config.deletion.results_dir}/restoration_check_{args.type}_{timestamp}.json"

    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")

    # Exit with error if any still missing
    if results['still_missing']:
        sys.exit(1)


if __name__ == "__main__":
    main()
