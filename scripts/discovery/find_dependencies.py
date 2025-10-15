#!/usr/bin/env python3
"""
Find Dependencies
Check for dependencies before deleting entities, processes, or regions.
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


def check_entity_dependencies(entity_ids: list, client: AuditBoardClient, logger):
    """
    Check if entities have process dependencies (processes_data links).

    Args:
        entity_ids: List of entity IDs to check
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Dict with dependency information
    """
    logger.info(f"Checking dependencies for {len(entity_ids)} entities...")

    # Get all processes_data
    processes_data = client.get('processes_data')
    all_pd = processes_data.get('processes_data', [])
    logger.info(f"Total processes_data in environment: {len(all_pd)}")

    # Find processes_data linked to our entities
    entity_pd = [pd for pd in all_pd if pd.get('entity_id') in entity_ids]

    logger.info(f"Processes_data linked to these entities: {len(entity_pd)}")

    results = {
        'entity_ids': entity_ids,
        'has_dependencies': len(entity_pd) > 0,
        'processes_data': entity_pd,
        'processes_data_count': len(entity_pd)
    }

    if entity_pd:
        logger.warning("\n⚠️  WARNING: Found processes_data entries that must be deleted first!")
        logger.subsection("")
        for pd in entity_pd[:10]:  # Show first 10
            logger.warning(f"  • processes_data ID: {pd.get('id')}")
            logger.warning(f"    Entity ID: {pd.get('entity_id')}")
            logger.warning(f"    Process ID: {pd.get('process_id')}")
        if len(entity_pd) > 10:
            logger.warning(f"  ... and {len(entity_pd) - 10} more")

        pd_ids = [pd.get('id') for pd in entity_pd]
        logger.warning(f"\nProcesses_data IDs to delete: {pd_ids}")
    else:
        logger.info("\n✅ No processes_data dependencies - entities can be deleted directly")

    return results


def check_process_dependencies(process_ids: list, client: AuditBoardClient, logger):
    """
    Check if processes have subprocess dependencies.

    Args:
        process_ids: List of process IDs to check
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Dict with dependency information
    """
    logger.info(f"Checking dependencies for {len(process_ids)} processes...")

    # Get all subprocesses
    all_subprocesses = client.get_subprocesses()
    process_subprocesses = [sp for sp in all_subprocesses if sp.get('process_id') in process_ids]

    logger.info(f"Subprocesses linked to these processes: {len(process_subprocesses)}")

    results = {
        'process_ids': process_ids,
        'has_dependencies': len(process_subprocesses) > 0,
        'subprocesses': process_subprocesses,
        'subprocesses_count': len(process_subprocesses)
    }

    if process_subprocesses:
        logger.warning("\n⚠️  WARNING: Found subprocesses that must be deleted first!")
        logger.subsection("")
        for sp in process_subprocesses[:10]:
            logger.warning(f"  • Subprocess {sp.get('id')}: {sp.get('uid')}")
            logger.warning(f"    Name: {sp.get('name')}")
            logger.warning(f"    Process ID: {sp.get('process_id')}")
        if len(process_subprocesses) > 10:
            logger.warning(f"  ... and {len(process_subprocesses) - 10} more")
    else:
        logger.info("\n✅ No subprocess dependencies - processes can be deleted directly")

    return results


def check_subprocess_dependencies(subprocess_ids: list, client: AuditBoardClient, logger):
    """
    Check if subprocesses have control dependencies.

    Args:
        subprocess_ids: List of subprocess IDs to check
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Dict with dependency information
    """
    logger.info(f"Checking dependencies for {len(subprocess_ids)} subprocesses...")

    # Get all controls
    all_controls = client.get_controls()
    subprocess_controls = [c for c in all_controls if c.get('subprocess_id') in subprocess_ids]

    logger.info(f"Controls linked to these subprocesses: {len(subprocess_controls)}")

    results = {
        'subprocess_ids': subprocess_ids,
        'has_dependencies': len(subprocess_controls) > 0,
        'controls': subprocess_controls,
        'controls_count': len(subprocess_controls)
    }

    if subprocess_controls:
        logger.warning("\n⚠️  WARNING: Found controls that must be deleted first!")
        logger.subsection("")
        for ctrl in subprocess_controls[:10]:
            logger.warning(f"  • Control {ctrl.get('id')}: {ctrl.get('uid')}")
            logger.warning(f"    Name: {ctrl.get('name', 'N/A')[:50]}")
            logger.warning(f"    Subprocess ID: {ctrl.get('subprocess_id')}")
        if len(subprocess_controls) > 10:
            logger.warning(f"  ... and {len(subprocess_controls) - 10} more")
    else:
        logger.info("\n✅ No control dependencies - subprocesses can be deleted directly")

    return results


def check_region_dependencies(region_id: int, client: AuditBoardClient, logger):
    """
    Check if a region has entity dependencies.

    Args:
        region_id: Region ID to check
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Dict with dependency information
    """
    logger.info(f"Checking dependencies for region {region_id}...")

    # Get all entities in this region
    all_entities = client.get_entities()
    region_entities = [e for e in all_entities if e.get('region_id') == region_id]

    # Get all processes in this region
    all_processes = client.get_processes()
    region_processes = [p for p in all_processes if p.get('region_id') == region_id]

    logger.info(f"Entities linked to this region: {len(region_entities)}")
    logger.info(f"Processes linked to this region: {len(region_processes)}")

    results = {
        'region_id': region_id,
        'has_dependencies': len(region_entities) > 0 or len(region_processes) > 0,
        'entities': region_entities,
        'entities_count': len(region_entities),
        'processes': region_processes,
        'processes_count': len(region_processes)
    }

    if region_entities or region_processes:
        logger.warning("\n⚠️  WARNING: Region has dependencies that must be deleted first!")
        logger.subsection("")

        if region_entities:
            logger.warning(f"  Entities: {len(region_entities)}")
            for entity in region_entities[:5]:
                logger.warning(f"    • Entity {entity.get('id')}: {entity.get('name', 'N/A')[:40]}")
            if len(region_entities) > 5:
                logger.warning(f"    ... and {len(region_entities) - 5} more")

        if region_processes:
            logger.warning(f"  Processes: {len(region_processes)}")
            for proc in region_processes[:5]:
                logger.warning(f"    • Process {proc.get('id')}: {proc.get('uid')} - {proc.get('name', 'N/A')[:40]}")
            if len(region_processes) > 5:
                logger.warning(f"    ... and {len(region_processes) - 5} more")
    else:
        logger.info("\n✅ No dependencies - region can be deleted directly")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Check for dependencies before deletion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check entity dependencies
  python find_dependencies.py --type entities --ids 25 26 27 28

  # Check process dependencies
  python find_dependencies.py --type processes --ids 48 49 50

  # Check subprocess dependencies
  python find_dependencies.py --type subprocesses --ids 86 87 88

  # Check region dependencies
  python find_dependencies.py --type region --id 15
        """
    )

    parser.add_argument('--type', type=str, required=True,
                        choices=['entities', 'processes', 'subprocesses', 'region'],
                        help='Type of entity to check')
    parser.add_argument('--ids', type=int, nargs='+',
                        help='IDs to check (for entities, processes, subprocesses)')
    parser.add_argument('--id', type=int,
                        help='Single ID to check (for region)')
    parser.add_argument('--output', type=str,
                        help='Output file path')
    parser.add_argument('--config', type=str,
                        help='Path to config file (optional)')

    args = parser.parse_args()

    # Validate arguments
    if args.type == 'region' and not args.id:
        parser.error("--id required when type is 'region'")
    if args.type != 'region' and not args.ids:
        parser.error("--ids required when type is not 'region'")

    # Load configuration
    if args.config:
        config = Config.load_from_file(args.config)
    else:
        config = Config.load_from_env()

    # Initialize logger
    logger = get_logger('find_dependencies')

    # Initialize API client
    client = AuditBoardClient(
        base_url=config.auditboard.base_url,
        api_token=config.auditboard.api_token,
        timeout=config.auditboard.timeout,
        max_retries=config.auditboard.max_retries,
        retry_delay=config.auditboard.retry_delay
    )

    logger.section(f"CHECKING {args.type.upper()} DEPENDENCIES")

    # Check dependencies
    if args.type == 'entities':
        results = check_entity_dependencies(args.ids, client, logger)
    elif args.type == 'processes':
        results = check_process_dependencies(args.ids, client, logger)
    elif args.type == 'subprocesses':
        results = check_subprocess_dependencies(args.ids, client, logger)
    elif args.type == 'region':
        results = check_region_dependencies(args.id, client, logger)

    # Save results
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{config.deletion.results_dir}/dependencies_{args.type}_{timestamp}.json"

    save_results(results, output_file)
    logger.info(f"\n✓ Results saved to: {output_file}")

    # Exit with error code if dependencies found
    if results.get('has_dependencies'):
        sys.exit(1)


if __name__ == "__main__":
    main()
