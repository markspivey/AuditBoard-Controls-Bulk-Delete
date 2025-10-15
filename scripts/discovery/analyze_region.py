#!/usr/bin/env python3
"""
Analyze Region
Discover and display complete state of an AuditBoard region.
Shows all entities, processes, subprocesses, and controls in hierarchical order.
"""
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_client import AuditBoardClient
from core.logger import get_logger
from core.config import Config, save_results


def analyze_region(region_id: int, client: AuditBoardClient, logger):
    """
    Discover complete region state including all dependencies.

    Args:
        region_id: ID of region to analyze
        client: AuditBoard API client
        logger: Logger instance

    Returns:
        Dict containing complete region state
    """
    logger.section(f"REGION ANALYSIS - Region {region_id}")

    state = {
        "timestamp": datetime.now().isoformat(),
        "region_id": region_id,
        "region": None,
        "entities": [],
        "processes": [],
        "subprocesses": [],
        "controls": [],
        "processes_data": [],
        "subprocesses_data": [],
        "controls_data": [],
        "summary": {}
    }

    # Step 1: Get Region
    logger.info("\n1. REGION")
    logger.subsection("")
    region = client.get_region(region_id)
    if region:
        state['region'] = {
            'id': region.get('id'),
            'name': region.get('name'),
            'description': region.get('description')
        }
        logger.info(f"   ✓ Region {region.get('id')}: {region.get('name')}")
    else:
        logger.error(f"   ⚠️  Could not fetch region {region_id}")
        return state

    # Step 2: Get all entities in this region
    logger.info("\n2. ENTITIES")
    logger.subsection("")
    all_entities = client.get_entities()
    region_entities = [e for e in all_entities if e.get('region_id') == region_id]

    for entity in region_entities:
        entity_info = {
            'id': entity.get('id'),
            'name': entity.get('name'),
            'entity_type_id': entity.get('entity_type_id'),
            'region_id': entity.get('region_id')
        }
        state['entities'].append(entity_info)
        logger.info(f"   ✓ Entity {entity_info['id']}: {entity_info['name']}")

    logger.info(f"\n   Total Entities: {len(state['entities'])}")

    if not state['entities']:
        logger.warning("   No entities found in this region")

    # Step 3: Get processes_data (entity → process mappings)
    logger.info("\n3. PROCESSES_DATA (Entity → Process Links)")
    logger.subsection("")
    entity_ids = [e['id'] for e in state['entities']]

    if entity_ids:
        processes_data = client.get('processes_data')
        all_pd = processes_data.get('processes_data', [])
        region_pd = [pd for pd in all_pd if pd.get('entity_id') in entity_ids]

        for pd in region_pd:
            pd_info = {
                'id': pd.get('id'),
                'entity_id': pd.get('entity_id'),
                'process_id': pd.get('process_id')
            }
            state['processes_data'].append(pd_info)

        logger.info(f"   Total processes_data links: {len(state['processes_data'])}")

        # Group by entity
        if region_pd:
            entity_process_map = {}
            for pd in region_pd:
                entity_id = pd.get('entity_id')
                if entity_id not in entity_process_map:
                    entity_process_map[entity_id] = []
                entity_process_map[entity_id].append(pd.get('process_id'))

            for entity_id, process_ids in entity_process_map.items():
                entity_name = next((e['name'] for e in state['entities'] if e['id'] == entity_id), f"Entity {entity_id}")
                logger.info(f"   - {entity_name}: {len(process_ids)} processes")

    # Step 4: Get all processes linked to these entities
    logger.info("\n4. PROCESSES")
    logger.subsection("")
    process_ids = list(set(pd['process_id'] for pd in state['processes_data']))

    if process_ids:
        all_processes = client.get_processes()

        for proc_id in process_ids:
            proc = next((p for p in all_processes if p.get('id') == proc_id), None)
            if proc:
                proc_info = {
                    'id': proc.get('id'),
                    'name': proc.get('name'),
                    'uid': proc.get('uid'),
                    'region_id': proc.get('region_id')
                }
                state['processes'].append(proc_info)
                logger.info(f"   ✓ Process {proc_info['id']}: {proc_info['uid']} - {proc_info['name']}")

        logger.info(f"\n   Total Processes: {len(state['processes'])}")

    # Step 5: Get subprocesses_data (process_data → subprocess mappings)
    logger.info("\n5. SUBPROCESSES_DATA (Process → Subprocess Links)")
    logger.subsection("")
    processes_data_ids = [pd['id'] for pd in state['processes_data']]

    if processes_data_ids:
        subprocesses_data = client.get('subprocesses_data')
        all_spd = subprocesses_data.get('subprocesses_data', [])
        region_spd = [spd for spd in all_spd if spd.get('processes_datum_id') in processes_data_ids]

        for spd in region_spd:
            spd_info = {
                'id': spd.get('id'),
                'processes_datum_id': spd.get('processes_datum_id'),
                'subprocess_id': spd.get('subprocess_id')
            }
            state['subprocesses_data'].append(spd_info)

        logger.info(f"   Total subprocesses_data links: {len(state['subprocesses_data'])}")

    # Step 6: Get all subprocesses
    logger.info("\n6. SUBPROCESSES")
    logger.subsection("")
    subprocess_ids = list(set(spd['subprocess_id'] for spd in state['subprocesses_data']))

    if subprocess_ids:
        all_subprocesses = client.get_subprocesses()

        for sp_id in subprocess_ids:
            sp = next((s for s in all_subprocesses if s.get('id') == sp_id), None)
            if sp:
                sp_info = {
                    'id': sp.get('id'),
                    'name': sp.get('name'),
                    'uid': sp.get('uid'),
                    'process_id': sp.get('process_id')
                }
                state['subprocesses'].append(sp_info)
                logger.info(f"   ✓ Subprocess {sp_info['id']}: {sp_info['uid']} - {sp_info['name']}")

        logger.info(f"\n   Total Subprocesses: {len(state['subprocesses'])}")

    # Step 7: Get all controls in these subprocesses
    logger.info("\n7. CONTROLS")
    logger.subsection("")
    if subprocess_ids:
        all_controls = client.get_controls()
        region_controls = [c for c in all_controls if c.get('subprocess_id') in subprocess_ids]

        for ctrl in region_controls:
            ctrl_info = {
                'id': ctrl.get('id'),
                'name': ctrl.get('name'),
                'uid': ctrl.get('uid'),
                'subprocess_id': ctrl.get('subprocess_id')
            }
            state['controls'].append(ctrl_info)

        # Group by subprocess
        if region_controls:
            subprocess_control_map = {}
            for ctrl in region_controls:
                sp_id = ctrl.get('subprocess_id')
                if sp_id not in subprocess_control_map:
                    subprocess_control_map[sp_id] = []
                subprocess_control_map[sp_id].append(ctrl)

            for sp_id, controls in subprocess_control_map.items():
                sp_name = next((s['name'] for s in state['subprocesses'] if s['id'] == sp_id), f"Subprocess {sp_id}")
                logger.info(f"   - {sp_name}: {len(controls)} controls")
                for ctrl in controls[:5]:  # Show first 5
                    logger.info(f"      • {ctrl.get('uid')}: {ctrl.get('name', 'N/A')[:50]}")
                if len(controls) > 5:
                    logger.info(f"      ... and {len(controls) - 5} more")

        logger.info(f"\n   Total Controls: {len(state['controls'])}")

    # Step 8: Get controls_data (control instance data)
    logger.info("\n8. CONTROLS_DATA (Control Instances)")
    logger.subsection("")
    control_ids = [c['id'] for c in state['controls']]

    if control_ids:
        controls_data = client.get('controls_data')
        all_cd = controls_data.get('controls_data', [])
        region_cd = [cd for cd in all_cd if cd.get('control_id') in control_ids]

        for cd in region_cd:
            cd_info = {
                'id': cd.get('id'),
                'control_id': cd.get('control_id'),
                'subprocesses_datum_id': cd.get('subprocesses_datum_id')
            }
            state['controls_data'].append(cd_info)

        logger.info(f"   Total controls_data (control instances): {len(state['controls_data'])}")

    # Summary
    logger.section("ANALYSIS SUMMARY")

    state['summary'] = {
        'region': f"Region {region_id} - {state['region']['name'] if state['region'] else 'N/A'}",
        'entities_count': len(state['entities']),
        'processes_count': len(state['processes']),
        'subprocesses_count': len(state['subprocesses']),
        'controls_count': len(state['controls']),
        'controls_data_count': len(state['controls_data']),
        'processes_data_count': len(state['processes_data']),
        'subprocesses_data_count': len(state['subprocesses_data'])
    }

    logger.info(f"\n📊 Hierarchy:")
    logger.info(f"   1. Region: {state['summary']['region']}")
    logger.info(f"   2. Entities: {state['summary']['entities_count']}")
    logger.info(f"   3. Processes_Data (links): {state['summary']['processes_data_count']}")
    logger.info(f"   4. Processes: {state['summary']['processes_count']}")
    logger.info(f"   5. Subprocesses_Data (links): {state['summary']['subprocesses_data_count']}")
    logger.info(f"   6. Subprocesses: {state['summary']['subprocesses_count']}")
    logger.info(f"   7. Controls: {state['summary']['controls_count']}")
    logger.info(f"   8. Controls_Data (instances): {state['summary']['controls_data_count']}")

    total_items = (state['summary']['entities_count'] +
                   state['summary']['processes_count'] +
                   state['summary']['subprocesses_count'] +
                   state['summary']['controls_count'])

    logger.info(f"\n📈 Total Items: {total_items}")

    if total_items > 0:
        logger.warning("\n⚠️  If deleted, this would permanently remove ALL data shown above!")

    return state


def main():
    parser = argparse.ArgumentParser(
        description='Analyze AuditBoard region and display complete hierarchy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze region 15
  python analyze_region.py --region-id 15

  # Analyze with custom output file
  python analyze_region.py --region-id 15 --output my_analysis.json

  # Use custom config file
  python analyze_region.py --region-id 15 --config config/config.yaml
        """
    )

    parser.add_argument('--region-id', type=int, required=True,
                        help='ID of region to analyze')
    parser.add_argument('--output', type=str,
                        help='Output file path (default: results/region_analysis_<timestamp>.json)')
    parser.add_argument('--config', type=str,
                        help='Path to config file (optional)')

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = Config.load_from_file(args.config)
    else:
        config = Config.load_from_env()

    # Initialize logger
    logger = get_logger('analyze_region')

    # Initialize API client
    client = AuditBoardClient(
        base_url=config.auditboard.base_url,
        api_token=config.auditboard.api_token,
        timeout=config.auditboard.timeout,
        max_retries=config.auditboard.max_retries,
        retry_delay=config.auditboard.retry_delay
    )

    # Analyze region
    state = analyze_region(args.region_id, client, logger)

    # Save results
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{config.deletion.results_dir}/region_analysis_{args.region_id}_{timestamp}.json"

    save_results(state, output_file)
    logger.info(f"\n✓ Full analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
