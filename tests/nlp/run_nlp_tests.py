# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Test runner for NLP parsing module."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add infinigen to path
infinigen_root = Path(__file__).parent.parent.parent
if str(infinigen_root) not in sys.path:
    sys.path.insert(0, str(infinigen_root))

from infinigen_examples.nlp import (  # noqa: E402
    parse_natural_language,
    post_process,
    validate_constraints,
)

# Import test modules
# Try absolute import first, then relative
try:
    from tests.nlp import test_cases, test_nlp_evaluation
except ImportError:
    try:
        # Relative import when run as script
        from . import test_cases, test_nlp_evaluation
    except ImportError:
        # Direct import when in same directory
        import test_cases
        import test_nlp_evaluation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_single_test(
    test_case: Dict[str, Any],
    use_openai: bool = False,
    use_local_llm: bool = True,
    ollama_model: str = "gemma3",
    ollama_base_url: str = "http://localhost:11434",
) -> Dict[str, Any]:
    """Run a single test case.

    Args:
        test_case: Test case definition
        use_openai: Whether to use OpenAI API
        use_local_llm: Whether to use local LLM
        ollama_model: Ollama model name
        ollama_base_url: Ollama server base URL

    Returns:
        Evaluation result dictionary
    """
    logger.info(f"Running test {test_case['id']}: {test_case['description']}")
    logger.info(f"Input: {test_case['input']}")

    try:
        # Step 1: Parse natural language
        parsed_data = parse_natural_language.parse_natural_language(
            test_case["input"],
            use_openai=use_openai,
            use_local_llm=use_local_llm,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
        )
        logger.debug(f"Parsed data: {parsed_data}")
    except Exception as e:
        logger.error(f"Failed to parse: {e}")
        parsed_data = parse_natural_language.get_default_parsed_data()

    # Step 2: Post-process (pass input_text for fallback extraction)
    post_processed = post_process.post_process_parsed_data(
        parsed_data.copy(), input_text=test_case["input"]
    )
    logger.debug(f"Post-processed: {post_processed}")

    # Step 3: Validate (pass in-place so reclassification updates post_processed)
    is_valid, warnings = validate_constraints.validate_constraints(post_processed)
    logger.debug(f"Validation: is_valid={is_valid}, warnings={warnings}")

    # Step 4: Evaluate
    evaluation = test_nlp_evaluation.evaluate_parsing_result(
        test_case,
        parsed_data,
        post_processed,
        warnings,
        is_valid,
    )
    # Include actual parsing results for inspection in saved JSON
    evaluation["actual_parsed"] = parsed_data
    evaluation["actual_post_processed"] = post_processed

    logger.info(
        f"Test {test_case['id']}: {'PASSED' if evaluation['passed'] else 'FAILED'}"
    )
    if evaluation["issues"]:
        for issue in evaluation["issues"]:
            logger.warning(f"  Issue: {issue}")

    return evaluation


def run_all_tests(
    use_openai: bool = False,
    use_local_llm: bool = True,
    ollama_model: str = "gemma3",
    ollama_base_url: str = "http://localhost:11434",
    test_ids: List[str] = None,
    categories: List[str] = None,
) -> List[Dict[str, Any]]:
    """Run all test cases.

    Args:
        use_openai: Whether to use OpenAI API
        use_local_llm: Whether to use local LLM
        ollama_model: Ollama model name
        ollama_base_url: Ollama server base URL
        test_ids: Optional list of test IDs to run (if None, run all)
        categories: Optional list of categories to run (if None, run all)

    Returns:
        List of evaluation result dictionaries
    """
    all_test_cases = test_cases.get_test_cases()

    # Filter test cases
    test_cases_to_run = []
    for case in all_test_cases:
        if test_ids and case["id"] not in test_ids:
            continue
        if categories and case["category"] not in categories:
            continue
        test_cases_to_run.append(case)

    logger.info(f"Running {len(test_cases_to_run)} test cases...")

    results = []
    for test_case in test_cases_to_run:
        try:
            result = run_single_test(
                test_case,
                use_openai=use_openai,
                use_local_llm=use_local_llm,
                ollama_model=ollama_model,
                ollama_base_url=ollama_base_url,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error running test {test_case['id']}: {e}")
            results.append(
                {
                    "test_id": test_case["id"],
                    "category": test_case["category"],
                    "description": test_case["description"],
                    "input": test_case["input"],
                    "passed": False,
                    "issues": [f"Test execution error: {str(e)}"],
                    "warnings": [],
                    "validation_passed": False,
                    "field_accuracy": {},
                    "reclassification_detected": False,
                    "stage_consistency": False,
                    "actual_parsed": None,
                    "actual_post_processed": None,
                }
            )

    return results


def generate_report(results: List[Dict[str, Any]], output_dir: Path) -> Path:
    """Generate test report.

    Args:
        results: List of evaluation results
        output_dir: Output directory for reports

    Returns:
        Path to generated report file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate statistics
    stats = test_nlp_evaluation.calculate_statistics(results)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON results
    json_path = output_dir / f"results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "statistics": stats,
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"Saved JSON results to {json_path}")

    # Generate markdown report
    report_path = output_dir / f"report_{timestamp}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# NLP Parsing Test Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total Tests**: {stats['total']}\n")
        f.write(f"- **Passed**: {stats['passed']}\n")
        f.write(f"- **Failed**: {stats['failed']}\n")
        f.write(f"- **Pass Rate**: {stats['pass_rate']:.1%}\n")
        f.write(
            f"- **Reclassification Detected**: {stats['reclassification_detected']} ({stats['reclassification_rate']:.1%})\n"
        )
        f.write(
            f"- **Stage Consistency**: {stats['stage_consistency']} ({stats['stage_consistency_rate']:.1%})\n\n"
        )

        # Category breakdown
        f.write("## Category Breakdown\n\n")
        f.write("| Category | Total | Passed | Failed | Pass Rate |\n")
        f.write("|----------|-------|--------|--------|-----------|\n")
        for category, cat_stats in sorted(stats["category_stats"].items()):
            pass_rate = (
                cat_stats["passed"] / cat_stats["total"]
                if cat_stats["total"] > 0
                else 0.0
            )
            f.write(
                f"| {category} | {cat_stats['total']} | {cat_stats['passed']} | {cat_stats['failed']} | {pass_rate:.1%} |\n"
            )
        f.write("\n")

        # Field accuracy
        f.write("## Field Accuracy\n\n")
        f.write("| Field | Accurate | Total | Accuracy Rate |\n")
        f.write("|-------|----------|-------|---------------|\n")
        for field, field_stats in sorted(stats["field_accuracy"].items()):
            accuracy_rate = (
                field_stats["accurate"] / field_stats["total"]
                if field_stats["total"] > 0
                else 0.0
            )
            f.write(
                f"| {field} | {field_stats['accurate']} | {field_stats['total']} | {accuracy_rate:.1%} |\n"
            )
        f.write("\n")

        # Failed tests
        failed_tests = [r for r in results if not r["passed"]]
        if failed_tests:
            f.write("## Failed Tests\n\n")
            for result in failed_tests:
                f.write(f"### {result['test_id']}: {result['description']}\n\n")
                f.write(f"**Input**: {result['input']}\n\n")
                f.write(f"**Category**: {result['category']}\n\n")
                if result["issues"]:
                    f.write("**Issues**:\n")
                    for issue in result["issues"]:
                        f.write(f"- {issue}\n")
                    f.write("\n")
                if result["warnings"]:
                    f.write("**Warnings**:\n")
                    for warning in result["warnings"]:
                        f.write(f"- {warning}\n")
                    f.write("\n")
                f.write("\n")

        # All test results
        f.write("## All Test Results\n\n")
        f.write("| ID | Category | Description | Passed | Issues |\n")
        f.write("|----|----------|-------------|--------|--------|\n")
        for result in results:
            issues_count = len(result.get("issues", []))
            passed_mark = "✓" if result["passed"] else "✗"
            f.write(
                f"| {result['test_id']} | {result['category']} | {result['description'][:50]} | {passed_mark} | {issues_count} |\n"
            )
        f.write("\n")

    logger.info(f"Generated report to {report_path}")
    return report_path


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Run NLP parsing tests")
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="Use OpenAI API instead of local LLM",
    )
    parser.add_argument(
        "--use-local-llm",
        action="store_true",
        default=True,
        help="Use local LLM (default: True)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="gemma3",
        help="Ollama model name (default: gemma3)",
    )
    parser.add_argument(
        "--ollama-base-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama server base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--test-ids",
        type=str,
        nargs="+",
        help="Specific test IDs to run (e.g., edge_001 edge_002)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        help="Specific categories to run",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/nlp/test_results",
        help="Output directory for test results (default: tests/nlp/test_results)",
    )

    args = parser.parse_args()

    # Run tests
    results = run_all_tests(
        use_openai=args.use_openai,
        use_local_llm=args.use_local_llm and not args.use_openai,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_base_url,
        test_ids=args.test_ids,
        categories=args.categories,
    )

    # Generate report
    output_dir = Path(args.output_dir)
    report_path = generate_report(results, output_dir)

    # Print summary
    stats = test_nlp_evaluation.calculate_statistics(results)
    print(f"\n{'=' * 60}")
    print("Test Summary")
    print(f"{'=' * 60}")
    print(f"Total: {stats['total']}")
    print(f"Passed: {stats['passed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Pass Rate: {stats['pass_rate']:.1%}")
    print(f"\nReport saved to: {report_path}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
