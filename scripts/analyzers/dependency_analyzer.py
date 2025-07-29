"""
Dependency analyzer for smart exclusion generation

This module analyzes Python imports and dependencies to generate optimal
exclusion lists for Nuitka builds.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class ImportInfo:
    """Information about an import statement"""

    module_name: str
    import_type: str  # "import", "from", "relative"
    source_file: Path
    line_number: int
    is_conditional: bool = False  # Inside if/try block
    is_optional: bool = False  # Has try/except around import


@dataclass
class DependencyGraph:
    """Analysis results for project dependencies"""

    direct_imports: Set[str] = field(default_factory=set)
    conditional_imports: Set[str] = field(default_factory=set)
    optional_imports: Set[str] = field(default_factory=set)
    unused_imports: Set[str] = field(default_factory=set)
    size_estimates: Dict[str, int] = field(default_factory=dict)
    import_locations: Dict[str, List[ImportInfo]] = field(default_factory=dict)

    def get_safe_exclusions(self) -> Set[str]:
        """Get modules that can be safely excluded"""
        # Start with unused imports
        safe = self.unused_imports.copy()

        # Add optional imports (but be cautious)
        safe.update(self.optional_imports)

        return safe

    def get_conditional_exclusions(self) -> Set[str]:
        """Get conditionally imported modules that might be excludable"""
        return self.conditional_imports


class ImportAnalyzer:
    """Analyzes Python imports to generate dependency information"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.python_files: List[Path] = []
        self.imports: List[ImportInfo] = []

    def discover_python_files(self, include_tests: bool = False) -> List[Path]:
        """Discover all Python files in the project"""
        patterns = ["**/*.py"]
        files = []

        for pattern in patterns:
            files.extend(self.project_root.glob(pattern))

        # Filter out unwanted files
        filtered_files = []
        for file_path in files:
            path_str = str(file_path)

            # Skip test files unless explicitly included
            if not include_tests and ("test_" in path_str or "/tests/" in path_str):
                continue

            # Skip build artifacts
            if any(skip in path_str for skip in ["build/", "dist/", ".git/", "__pycache__/"]):
                continue

            filtered_files.append(file_path)

        self.python_files = filtered_files
        return filtered_files

    def parse_imports_from_file(self, file_path: Path) -> List[ImportInfo]:
        """Parse imports from a single Python file"""
        imports = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                import_info = None

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = ImportInfo(
                            module_name=alias.name,
                            import_type="import",
                            source_file=file_path,
                            line_number=node.lineno,
                        )
                        imports.append(import_info)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:  # Avoid relative imports without module
                        import_info = ImportInfo(
                            module_name=node.module,
                            import_type="from",
                            source_file=file_path,
                            line_number=node.lineno,
                        )
                        imports.append(import_info)

                # Detect conditional imports (inside if/try blocks)
                if import_info:
                    import_info.is_conditional = self._is_conditional_import(node, tree)
                    import_info.is_optional = self._is_optional_import(node, tree)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"⚠️  Warning: Could not parse {file_path}: {e}")

        return imports

    def _is_conditional_import(self, node: ast.AST, tree: ast.AST) -> bool:
        """Check if import is inside a conditional block"""
        # This is a simplified check - in practice, you'd want more sophisticated analysis
        for parent in ast.walk(tree):
            if hasattr(parent, "body") and node in getattr(parent, "body", []):
                if isinstance(parent, (ast.If, ast.Try, ast.ExceptHandler)):
                    return True
        return False

    def _is_optional_import(self, node: ast.AST, tree: ast.AST) -> bool:
        """Check if import is in a try/except block"""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.Try) and node in getattr(parent, "body", []):
                return True
        return False

    def analyze_project(self, entry_points: List[Path] = None) -> DependencyGraph:
        """Analyze the entire project for dependencies"""
        # Discover files
        self.discover_python_files()

        # Parse all imports
        all_imports = []
        for file_path in self.python_files:
            file_imports = self.parse_imports_from_file(file_path)
            all_imports.extend(file_imports)

        self.imports = all_imports

        # Build dependency graph
        graph = DependencyGraph()

        # Categorize imports
        for import_info in all_imports:
            module = import_info.module_name.split(".")[0]  # Get top-level module

            if import_info.is_optional:
                graph.optional_imports.add(module)
            elif import_info.is_conditional:
                graph.conditional_imports.add(module)
            else:
                graph.direct_imports.add(module)

            # Track import locations
            if module not in graph.import_locations:
                graph.import_locations[module] = []
            graph.import_locations[module].append(import_info)

        # Find unused imports by checking against entry points
        if entry_points:
            graph.unused_imports = self._find_unused_imports(entry_points, graph)

        # Estimate sizes (this would require actual measurement)
        graph.size_estimates = self._estimate_module_sizes(graph.direct_imports)

        return graph

    def _find_unused_imports(self, entry_points: List[Path], graph: DependencyGraph) -> Set[str]:
        """Find imports that are not used by any entry point"""
        # This is a simplified implementation
        # In practice, you'd want to do runtime analysis or more sophisticated static analysis

        unused = set()

        # Get imports from entry points
        entry_imports = set()
        for entry_point in entry_points:
            if entry_point.exists():
                imports = self.parse_imports_from_file(entry_point)
                entry_imports.update(imp.module_name.split(".")[0] for imp in imports)

        # Find modules imported elsewhere but not in entry points
        all_modules = graph.direct_imports | graph.conditional_imports | graph.optional_imports
        for module in all_modules:
            if module not in entry_imports:
                # Additional checks could go here
                unused.add(module)

        return unused

    def _estimate_module_sizes(self, modules: Set[str]) -> Dict[str, int]:
        """Estimate the size impact of modules"""
        # This is a placeholder - real implementation would measure actual import sizes
        size_estimates = {}

        # Common size estimates (in KB) - these are rough estimates
        known_sizes = {
            "numpy": 15000,
            "pandas": 25000,
            "matplotlib": 20000,
            "scipy": 30000,
            "torch": 800000,
            "tensorflow": 500000,
            "PIL": 3000,
            "requests": 1000,
            "urllib3": 500,
            "click": 500,
            "typer": 200,
            "rich": 1500,
            "pydantic": 2000,
            "PySide6": 50000,
            "qfluentwidgets": 5000,
        }

        for module in modules:
            size_estimates[module] = known_sizes.get(module, 100)  # Default 100KB

        return size_estimates

    def generate_exclusion_recommendations(
        self, graph: DependencyGraph, build_mode: str
    ) -> Dict[str, Set[str]]:
        """Generate exclusion recommendations based on analysis"""
        recommendations = {
            "safe_exclusions": set(),
            "conditional_exclusions": set(),
            "size_optimizations": set(),
            "manual_review": set(),
        }

        # Safe exclusions - unused or optional imports
        recommendations["safe_exclusions"] = graph.get_safe_exclusions()

        # Conditional exclusions - need manual review
        recommendations["conditional_exclusions"] = graph.get_conditional_exclusions()

        # Size-based recommendations - large modules that might not be needed
        large_modules = {
            module
            for module, size in graph.size_estimates.items()
            if size > 5000  # Modules larger than 5MB
        }
        recommendations["size_optimizations"] = large_modules

        # Build mode specific exclusions
        if build_mode == "gui_only":
            # CLI-related modules can be excluded
            cli_modules = {"typer", "click", "rich.prompt", "argparse"}
            recommendations["safe_exclusions"].update(
                cli_modules & (graph.direct_imports | graph.conditional_imports)
            )
        elif build_mode == "cli_only":
            # GUI-related modules can be excluded
            gui_modules = {"PySide6", "qfluentwidgets", "darkdetect"}
            recommendations["safe_exclusions"].update(
                gui_modules & (graph.direct_imports | graph.conditional_imports)
            )

        return recommendations

    def print_analysis_report(self, graph: DependencyGraph, recommendations: Dict[str, Set[str]]):
        """Print a detailed analysis report"""
        print("\n📊 Dependency Analysis Report")
        print("=" * 50)

        print("\n📦 Import Summary:")
        print(f"  Direct imports: {len(graph.direct_imports)}")
        print(f"  Conditional imports: {len(graph.conditional_imports)}")
        print(f"  Optional imports: {len(graph.optional_imports)}")
        print(f"  Unused imports: {len(graph.unused_imports)}")

        print("\n💾 Size Analysis:")
        total_size = sum(graph.size_estimates.values())
        print(f"  Total estimated size: {total_size / 1024:.1f} MB")

        # Show largest modules
        largest = sorted(graph.size_estimates.items(), key=lambda x: x[1], reverse=True)[:10]
        print("  Largest modules:")
        for module, size in largest:
            print(f"    {module}: {size / 1024:.1f} MB")

        print("\n🎯 Exclusion Recommendations:")
        for category, modules in recommendations.items():
            if modules:
                print(f"  {category.replace('_', ' ').title()}: {len(modules)} modules")
                for module in sorted(modules):
                    size = graph.size_estimates.get(module, 0)
                    print(f"    - {module} ({size / 1024:.1f} MB)")


def analyze_for_nuitka_build(
    project_root: Path, build_mode: str = "gui_only", entry_points: List[Path] = None
) -> Tuple[DependencyGraph, Dict[str, Set[str]]]:
    """Analyze project and generate Nuitka exclusion recommendations

    Args:
        project_root: Root directory of the project
        build_mode: Build mode ("gui_only", "cli_only", "universal")
        entry_points: List of entry point files to analyze

    Returns:
        Tuple of (dependency_graph, exclusion_recommendations)
    """
    analyzer = ImportAnalyzer(project_root)
    graph = analyzer.analyze_project(entry_points)
    recommendations = analyzer.generate_exclusion_recommendations(graph, build_mode)

    return graph, recommendations


if __name__ == "__main__":
    # Example usage
    project_root = Path(".")
    entry_points = [Path("main_gui.py"), Path("main_cli.py")]

    print("🔍 Analyzing project dependencies...")
    graph, recommendations = analyze_for_nuitka_build(project_root, "gui_only", entry_points)

    analyzer = ImportAnalyzer(project_root)
    analyzer.print_analysis_report(graph, recommendations)
