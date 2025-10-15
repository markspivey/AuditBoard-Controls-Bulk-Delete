#!/usr/bin/env python3
"""
Safety Utilities
Safety checks and confirmations for deletion operations.
"""
import os
import sys
import time
from typing import List, Dict, Optional
from .logger import ScriptLogger


class SafetyChecker:
    """Safety checks and confirmations for deletion operations."""

    def __init__(self, logger: ScriptLogger, dry_run: bool = True):
        """
        Initialize safety checker.

        Args:
            logger: Logger instance
            dry_run: Whether in dry-run mode (default True)
        """
        self.logger = logger
        self.dry_run = dry_run

    def confirm_deletion(
        self,
        item_type: str,
        item_count: int,
        confirmation_text: Optional[str] = None,
        skip_confirm: bool = False
    ) -> bool:
        """
        Require user confirmation for deletion.

        Args:
            item_type: Type of items being deleted (e.g., "controls", "processes")
            item_count: Number of items to delete
            confirmation_text: Custom confirmation text to require
            skip_confirm: Skip confirmation prompt (use with caution!)

        Returns:
            True if confirmed, False otherwise
        """
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would delete {item_count} {item_type}")
            return True

        if skip_confirm:
            self.logger.warning("⚠️  Confirmation skipped with --confirm flag")
            self.logger.warning(f"⚠️  PERMANENTLY DELETING {item_count} {item_type}!")
            return True

        # Default confirmation text
        if confirmation_text is None:
            confirmation_text = f"DELETE {item_count} {item_type.upper()}"

        print(f"\n⚠️  WARNING: You are about to PERMANENTLY DELETE {item_count} {item_type}!")
        print("This operation CANNOT be undone!")
        print(f"\nType '{confirmation_text}' to confirm: ", end='')

        try:
            user_input = input()
            if user_input == confirmation_text:
                return True
            else:
                print("Confirmation failed. Exiting.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            return False

    def countdown_warning(self, seconds: int = 5):
        """
        Display countdown warning before dangerous operation.

        Args:
            seconds: Countdown duration in seconds
        """
        if self.dry_run:
            return

        self.logger.warning("⚠️  WARNING: LIVE DELETION MODE - This will permanently delete data!")
        self.logger.warning(f"⚠️  Press Ctrl+C within {seconds} seconds to abort...")

        try:
            time.sleep(seconds)
        except KeyboardInterrupt:
            self.logger.info("Aborted by user")
            sys.exit(0)

    def check_dependencies(
        self,
        item_type: str,
        item_id: int,
        dependencies: Dict[str, List]
    ) -> bool:
        """
        Check for dependencies before deletion.

        Args:
            item_type: Type of item being deleted
            item_id: ID of item
            dependencies: Dict of dependency types and their items

        Returns:
            True if safe to delete (no dependencies), False otherwise
        """
        has_dependencies = False

        for dep_type, items in dependencies.items():
            if items:
                has_dependencies = True
                self.logger.error(
                    f"⚠️  WARNING: Found {len(items)} {dep_type} linked to {item_type} {item_id}"
                )

                # Show first 5 dependencies
                for item in items[:5]:
                    item_id_str = item.get('id', 'N/A')
                    item_name = item.get('name', item.get('uid', 'N/A'))
                    self.logger.error(f"   - {dep_type[:-1]} {item_id_str}: {item_name}")

                if len(items) > 5:
                    self.logger.error(f"   ... and {len(items) - 5} more")

        if has_dependencies:
            self.logger.error(f"\n❌ CANNOT DELETE {item_type.upper()} - Dependencies still exist!")
            self.logger.error("Please delete dependent items first.")
            return False

        self.logger.info("✅ No dependencies found - safe to delete")
        return True

    def validate_environment(self):
        """
        Validate required environment variables are set.

        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = ['AUDITBOARD_BASE_URL', 'AUDITBOARD_API_TOKEN']
        missing = []

        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set these in your .env file or environment."
            )

    def confirm_production(self, base_url: str) -> bool:
        """
        Extra confirmation if operating on production environment.

        Args:
            base_url: AuditBoard base URL

        Returns:
            True if confirmed, False otherwise
        """
        if 'sandbox' in base_url.lower():
            return True  # Sandbox - no extra confirmation needed

        if self.dry_run:
            return True  # Dry run - safe

        print("\n" + "=" * 80)
        print("⚠️  PRODUCTION ENVIRONMENT DETECTED")
        print("=" * 80)
        print(f"Base URL: {base_url}")
        print("\nYou are about to perform operations on a PRODUCTION environment.")
        print("This is NOT a sandbox or test environment.")
        print("\nType 'I UNDERSTAND THIS IS PRODUCTION' to continue: ", end='')

        try:
            user_input = input()
            if user_input == "I UNDERSTAND THIS IS PRODUCTION":
                return True
            else:
                print("Confirmation failed. Exiting.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            return False


def is_dry_run() -> bool:
    """
    Check if dry-run mode is enabled.

    Checks --dry-run flag and DRY_RUN environment variable.

    Returns:
        True if dry-run mode, False otherwise
    """
    # Check command line args
    if '--dry-run' in sys.argv:
        return True

    # Check if --live flag is present (overrides dry-run)
    if '--live' in sys.argv:
        return False

    # Check environment variable (default to True for safety)
    dry_run_env = os.getenv('DRY_RUN', 'true').lower()
    return dry_run_env in ['true', '1', 'yes']
