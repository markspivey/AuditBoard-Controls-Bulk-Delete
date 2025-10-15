#!/usr/bin/env python3
"""
Verify Restoration
Deep comparison of restored entities against original deleted data.
Verifies perfect restoration with all metadata intact.
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


def compare_entity(original: dict, restored: dict, logger):
    """
    Compare original and restored entity data.

    Returns:
        Tuple of (matches, differences)
    """
    differences = []
    matches = []

    # Compare ID
    if original.get('id') == restored.get('id'):
        matches.append(f"✅ ID: {original.get('id')}")
    else:
        differences.append(f"❌ ID: {original.get('id')} → {restored.get('id')}")

    # Compare name
    if original.get('name') == restored.get('name'):
        matches.append(f"✅ Name: {original.get('name', 'N/A')[:60]}")
    else:
        differences.append(f"❌ Name changed")

    # Compare other key fields
    key_fields = ['uid', 'region_id', 'entity_type_id', 'process_id', 'subprocess_id']
    for field in key_fields:
        if field in original:
            if original.get(field) == restored.get(field):
                matches.append(f"✅ {field}: {original.get(field)}")
            else:
                differences.append(f"❌ {field}: {original.get(field)} → {restored.get(field)}")

    return matches, differences


def verify_restoration(entity_type: str, original_data: list, client: AuditBoardClient, logger):
    """
    Verify entities were perfectly restored.

    Args:
        entity_type: Type of entity
        original_data: List of original entity dicts before deletion
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Verification results dict
    """
    logger.section(f"VERIFYING {entity_type.upper()} RESTORATION")

    logger.info(f"Comparing {len(original_data)} {entity_type} against restored data...")
    logger.subsection("")

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
        return {"perfect_restoration": False, "error": "Unknown entity type"}

    results = {
        "perfect_restoration": True,
        "entity_type": entity_type,
        "entities": []
    }

    for original in original_data:
        entity_id = original.get('id')

        logger.subsection(f"Entity {entity_id}: {original.get('name', original.get('uid', 'N/A'))[:60]}")

        restored = getter(entity_id)

        if not restored:
            logger.error(f"❌ ERROR: Entity {entity_id} not found!")
            results['perfect_restoration'] = False
            results['entities'].append({
                'id': entity_id,
                'status': 'NOT_FOUND',
                'matches': [],
                'differences': []
            })
            continue

        matches, differences = compare_entity(original, restored, logger)

        entity_result = {
            'id': entity_id,
            'status': 'PERFECT' if not differences else 'PARTIAL',
            'matches': matches,
            'differences': differences,
            'original': original,
            'restored': restored
        }

        results['entities'].append(entity_result)

        if differences:
            results['perfect_restoration'] = False
            logger.warning(f"\n⚠️  DIFFERENCES FOUND:")
            for diff in differences:
                logger.warning(f"   {diff}")

        logger.info(f"\n✅ MATCHES:")
        for match in matches:
            logger.info(f"   {match}")

        # Show all restored fields
        logger.info(f"\n📋 KEY RESTORED FIELDS:")
        key_fields = ['id', 'uid', 'name', 'region_id', 'created_at', 'updated_at']
        for key in key_fields:
            if key in restored:
                value = restored[key]
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                logger.info(f"   {key}: {value}")

    # Final summary
    logger.section("RESTORATION VERIFICATION SUMMARY")

    if results['perfect_restoration']:
        logger.info("\n🎉 PERFECT RESTORATION CONFIRMED!")
        logger.info("   All entities restored with:")
        logger.info("   ✅ Same IDs")
        logger.info("   ✅ Same names")
        logger.info("   ✅ All key metadata intact")
    else:
        logger.warning("\n⚠️  PARTIAL RESTORATION - Some differences detected")
        logger.warning("   Review differences above")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Verify perfect restoration by comparing against original data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify restoration from deletion results file
  python verify_restoration.py --type controls --original-file controls_deletion_live.json

  # Verify with custom comparison
  python verify_restoration.py --type entities --original-file original_entities.json
        """
    )

    parser.add_argument('--type', type=str, required=True,
                        choices=['controls', 'processes', 'subprocesses', 'entities', 'auditable_entities', 'regions'],
                        help='Type of entity to verify')
    parser.add_argument('--original-file', type=str, required=True,
                        help='JSON file containing original entity data before deletion')
    parser.add_argument('--output', type=str,
                        help='Output file path')
    parser.add_argument('--config', type=str,
                        help='Config file path')

    args = parser.parse_args()

    # Load original data
    with open(args.original_file, 'r') as f:
        original_file_data = json.load(f)

    # Extract entity list (handle different file formats)
    if isinstance(original_file_data, list):
        original_data = original_file_data
    elif 'deleted' in original_file_data:
        original_data = original_file_data['deleted']
    elif 'entities' in original_file_data:
        original_data = original_file_data['entities']
    else:
        print(f"Error: Could not find entity data in {args.original_file}")
        print("Expected format: list of entities or dict with 'deleted'/'entities' key")
        sys.exit(1)

    # Load configuration
    if args.config:
        config = Config.load_from_file(args.config)
    else:
        config = Config.load_from_env()

    # Initialize logger
    logger = get_logger('verify_restoration')

    # Initialize API client
    client = AuditBoardClient(
        base_url=config.auditboard.base_url,
        api_token=config.auditboard.api_token,
        timeout=config.auditboard.timeout,
        max_retries=config.auditboard.max_retries,
        retry_delay=config.auditboard.retry_delay
    )

    # Verify restoration
    results = verify_restoration(args.type, original_data, client, logger)

    # Save results
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{config.deletion.results_dir}/restoration_verification_{args.type}_{timestamp}.json"

    save_results(results, output_file)
    logger.info(f"\n✓ Full verification saved to: {output_file}")

    # Exit with error if not perfect restoration
    if not results['perfect_restoration']:
        sys.exit(1)


if __name__ == "__main__":
    main()
