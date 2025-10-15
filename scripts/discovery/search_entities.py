#!/usr/bin/env python3
"""
Search Entities
Search for controls, processes, subprocesses, or entities by pattern.
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


def search_controls(client: AuditBoardClient, logger, pattern: str, case_sensitive: bool = False):
    """
    Search for controls matching a pattern.

    Args:
        client: AuditBoard API client
        logger: Logger instance
        pattern: Search pattern (substring match)
        case_sensitive: Whether search is case-sensitive

    Returns:
        List of matching controls with hierarchy info
    """
    logger.info(f"Searching controls for pattern: '{pattern}'")
    logger.info(f"Case sensitive: {case_sensitive}")

    # Get all controls
    all_controls = client.get_controls()
    logger.info(f"Total controls in environment: {len(all_controls)}")

    # Get supporting data for hierarchy
    all_subprocesses = client.get_subprocesses()
    sp_map = {sp['id']: sp for sp in all_subprocesses}

    all_processes = client.get_processes()
    proc_map = {p['id']: p for p in all_processes}

    all_regions = client.get_regions()
    region_map = {r['id']: r for r in all_regions}

    # Search
    matching_controls = []

    for ctrl in all_controls:
        ctrl_uid = ctrl.get('uid', '')
        ctrl_name = ctrl.get('name', '')

        # Apply case sensitivity
        if not case_sensitive:
            ctrl_uid = ctrl_uid.lower()
            ctrl_name = ctrl_name.lower()
            search_pattern = pattern.lower()
        else:
            search_pattern = pattern

        # Check if matches pattern
        if search_pattern in ctrl_uid or search_pattern in ctrl_name:
            # Get hierarchy info
            sp_id = ctrl.get('subprocess_id')
            subprocess = sp_map.get(sp_id, {})
            process_id = subprocess.get('process_id')
            process = proc_map.get(process_id, {})
            region_id = process.get('region_id')
            region = region_map.get(region_id, {})

            matching_controls.append({
                'control': ctrl,
                'subprocess': subprocess,
                'process': process,
                'region': region
            })

    logger.info(f"Found {len(matching_controls)} matching controls")
    return matching_controls


def search_processes(client: AuditBoardClient, logger, pattern: str, case_sensitive: bool = False):
    """Search for processes matching a pattern."""
    logger.info(f"Searching processes for pattern: '{pattern}'")

    all_processes = client.get_processes()
    logger.info(f"Total processes in environment: {len(all_processes)}")

    matching = []
    for proc in all_processes:
        proc_uid = proc.get('uid', '')
        proc_name = proc.get('name', '')

        if not case_sensitive:
            proc_uid = proc_uid.lower()
            proc_name = proc_name.lower()
            search_pattern = pattern.lower()
        else:
            search_pattern = pattern

        if search_pattern in proc_uid or search_pattern in proc_name:
            matching.append(proc)

    logger.info(f"Found {len(matching)} matching processes")
    return matching


def search_entities(client: AuditBoardClient, logger, pattern: str, case_sensitive: bool = False):
    """Search for entities matching a pattern."""
    logger.info(f"Searching entities for pattern: '{pattern}'")

    all_entities = client.get_entities()
    logger.info(f"Total entities in environment: {len(all_entities)}")

    matching = []
    for entity in all_entities:
        entity_uid = entity.get('uid', '') or ''
        entity_name = entity.get('name', '')

        if not case_sensitive:
            entity_uid = entity_uid.lower()
            entity_name = entity_name.lower()
            search_pattern = pattern.lower()
        else:
            search_pattern = pattern

        if search_pattern in entity_uid or search_pattern in entity_name:
            matching.append(entity)

    logger.info(f"Found {len(matching)} matching entities")
    return matching


def display_control_results(results, logger):
    """Display control search results grouped by region."""
    if not results:
        logger.info("No results to display")
        return

    # Group by region
    by_region = {}
    for item in results:
        region_name = item['region'].get('name', 'Unknown')
        region_id = item['region'].get('id', 'N/A')
        key = f"{region_name} (ID: {region_id})"

        if key not in by_region:
            by_region[key] = []
        by_region[key].append(item)

    logger.subsection("RESULTS BY REGION")

    for region_key, items in sorted(by_region.items()):
        logger.info(f"\n📍 {region_key}: {len(items)} controls")

        for item in items[:10]:  # Show first 10
            ctrl = item['control']
            sp = item['subprocess']
            proc = item['process']

            logger.info(f"   • Control {ctrl.get('id')}: {ctrl.get('uid')}")
            logger.info(f"     Name: {ctrl.get('name', 'N/A')[:60]}")
            logger.info(f"     Subprocess: {sp.get('uid', 'N/A')} - {sp.get('name', 'N/A')[:40]}")
            logger.info(f"     Process: {proc.get('uid', 'N/A')} - {proc.get('name', 'N/A')[:40]}")

        if len(items) > 10:
            logger.info(f"   ... and {len(items) - 10} more controls")


def display_process_results(results, logger):
    """Display process search results."""
    if not results:
        logger.info("No results to display")
        return

    logger.subsection("RESULTS")

    for proc in results[:20]:  # Show first 20
        logger.info(f"   • Process {proc.get('id')}: {proc.get('uid')}")
        logger.info(f"     Name: {proc.get('name', 'N/A')[:60]}")
        logger.info(f"     Region ID: {proc.get('region_id')}")

    if len(results) > 20:
        logger.info(f"   ... and {len(results) - 20} more processes")


def display_entity_results(results, logger):
    """Display entity search results."""
    if not results:
        logger.info("No results to display")
        return

    logger.subsection("RESULTS")

    for entity in results[:20]:  # Show first 20
        logger.info(f"   • Entity {entity.get('id')}: {entity.get('uid', 'N/A')}")
        logger.info(f"     Name: {entity.get('name', 'N/A')[:60]}")
        logger.info(f"     Region ID: {entity.get('region_id')}")

    if len(results) > 20:
        logger.info(f"   ... and {len(results) - 20} more entities")


def main():
    parser = argparse.ArgumentParser(
        description='Search for AuditBoard entities by pattern',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search controls for pattern
  python search_entities.py --type controls --pattern "CC"

  # Search processes (case-sensitive)
  python search_entities.py --type processes --pattern "Compliance" --case-sensitive

  # Search entities
  python search_entities.py --type entities --pattern "Payment"

  # Save results to custom file
  python search_entities.py --type controls --pattern "CC" --output my_results.json
        """
    )

    parser.add_argument('--type', type=str, required=True,
                        choices=['controls', 'processes', 'entities'],
                        help='Type of entity to search')
    parser.add_argument('--pattern', type=str, required=True,
                        help='Search pattern (substring match in UID or name)')
    parser.add_argument('--case-sensitive', action='store_true',
                        help='Enable case-sensitive search')
    parser.add_argument('--output', type=str,
                        help='Output file path (default: results/search_<type>_<timestamp>.json)')
    parser.add_argument('--config', type=str,
                        help='Path to config file (optional)')

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = Config.load_from_file(args.config)
    else:
        config = Config.load_from_env()

    # Initialize logger
    logger = get_logger('search_entities')

    # Initialize API client
    client = AuditBoardClient(
        base_url=config.auditboard.base_url,
        api_token=config.auditboard.api_token,
        timeout=config.auditboard.timeout,
        max_retries=config.auditboard.max_retries,
        retry_delay=config.auditboard.retry_delay
    )

    logger.section(f"SEARCHING {args.type.upper()}")

    # Execute search
    if args.type == 'controls':
        results = search_controls(client, logger, args.pattern, args.case_sensitive)
        display_control_results(results, logger)
    elif args.type == 'processes':
        results = search_processes(client, logger, args.pattern, args.case_sensitive)
        display_process_results(results, logger)
    elif args.type == 'entities':
        results = search_entities(client, logger, args.pattern, args.case_sensitive)
        display_entity_results(results, logger)

    # Save results
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{config.deletion.results_dir}/search_{args.type}_{timestamp}.json"

    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
