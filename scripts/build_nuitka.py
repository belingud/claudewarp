#!/usr/bin/env python3
"""
Nuitka build script for ClaudeWarp

This script provides optimized Nuitka builds with intelligent dependency exclusion
and platform-specific optimizations.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List

# Add the scripts directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analyzers.validator import validate_nuitka_build
from config.nuitka_base import (
    BuildMode,
    NuitkaConfig,
    OptimizationLevel,
    OutputFormat,
    Platform,
)


def run_command(command: List[str], description: str) -> int:
    """Run a command and return the exit code"""
    print(f"🔧 {description}")
    print(f"Command: {' '.join(command)}")
    print("-" * 50)

    start_time = time.time()
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        elapsed = time.time() - start_time
        print(f"✅ {description} completed in {elapsed:.1f}s")
        return result.returncode
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"❌ {description} failed after {elapsed:.1f}s with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ {description} failed after {elapsed:.1f}s: {e}")
        return 1


def validate_environment() -> bool:
    """Validate that the build environment is ready"""
    print("🔍 Validating build environment...")

    # Check if we're in a virtual environment
    if not hasattr(sys, "real_prefix") and not (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print("⚠️  Warning: Not running in a virtual environment")
        print("   It's recommended to use: uv sync --group gui-build")

    # Check if Nuitka is available
    try:
        result = subprocess.run(
            ["python", "-m", "nuitka", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ Nuitka version: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Nuitka not found. Install with: uv add --dev nuitka")
        return False

    # Check entry point exists
    return True


def analyze_build_size(executable_path: Path) -> None:
    """Analyze and report build size information"""
    if not executable_path.exists():
        print("❌ Built executable not found for size analysis")
        return

    print("\n📊 Build Size Analysis")
    print("=" * 40)

    if executable_path.is_file():
        # Single file
        size_mb = executable_path.stat().st_size / (1024 * 1024)
        print(f"📦 Executable size: {size_mb:.1f} MB")
        print(f"📍 Location: {executable_path}")
    elif executable_path.is_dir():
        # Directory (like .app bundle)
        size_mb = sum(f.stat().st_size for f in executable_path.rglob("*") if f.is_file()) / (
            1024 * 1024
        )
        print(f"📦 Bundle size: {size_mb:.1f} MB")
        print(f"📍 Location: {executable_path}")

        # Show top-level contents
        print("\n📁 Bundle contents:")
        for item in sorted(executable_path.iterdir()):
            if item.is_dir():
                item_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file()) / (
                    1024 * 1024
                )
                print(f"  📁 {item.name}/: {item_size:.1f} MB")
            else:
                item_size = item.stat().st_size / (1024 * 1024)
                print(f"  📄 {item.name}: {item_size:.1f} MB")


def validate_build(executable_path: Path, config: NuitkaConfig) -> bool:
    """Validate that the built executable works correctly"""
    print(f"\n🧪 Validating build: {executable_path}")

    if not executable_path.exists():
        print("❌ Executable not found")
        return False

    # Platform-specific validation
    if config.target_platform == Platform.MACOS and config.output_format == OutputFormat.APP_BUNDLE:
        # For macOS app bundles, find the actual executable
        actual_executable = executable_path / "Contents" / "MacOS" / "ClaudeWarp"
        if not actual_executable.exists():
            print("❌ macOS app bundle structure invalid")
            return False
        print("✅ macOS app bundle structure valid")

    # TODO: Add runtime validation (requires careful handling)
    # For now, just check that the file exists and is executable
    try:
        if executable_path.is_file() and not executable_path.stat().st_mode & 0o111:
            print("⚠️  Warning: Executable may not have execute permissions")
        print("✅ Basic validation passed")
        return True
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def build_with_nuitka(config: NuitkaConfig) -> int:
    """Execute Nuitka build with the given configuration"""

    # Generate Nuitka command
    nuitka_args = ["uv", "run", "nuitka"] + config.to_command_args()

    print("\n🚀 Starting Nuitka build")
    print(f"Mode: {config.build_mode.value}")
    print(f"Platform: {config.target_platform.value}")
    print(f"Optimization: {config.optimization_level.value}")
    print(f"Output: {config.output_format.value}")
    print(f"Entry point: {config.entry_point}")

    # Clean previous builds
    if config.output_dir.exists():
        print(f"🧹 Cleaning previous build directory: {config.output_dir}")
        import shutil

        shutil.rmtree(config.output_dir)

    # Run the build
    exit_code = run_command(nuitka_args, "Nuitka compilation")

    if exit_code == 0:
        # Determine expected output path
        if (
            config.target_platform == Platform.MACOS
            and config.output_format == OutputFormat.APP_BUNDLE
        ):
            app_name = config.output_name or "ClaudeWarp"
            executable_path = config.output_dir / f"{app_name}.app"
        else:
            executable_name = config.output_name or config.entry_point.stem  # type: ignore
            executable_path = config.output_dir / executable_name

        # Analyze build results
        analyze_build_size(executable_path)

        # Validate build with comprehensive testing
        if validate_build(executable_path, config):
            # Run comprehensive validation
            print("\n🧪 Running comprehensive validation...")
            validation_report = validate_nuitka_build(
                executable_path,
                config.build_mode.value,
                expected_exclusions=list(config.exclusions),
            )

            if validation_report.overall_passed:
                print("\n🎉 Build completed successfully!")
                print(f"📦 Output: {executable_path}")

                # Usage instructions
                if (
                    config.target_platform == Platform.MACOS
                    and config.output_format == OutputFormat.APP_BUNDLE
                ):
                    print(f"🚀 Run with: open {executable_path}")
                else:
                    print(f"🚀 Run with: {executable_path}")
            else:
                print("\n⚠️  Build completed but comprehensive validation failed")
                validation_report.print_report()
                return 1
        else:
            print("\n⚠️  Build completed but basic validation failed")
            return 1

    return exit_code


def main():
    """Main build script entry point"""
    parser = argparse.ArgumentParser(
        description="ClaudeWarp Nuitka build script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["gui", "cli", "universal"],
        default="gui",
        help="Build mode (default: gui)",
    )

    parser.add_argument(
        "--optimization",
        choices=["dev", "prod"],
        default="prod",
        help="Optimization level (default: prod)",
    )

    parser.add_argument(
        "--output-format",
        choices=["onefile", "standalone", "app-bundle"],
        help="Output format (auto-detected if not specified)",
    )

    parser.add_argument("--output-name", help="Custom output filename")

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with verbose output"
    )

    parser.add_argument(
        "--skip-validation", action="store_true", help="Skip environment validation"
    )

    args = parser.parse_args()

    print("🏗️  ClaudeWarp Nuitka Build System")
    print("=" * 40)

    # Validate environment
    if not args.skip_validation and not validate_environment():
        return 1

    # Configure build
    build_mode = {
        "gui": BuildMode.GUI_ONLY,
        "cli": BuildMode.CLI_ONLY,
        "universal": BuildMode.UNIVERSAL,
    }[args.mode]

    optimization_level = {
        "dev": OptimizationLevel.DEVELOPMENT,
        "prod": OptimizationLevel.PRODUCTION,
    }[args.optimization]

    # Create configuration
    config = NuitkaConfig(build_mode=build_mode, optimization_level=optimization_level)

    # Override output format if specified
    if args.output_format:
        output_format_map = {
            "onefile": OutputFormat.ONEFILE,
            "standalone": OutputFormat.STANDALONE,
            "app-bundle": OutputFormat.APP_BUNDLE,
        }
        config.output_format = output_format_map[args.output_format]

    # Override output name if specified
    if args.output_name:
        config.output_name = args.output_name

    # Debug mode adjustments
    if args.debug:
        config.enable_optimizations = False
        config.optimization_level = OptimizationLevel.DEVELOPMENT

    # Execute build
    return build_with_nuitka(config)


if __name__ == "__main__":
    sys.exit(main())
