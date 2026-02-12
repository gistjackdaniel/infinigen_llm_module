# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Evaluation functions for NLP parsing test results."""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def compare_lists(
    actual: Optional[List], expected: Optional[List], field_name: str
) -> Tuple[bool, List[str]]:
    """Compare two lists (order-independent).

    Args:
        actual: Actual list value
        expected: Expected list value
        field_name: Name of the field being compared

    Returns:
        Tuple of (is_match, list_of_issues)
    """
    issues = []

    if actual is None and expected is None:
        return True, []

    if actual is None:
        issues.append(f"{field_name}: Expected {expected} but got None")
        return False, issues

    if expected is None:
        # If expected is None, actual can be None or empty list
        if not actual:
            return True, []
        issues.append(f"{field_name}: Expected None but got {actual}")
        return False, issues

    actual_set = set(actual) if actual else set()
    expected_set = set(expected) if expected else set()

    if actual_set == expected_set:
        return True, []

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    if missing:
        issues.append(f"{field_name}: Missing items {missing}")
    if extra:
        issues.append(f"{field_name}: Extra items {extra}")

    return False, issues


def compare_values(
    actual: Any, expected: Any, field_name: str
) -> Tuple[bool, List[str]]:
    """Compare two values.

    Args:
        actual: Actual value
        expected: Expected value
        field_name: Name of the field being compared

    Returns:
        Tuple of (is_match, list_of_issues)
    """
    issues = []

    if actual == expected:
        return True, []

    # Handle None cases
    if expected is None:
        # None is acceptable for most fields (means not specified)
        return True, []

    if actual is None and expected is not None:
        issues.append(f"{field_name}: Expected {expected} but got None")
        return False, issues

    issues.append(f"{field_name}: Expected {expected} but got {actual}")
    return False, issues


def evaluate_parsing_result(
    test_case: Dict[str, Any],
    actual_parsed: Dict[str, Any],
    actual_post_processed: Dict[str, Any],
    validation_warnings: List[str],
    validation_is_valid: bool,
) -> Dict[str, Any]:
    """Evaluate a single test case result.

    Args:
        test_case: Test case definition
        actual_parsed: Raw parsed data from LLM
        actual_post_processed: Post-processed parsed data
        validation_warnings: Warnings from validation
        validation_is_valid: Whether validation passed

    Returns:
        Evaluation result dictionary
    """
    result = {
        "test_id": test_case["id"],
        "category": test_case["category"],
        "description": test_case["description"],
        "input": test_case["input"],
        "passed": True,
        "issues": [],
        "warnings": validation_warnings,
        "validation_passed": validation_is_valid,
        "field_accuracy": {},
        "reclassification_detected": False,
        "stage_consistency": True,
    }

    # Check expected output if provided
    if "expected_output" in test_case:
        expected = test_case["expected_output"]
        field_issues = {}

        for field, expected_value in expected.items():
            actual_value = actual_post_processed.get(field)

            if isinstance(expected_value, list):
                is_match, issues = compare_lists(actual_value, expected_value, field)
            else:
                is_match, issues = compare_values(actual_value, expected_value, field)

            result["field_accuracy"][field] = is_match
            if not is_match:
                field_issues[field] = issues
                result["passed"] = False

        if field_issues:
            result["issues"].extend(
                [
                    f"{field}: {', '.join(issues)}"
                    for field, issues in field_issues.items()
                ]
            )

    # Check expected issues if provided
    if "expected_issues" in test_case:
        expected_issues = test_case["expected_issues"]
        found_issues = []

        for expected_issue in expected_issues:
            # Check if this issue is mentioned in warnings or actual issues
            issue_found = False
            for warning in validation_warnings:
                if expected_issue.lower() in warning.lower():
                    issue_found = True
                    found_issues.append(expected_issue)
                    break

            if not issue_found:
                for actual_issue in result["issues"]:
                    if expected_issue.lower() in actual_issue.lower():
                        issue_found = True
                        found_issues.append(expected_issue)
                        break

            if not issue_found:
                result["issues"].append(
                    f"Expected issue not detected: {expected_issue}"
                )
                result["passed"] = False

        if found_issues:
            result["issues"].append(
                f"Expected issues detected: {', '.join(found_issues)}"
            )

    # Check expected_after_fix if provided
    if "expected_after_fix" in test_case:
        expected_fixed = test_case["expected_after_fix"]
        for field, expected_value in expected_fixed.items():
            actual_value = actual_post_processed.get(field)

            if isinstance(expected_value, list):
                is_match, issues = compare_lists(actual_value, expected_value, field)
            else:
                is_match, issues = compare_values(actual_value, expected_value, field)

            if not is_match:
                result["issues"].append(f"After fix - {field}: {', '.join(issues)}")
                result["passed"] = False

    # Check for reclassification
    reclassification_keywords = [
        "reclassified",
        "automatically",
        "should be in",
        "was in",
    ]
    for warning in validation_warnings:
        for keyword in reclassification_keywords:
            if keyword.lower() in warning.lower():
                result["reclassification_detected"] = True
                break

    # Check stage consistency
    restrict_child_secondary = actual_post_processed.get("restrict_child_secondary")
    solve_small_enabled = actual_post_processed.get("solve_small_enabled", True)

    if restrict_child_secondary and not solve_small_enabled:
        result["stage_consistency"] = False
        result["issues"].append(
            "Stage inconsistency: restrict_child_secondary has objects but solve_small_enabled=False"
        )
        result["passed"] = False

    restrict_child_primary = actual_post_processed.get("restrict_child_primary")
    solve_large_enabled = actual_post_processed.get("solve_large_enabled", True)
    solve_medium_enabled = actual_post_processed.get("solve_medium_enabled", True)

    if restrict_child_primary and not (solve_large_enabled or solve_medium_enabled):
        result["stage_consistency"] = False
        result["issues"].append(
            "Stage inconsistency: restrict_child_primary has objects but both solve_large_enabled and solve_medium_enabled are False"
        )
        result["passed"] = False

    return result


def calculate_statistics(evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics from evaluation results.

    Args:
        evaluation_results: List of evaluation result dictionaries

    Returns:
        Statistics dictionary
    """
    total = len(evaluation_results)
    passed = sum(1 for r in evaluation_results if r["passed"])
    failed = total - passed

    # Category breakdown
    category_stats = {}
    for result in evaluation_results:
        category = result["category"]
        if category not in category_stats:
            category_stats[category] = {"total": 0, "passed": 0, "failed": 0}
        category_stats[category]["total"] += 1
        if result["passed"]:
            category_stats[category]["passed"] += 1
        else:
            category_stats[category]["failed"] += 1

    # Reclassification stats
    reclassification_count = sum(
        1 for r in evaluation_results if r["reclassification_detected"]
    )

    # Stage consistency stats
    consistent_count = sum(1 for r in evaluation_results if r["stage_consistency"])

    # Field accuracy
    field_accuracy = {}
    for result in evaluation_results:
        for field, is_accurate in result.get("field_accuracy", {}).items():
            if field not in field_accuracy:
                field_accuracy[field] = {"total": 0, "accurate": 0}
            field_accuracy[field]["total"] += 1
            if is_accurate:
                field_accuracy[field]["accurate"] += 1

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total > 0 else 0.0,
        "category_stats": category_stats,
        "reclassification_detected": reclassification_count,
        "reclassification_rate": reclassification_count / total if total > 0 else 0.0,
        "stage_consistency": consistent_count,
        "stage_consistency_rate": consistent_count / total if total > 0 else 0.0,
        "field_accuracy": field_accuracy,
    }
