#!/usr/bin/env python3
"""
SUSE Application Collection Synchronization Agent

A comprehensive automation tool for synchronizing container versions between
SUSE Application Collection charts and local application Helm charts.

This agent:
1. Pulls latest versions of specified Helm charts from SUSE Application Collection
2. Extracts container image versions from the pulled charts
3. Updates multiple target Helm charts with the latest SUSE versions
4. Updates upstream charts to mirror SUSE versions for consistency
5. Generates comprehensive summary reports of all changes made

Author: AI Compare Team
License: MIT
"""

import os
import sys
import yaml
import json
import subprocess
import tempfile
import shutil
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('suse-sync.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ImageMapping:
    """Defines how to map images from source to target charts."""
    source_path: str  # e.g., "ollama.image"
    target_path: str  # e.g., "ollama.image"
    registry_transform: Optional[str] = None  # Transform registry paths

@dataclass
class ChartSync:
    """Configuration for a chart synchronization operation."""
    name: str
    source_chart: str  # OCI URL for SUSE Application Collection
    target_charts: List[str]  # Local chart paths to update
    image_mappings: List[ImageMapping]

@dataclass
class SyncResult:
    """Result of a synchronization operation."""
    chart_name: str
    target_chart: str
    success: bool
    changes_made: List[str]
    errors: List[str]
    old_versions: Dict[str, str]
    new_versions: Dict[str, str]

class HelmChartError(Exception):
    """Custom exception for Helm chart operations."""
    pass

class SUSEAppCollectionSync:
    """Main synchronization agent for SUSE Application Collection charts."""

    def __init__(self, config_file: str, dry_run: bool = False):
        """
        Initialize the synchronization agent.

        Args:
            config_file: Path to the configuration file
            dry_run: If True, only show what would be changed without making changes
        """
        self.config_file = config_file
        self.dry_run = dry_run
        self.temp_dir = None
        self.config = None
        self.results: List[SyncResult] = []

    def load_config(self) -> None:
        """Load configuration from the config file."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
        except Exception as e:
            raise HelmChartError(f"Failed to load config file {self.config_file}: {e}")

    def setup_temp_directory(self) -> None:
        """Create a temporary directory for chart operations."""
        self.temp_dir = tempfile.mkdtemp(prefix="suse-sync-")
        logger.info(f"Created temporary directory: {self.temp_dir}")

    def cleanup_temp_directory(self) -> None:
        """Clean up the temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temporary directory: {self.temp_dir}")

    def run_helm_command(self, command: List[str], cwd: Optional[str] = None) -> str:
        """
        Run a Helm command and return the output.

        Args:
            command: List of command arguments
            cwd: Working directory for the command

        Returns:
            Command output as string

        Raises:
            HelmChartError: If the command fails
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd or self.temp_dir,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = f"Helm command failed: {' '.join(command)}\nError: {e.stderr}"
            logger.error(error_msg)
            raise HelmChartError(error_msg)

    def pull_chart(self, chart_url: str, chart_name: str) -> str:
        """
        Pull a Helm chart from OCI registry.

        Args:
            chart_url: OCI URL of the chart
            chart_name: Name to use for the pulled chart

        Returns:
            Path to the extracted chart directory
        """
        logger.info(f"Pulling chart {chart_name} from {chart_url}")

        # Create a subdirectory for this chart
        chart_dir = os.path.join(self.temp_dir, chart_name)
        os.makedirs(chart_dir, exist_ok=True)

        # Pull the chart
        pull_command = ["helm", "pull", chart_url, "--untar", "--untardir", chart_dir]
        self.run_helm_command(pull_command)

        # Find the extracted chart directory
        extracted_dirs = [d for d in os.listdir(chart_dir) if os.path.isdir(os.path.join(chart_dir, d))]
        if not extracted_dirs:
            raise HelmChartError(f"No chart directory found after pulling {chart_url}")

        extracted_path = os.path.join(chart_dir, extracted_dirs[0])
        logger.info(f"Chart extracted to: {extracted_path}")
        return extracted_path

    def get_nested_value(self, data: Dict, path: str) -> Optional[str]:
        """
        Get a nested value from a dictionary using dot notation.

        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "ollama.image.tag")

        Returns:
            The value if found, None otherwise
        """
        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current if isinstance(current, str) else str(current) if current is not None else None

    def set_nested_value(self, data: Dict, path: str, value: str) -> None:
        """
        Set a nested value in a dictionary using dot notation.

        Args:
            data: Dictionary to modify
            path: Dot-separated path (e.g., "ollama.image.tag")
            value: Value to set
        """
        keys = path.split('.')
        current = data

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def extract_image_versions(self, chart_path: str, image_mappings: List[ImageMapping]) -> Dict[str, Dict[str, str]]:
        """
        Extract image versions from a Helm chart.

        Args:
            chart_path: Path to the extracted chart
            image_mappings: List of image mappings to extract

        Returns:
            Dictionary mapping image paths to their repository and tag
        """
        values_file = os.path.join(chart_path, "values.yaml")
        if not os.path.exists(values_file):
            raise HelmChartError(f"values.yaml not found in {chart_path}")

        with open(values_file, 'r') as f:
            values = yaml.safe_load(f)

        extracted_images = {}

        for mapping in image_mappings:
            repo_path = f"{mapping.source_path}.repository"
            tag_path = f"{mapping.source_path}.tag"

            repository = self.get_nested_value(values, repo_path)
            tag = self.get_nested_value(values, tag_path)

            if repository and tag:
                extracted_images[mapping.source_path] = {
                    'repository': repository,
                    'tag': tag
                }
                logger.debug(f"Extracted {mapping.source_path}: {repository}:{tag}")
            else:
                logger.warning(f"Could not extract image for {mapping.source_path}")

        return extracted_images

    def transform_registry_path(self, repository: str, transform: Optional[str]) -> str:
        """
        Transform a registry path according to the specified transformation.

        Args:
            repository: Original repository path
            transform: Transformation type ('suse_to_upstream', 'upstream_to_suse', etc.)

        Returns:
            Transformed repository path
        """
        if not transform:
            return repository

        if transform == 'suse_to_upstream':
            # Transform SUSE registry paths to upstream equivalents
            if 'dp.apps.rancher.io/containers/' in repository:
                # Extract the image name from SUSE path
                image_name = repository.split('/')[-1]

                # Map common SUSE images to upstream equivalents
                upstream_mappings = {
                    'ollama': 'ollama/ollama',
                    'open-webui': 'ghcr.io/open-webui/open-webui',
                    'open-webui-pipelines': 'ghcr.io/open-webui/pipelines'
                }

                return upstream_mappings.get(image_name, repository)

        elif transform == 'upstream_to_suse':
            # Transform upstream paths to SUSE registry equivalents
            suse_mappings = {
                'ollama/ollama': 'dp.apps.rancher.io/containers/ollama',
                'ghcr.io/open-webui/open-webui': 'dp.apps.rancher.io/containers/open-webui',
                'ghcr.io/open-webui/pipelines': 'dp.apps.rancher.io/containers/open-webui-pipelines'
            }

            return suse_mappings.get(repository, repository)

        return repository

    def update_target_chart(self, target_chart_path: str, extracted_images: Dict[str, Dict[str, str]],
                          image_mappings: List[ImageMapping]) -> Tuple[bool, List[str], Dict[str, str], Dict[str, str]]:
        """
        Update a target chart with new image versions.

        Args:
            target_chart_path: Path to the target chart
            extracted_images: Image versions extracted from source chart
            image_mappings: List of image mappings

        Returns:
            Tuple of (success, changes_made, old_versions, new_versions)
        """
        values_file = os.path.join(target_chart_path, "values.yaml")
        if not os.path.exists(values_file):
            return False, [f"values.yaml not found in {target_chart_path}"], {}, {}

        # Load current values
        with open(values_file, 'r') as f:
            current_values = yaml.safe_load(f)

        changes_made = []
        old_versions = {}
        new_versions = {}

        for mapping in image_mappings:
            if mapping.source_path not in extracted_images:
                continue

            source_image = extracted_images[mapping.source_path]
            new_repository = self.transform_registry_path(
                source_image['repository'],
                mapping.registry_transform
            )
            new_tag = source_image['tag']

            # Get current values
            current_repo = self.get_nested_value(current_values, f"{mapping.target_path}.repository")
            current_tag = self.get_nested_value(current_values, f"{mapping.target_path}.tag")

            # Store old versions
            if current_repo and current_tag:
                old_versions[mapping.target_path] = f"{current_repo}:{current_tag}"

            # Check if update is needed
            repo_changed = current_repo != new_repository
            tag_changed = current_tag != new_tag

            if repo_changed or tag_changed:
                # Update repository if needed
                if repo_changed:
                    self.set_nested_value(current_values, f"{mapping.target_path}.repository", new_repository)
                    changes_made.append(f"Updated {mapping.target_path}.repository: {current_repo} -> {new_repository}")

                # Update tag if needed
                if tag_changed:
                    self.set_nested_value(current_values, f"{mapping.target_path}.tag", new_tag)
                    changes_made.append(f"Updated {mapping.target_path}.tag: {current_tag} -> {new_tag}")

                new_versions[mapping.target_path] = f"{new_repository}:{new_tag}"
            else:
                logger.info(f"No update needed for {mapping.target_path}: {current_repo}:{current_tag}")

        # Write updated values if changes were made and not in dry-run mode
        if changes_made and not self.dry_run:
            # Create backup
            backup_file = f"{values_file}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            shutil.copy2(values_file, backup_file)
            logger.info(f"Created backup: {backup_file}")

            # Write updated values
            with open(values_file, 'w') as f:
                yaml.dump(current_values, f, default_flow_style=False, indent=2, sort_keys=False)

            logger.info(f"Updated {values_file}")

        return True, changes_made, old_versions, new_versions

    def sync_chart(self, chart_sync: ChartSync) -> List[SyncResult]:
        """
        Synchronize a single chart configuration.

        Args:
            chart_sync: Chart synchronization configuration

        Returns:
            List of sync results for each target chart
        """
        results = []

        try:
            # Pull the source chart
            chart_path = self.pull_chart(chart_sync.source_chart, chart_sync.name)

            # Extract image versions
            extracted_images = self.extract_image_versions(chart_path, chart_sync.image_mappings)

            if not extracted_images:
                error_msg = f"No images extracted from {chart_sync.name}"
                logger.error(error_msg)
                for target_chart in chart_sync.target_charts:
                    results.append(SyncResult(
                        chart_name=chart_sync.name,
                        target_chart=target_chart,
                        success=False,
                        changes_made=[],
                        errors=[error_msg],
                        old_versions={},
                        new_versions={}
                    ))
                return results

            # Update each target chart
            for target_chart in chart_sync.target_charts:
                logger.info(f"Updating target chart: {target_chart}")

                try:
                    success, changes, old_versions, new_versions = self.update_target_chart(
                        target_chart, extracted_images, chart_sync.image_mappings
                    )

                    results.append(SyncResult(
                        chart_name=chart_sync.name,
                        target_chart=target_chart,
                        success=success,
                        changes_made=changes,
                        errors=[],
                        old_versions=old_versions,
                        new_versions=new_versions
                    ))

                except Exception as e:
                    error_msg = f"Failed to update {target_chart}: {e}"
                    logger.error(error_msg)
                    results.append(SyncResult(
                        chart_name=chart_sync.name,
                        target_chart=target_chart,
                        success=False,
                        changes_made=[],
                        errors=[error_msg],
                        old_versions={},
                        new_versions={}
                    ))

        except Exception as e:
            error_msg = f"Failed to sync {chart_sync.name}: {e}"
            logger.error(error_msg)
            for target_chart in chart_sync.target_charts:
                results.append(SyncResult(
                    chart_name=chart_sync.name,
                    target_chart=target_chart,
                    success=False,
                    changes_made=[],
                    errors=[error_msg],
                    old_versions={},
                    new_versions={}
                ))

        return results

    def generate_summary_report(self) -> str:
        """
        Generate a comprehensive summary report of all synchronization operations.

        Returns:
            Formatted summary report as string
        """
        total_charts = len(self.results)
        successful_updates = sum(1 for r in self.results if r.success and r.changes_made)
        failed_updates = sum(1 for r in self.results if not r.success)
        no_changes = sum(1 for r in self.results if r.success and not r.changes_made)

        report = []
        report.append("=" * 80)
        report.append("SUSE Application Collection Synchronization Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        report.append("")

        # Summary statistics
        report.append("SUMMARY:")
        report.append(f"  Total charts processed: {total_charts}")
        report.append(f"  Successful updates: {successful_updates}")
        report.append(f"  No changes needed: {no_changes}")
        report.append(f"  Failed updates: {failed_updates}")
        report.append("")

        # Detailed results
        if self.results:
            report.append("DETAILED RESULTS:")
            report.append("-" * 50)

            for result in self.results:
                status = "✅ SUCCESS" if result.success else "❌ FAILED"
                report.append(f"\n{status} - {result.chart_name} -> {os.path.basename(result.target_chart)}")

                if result.changes_made:
                    report.append("  Changes made:")
                    for change in result.changes_made:
                        report.append(f"    • {change}")

                if result.errors:
                    report.append("  Errors:")
                    for error in result.errors:
                        report.append(f"    • {error}")

                if not result.changes_made and not result.errors and result.success:
                    report.append("  No changes needed - versions already up to date")

        # Version summary
        version_changes = {}
        for result in self.results:
            if result.success and result.new_versions:
                for path, version in result.new_versions.items():
                    if path not in version_changes:
                        version_changes[path] = set()
                    version_changes[path].add(version)

        if version_changes:
            report.append("")
            report.append("VERSION SUMMARY:")
            report.append("-" * 30)
            for path, versions in version_changes.items():
                report.append(f"  {path}: {', '.join(sorted(versions))}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def run(self) -> bool:
        """
        Run the complete synchronization process.

        Returns:
            True if all operations completed successfully, False otherwise
        """
        try:
            # Load configuration
            self.load_config()

            # Setup temporary directory
            self.setup_temp_directory()

            # Process each chart sync configuration
            for chart_config in self.config.get('chart_syncs', []):
                chart_sync = ChartSync(
                    name=chart_config['name'],
                    source_chart=chart_config['source_chart'],
                    target_charts=chart_config['target_charts'],
                    image_mappings=[
                        ImageMapping(**mapping) for mapping in chart_config['image_mappings']
                    ]
                )

                logger.info(f"Processing chart sync: {chart_sync.name}")
                results = self.sync_chart(chart_sync)
                self.results.extend(results)

            # Generate and display summary report
            summary = self.generate_summary_report()
            print(summary)

            # Write summary to file
            summary_file = f"sync-summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            with open(summary_file, 'w') as f:
                f.write(summary)
            logger.info(f"Summary report saved to: {summary_file}")

            # Return overall success status
            return all(result.success for result in self.results)

        except Exception as e:
            logger.error(f"Synchronization failed: {e}")
            return False

        finally:
            # Cleanup
            self.cleanup_temp_directory()

def main():
    """Main entry point for the synchronization agent."""
    parser = argparse.ArgumentParser(
        description="SUSE Application Collection Synchronization Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run synchronization with default config
  python suse-app-collection-sync.py

  # Dry run to see what would be changed
  python suse-app-collection-sync.py --dry-run

  # Use custom config file
  python suse-app-collection-sync.py --config custom-sync-config.yaml

  # Enable debug logging
  python suse-app-collection-sync.py --verbose
        """
    )

    parser.add_argument(
        '--config', '-c',
        default='suse-sync-config.yaml',
        help='Configuration file path (default: suse-sync-config.yaml)'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be changed without making any modifications'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file {args.config} not found.")
        print("Please create a configuration file or specify an existing one with --config")
        sys.exit(1)

    # Run synchronization
    sync_agent = SUSEAppCollectionSync(args.config, args.dry_run)
    success = sync_agent.run()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
