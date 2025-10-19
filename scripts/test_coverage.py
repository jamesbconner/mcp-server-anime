#!/usr/bin/env python3
"""
Test coverage analysis and improvement script for MCP Server Anime.

This script helps identify areas with low test coverage and provides
suggestions for improving test coverage to reach 90%+.
"""

import subprocess
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse


def run_command(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False
        )
        return result
    except Exception as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        sys.exit(1)


def run_tests_with_coverage() -> Tuple[float, Dict[str, float]]:
    """Run tests with coverage and return overall coverage and per-file coverage."""
    print("🧪 Running tests with coverage analysis...")
    
    # Run pytest with coverage
    cmd = [
        "poetry", "run", "pytest",
        "-m", "not integration",
        "--cov=src/mcp_server_anime",
        "--cov-report=xml:coverage.xml",
        "--cov-report=json:coverage.json",
        "--cov-report=term-missing",
        "--quiet"
    ]
    
    result = run_command(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("❌ Tests failed. Please fix failing tests before analyzing coverage.")
        return 0.0, {}
    
    # Parse coverage results
    coverage_data = {}
    overall_coverage = 0.0
    
    # Try to read JSON coverage report
    coverage_json_path = Path("coverage.json")
    if coverage_json_path.exists():
        try:
            with open(coverage_json_path) as f:
                data = json.load(f)
                overall_coverage = data.get("totals", {}).get("percent_covered", 0.0)
                
                for filename, file_data in data.get("files", {}).items():
                    if "src/mcp_server_anime" in filename:
                        coverage_data[filename] = file_data.get("summary", {}).get("percent_covered", 0.0)
        except Exception as e:
            print(f"Warning: Could not parse coverage.json: {e}")
    
    # Fallback to XML if JSON parsing failed
    if not coverage_data:
        coverage_xml_path = Path("coverage.xml")
        if coverage_xml_path.exists():
            try:
                tree = ET.parse(coverage_xml_path)
                root = tree.getroot()
                
                # Get overall coverage
                overall_elem = root.find(".//coverage")
                if overall_elem is not None:
                    overall_coverage = float(overall_elem.get("line-rate", 0)) * 100
                
                # Get per-file coverage
                for class_elem in root.findall(".//class"):
                    filename = class_elem.get("filename", "")
                    if "src/mcp_server_anime" in filename:
                        line_rate = float(class_elem.get("line-rate", 0))
                        coverage_data[filename] = line_rate * 100
            except Exception as e:
                print(f"Warning: Could not parse coverage.xml: {e}")
    
    return overall_coverage, coverage_data


def analyze_coverage(coverage_data: Dict[str, float], target: float = 90.0) -> None:
    """Analyze coverage data and provide recommendations."""
    print(f"\n📊 Coverage Analysis (Target: {target}%)")
    print("=" * 60)
    
    if not coverage_data:
        print("❌ No coverage data available")
        return
    
    # Sort files by coverage (lowest first)
    sorted_files = sorted(coverage_data.items(), key=lambda x: x[1])
    
    low_coverage_files = [(f, c) for f, c in sorted_files if c < target]
    good_coverage_files = [(f, c) for f, c in sorted_files if c >= target]
    
    print(f"📈 Files with good coverage ({len(good_coverage_files)}):")
    for filename, coverage in good_coverage_files[-5:]:  # Show top 5
        short_name = Path(filename).name
        print(f"  ✅ {short_name:<30} {coverage:6.1f}%")
    
    if low_coverage_files:
        print(f"\n📉 Files needing attention ({len(low_coverage_files)}):")
        for filename, coverage in low_coverage_files:
            short_name = Path(filename).name
            gap = target - coverage
            print(f"  ⚠️  {short_name:<30} {coverage:6.1f}% (need +{gap:.1f}%)")
    
    print(f"\n💡 Recommendations:")
    if low_coverage_files:
        print("1. Focus on files with lowest coverage first")
        print("2. Add tests for uncovered lines (use --cov-report=html for details)")
        print("3. Consider adding edge case and error handling tests")
        print("4. Test async code paths and exception scenarios")
    else:
        print("🎉 All files meet the coverage target!")


def get_uncovered_lines() -> Dict[str, List[int]]:
    """Get uncovered lines from coverage report."""
    uncovered = {}
    
    # Run coverage report to get missing lines
    cmd = ["poetry", "run", "coverage", "report", "--show-missing"]
    result = run_command(cmd)
    
    if result.returncode == 0:
        lines = result.stdout.split('\n')
        for line in lines:
            if 'src/mcp_server_anime' in line and 'Missing' in line:
                parts = line.split()
                if len(parts) >= 4:
                    filename = parts[0]
                    missing_part = parts[-1] if parts[-1] != 'Missing' else parts[-2]
                    if missing_part and missing_part != '0':
                        # Parse missing lines (e.g., "45-47, 52, 55-60")
                        missing_lines = []
                        for part in missing_part.split(','):
                            part = part.strip()
                            if '-' in part:
                                start, end = map(int, part.split('-'))
                                missing_lines.extend(range(start, end + 1))
                            elif part.isdigit():
                                missing_lines.append(int(part))
                        uncovered[filename] = missing_lines
    
    return uncovered


def suggest_test_improvements(uncovered_lines: Dict[str, List[int]]) -> None:
    """Suggest specific test improvements based on uncovered lines."""
    if not uncovered_lines:
        return
    
    print(f"\n🔍 Specific Test Suggestions:")
    print("=" * 60)
    
    for filename, lines in uncovered_lines.items():
        short_name = Path(filename).name
        print(f"\n📁 {short_name}:")
        
        # Read the file to analyze uncovered lines
        try:
            file_path = Path(filename)
            if file_path.exists():
                with open(file_path) as f:
                    file_lines = f.readlines()
                
                for line_num in lines[:5]:  # Show first 5 uncovered lines
                    if line_num <= len(file_lines):
                        line_content = file_lines[line_num - 1].strip()
                        if line_content:
                            print(f"  Line {line_num:3d}: {line_content[:60]}...")
                            
                            # Provide suggestions based on line content
                            if 'raise' in line_content:
                                print(f"           💡 Add test for exception: {line_content}")
                            elif 'if' in line_content or 'elif' in line_content:
                                print(f"           💡 Add test for condition: {line_content}")
                            elif 'except' in line_content:
                                print(f"           💡 Add test for error handling: {line_content}")
                            elif 'async def' in line_content or 'def' in line_content:
                                print(f"           💡 Add test for function: {line_content}")
                
                if len(lines) > 5:
                    print(f"  ... and {len(lines) - 5} more lines")
        except Exception as e:
            print(f"  Could not analyze file: {e}")


def run_specific_test_commands() -> None:
    """Run specific test commands to help improve coverage."""
    print(f"\n🚀 Running Additional Test Commands:")
    print("=" * 60)
    
    commands = [
        {
            "name": "Unit tests only",
            "cmd": ["poetry", "run", "pytest", "-m", "unit", "-v"],
            "description": "Run only unit tests"
        },
        {
            "name": "Error handling tests",
            "cmd": ["poetry", "run", "pytest", "-k", "error", "-v"],
            "description": "Run tests focused on error handling"
        },
        {
            "name": "Validation tests",
            "cmd": ["poetry", "run", "pytest", "-k", "validation", "-v"],
            "description": "Run input validation tests"
        },
        {
            "name": "Cache tests",
            "cmd": ["poetry", "run", "pytest", "-k", "cache", "-v"],
            "description": "Run caching-related tests"
        }
    ]
    
    for test_config in commands:
        print(f"\n🧪 {test_config['name']}:")
        print(f"   {test_config['description']}")
        result = run_command(test_config['cmd'])
        if result.returncode == 0:
            print("   ✅ Passed")
        else:
            print("   ❌ Failed")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze and improve test coverage")
    parser.add_argument("--target", type=float, default=90.0, help="Target coverage percentage")
    parser.add_argument("--detailed", action="store_true", help="Show detailed analysis")
    parser.add_argument("--suggestions", action="store_true", help="Show test suggestions")
    parser.add_argument("--run-tests", action="store_true", help="Run additional test commands")
    
    args = parser.parse_args()
    
    print("🎯 MCP Server Anime - Test Coverage Analysis")
    print("=" * 60)
    
    # Run tests and get coverage
    overall_coverage, coverage_data = run_tests_with_coverage()
    
    print(f"\n📊 Overall Coverage: {overall_coverage:.1f}%")
    
    if overall_coverage >= args.target:
        print(f"🎉 Congratulations! Coverage target of {args.target}% achieved!")
    else:
        gap = args.target - overall_coverage
        print(f"⚠️  Need {gap:.1f}% more coverage to reach {args.target}% target")
    
    # Analyze coverage
    analyze_coverage(coverage_data, args.target)
    
    if args.detailed or overall_coverage < args.target:
        # Get uncovered lines
        uncovered_lines = get_uncovered_lines()
        
        if args.suggestions:
            suggest_test_improvements(uncovered_lines)
    
    if args.run_tests:
        run_specific_test_commands()
    
    # Final recommendations
    print(f"\n🎯 Next Steps:")
    if overall_coverage < args.target:
        print("1. Run: poetry run pytest --cov-report=html")
        print("2. Open: htmlcov/index.html in browser")
        print("3. Focus on red (uncovered) lines")
        print("4. Add tests for error conditions and edge cases")
        print("5. Re-run this script to track progress")
    else:
        print("1. Maintain current coverage level")
        print("2. Add tests for new features")
        print("3. Consider increasing target coverage")
    
    print(f"\n📝 Useful Commands:")
    print("  make coverage-html    # Generate HTML coverage report")
    print("  make test-unit        # Run unit tests only")
    print("  make quality          # Run all quality checks")
    
    return 0 if overall_coverage >= args.target else 1


if __name__ == "__main__":
    sys.exit(main())