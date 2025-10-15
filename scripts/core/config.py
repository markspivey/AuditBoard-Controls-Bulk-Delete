#!/usr/bin/env python3
"""
Configuration Management
Load and manage configuration from files and environment variables.
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AuditBoardConfig:
    """AuditBoard connection configuration."""
    base_url: str
    api_token: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0


@dataclass
class SafetyConfig:
    """Safety settings configuration."""
    dry_run_default: bool = True
    require_confirmation: bool = True
    rate_limit_delay: float = 1.0
    countdown_seconds: int = 5


@dataclass
class DeletionConfig:
    """Deletion operation configuration."""
    batch_size: int = 10
    pause_every_n: int = 5
    save_results: bool = True
    results_dir: str = 'results'


class Config:
    """Main configuration manager."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to YAML config file (optional)
        """
        self.config_data = {}

        # Load config file if provided
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                self.config_data = yaml.safe_load(f) or {}

        # Parse configurations
        self.auditboard = self._load_auditboard_config()
        self.safety = self._load_safety_config()
        self.deletion = self._load_deletion_config()

    def _load_auditboard_config(self) -> AuditBoardConfig:
        """Load AuditBoard connection config."""
        ab_config = self.config_data.get('auditboard', {})

        # Environment variables take precedence
        base_url = os.getenv('AUDITBOARD_BASE_URL') or ab_config.get('base_url')
        api_token = os.getenv('AUDITBOARD_API_TOKEN') or ab_config.get('api_token')

        if not base_url:
            raise ValueError("AUDITBOARD_BASE_URL not configured")
        if not api_token:
            raise ValueError("AUDITBOARD_API_TOKEN not configured")

        return AuditBoardConfig(
            base_url=base_url,
            api_token=api_token,
            timeout=ab_config.get('timeout', 30),
            max_retries=ab_config.get('max_retries', 3),
            retry_delay=ab_config.get('retry_delay', 2.0)
        )

    def _load_safety_config(self) -> SafetyConfig:
        """Load safety settings config."""
        safety_config = self.config_data.get('safety', {})

        # Check DRY_RUN environment variable
        dry_run_env = os.getenv('DRY_RUN', 'true').lower()
        dry_run_default = dry_run_env in ['true', '1', 'yes']

        return SafetyConfig(
            dry_run_default=dry_run_default,
            require_confirmation=safety_config.get('require_confirmation', True),
            rate_limit_delay=safety_config.get('rate_limit_delay', 1.0),
            countdown_seconds=safety_config.get('countdown_seconds', 5)
        )

    def _load_deletion_config(self) -> DeletionConfig:
        """Load deletion operation config."""
        deletion_config = self.config_data.get('deletion', {})

        return DeletionConfig(
            batch_size=deletion_config.get('batch_size', 10),
            pause_every_n=deletion_config.get('pause_every_n', 5),
            save_results=deletion_config.get('save_results', True),
            results_dir=deletion_config.get('results_dir', 'results')
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., 'auditboard.timeout')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config_data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    @staticmethod
    def load_from_file(config_file: str) -> 'Config':
        """
        Load configuration from YAML file.

        Args:
            config_file: Path to YAML config file

        Returns:
            Config instance
        """
        return Config(config_file=config_file)

    @staticmethod
    def load_from_env() -> 'Config':
        """
        Load configuration from environment variables only.

        Returns:
            Config instance
        """
        return Config()


def load_deletion_plan(plan_file: str) -> Dict[str, Any]:
    """
    Load deletion plan from JSON file.

    Args:
        plan_file: Path to deletion plan JSON file

    Returns:
        Deletion plan dict
    """
    with open(plan_file, 'r') as f:
        return json.load(f)


def save_results(results: Dict[str, Any], output_file: str):
    """
    Save deletion results to JSON file.

    Args:
        results: Results dictionary
        output_file: Output file path
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
