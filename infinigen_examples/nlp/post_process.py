# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Post-processing module for parsed LLM output."""

import logging
from typing import Any, Dict, List, Optional

from infinigen_examples.nlp import parse_natural_language

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Keyword-based fallback extraction helpers
# ──────────────────────────────────────────────


def fallback_extract_rooms(input_text: str) -> Optional[List[str]]:
    """Extract room types from input text using keyword matching.

    Used as a fallback when the LLM fails to populate restrict_parent_rooms.
    Scans the input text for known room keywords from tag_mapping.

    To avoid false positives, keywords that also map to an *object* type
    (e.g. "closet" can mean a piece of furniture OR a room) are skipped.

    Args:
        input_text: Original natural language input

    Returns:
        List of room type Semantics names, or None if nothing found
    """
    from infinigen_examples.nlp import tag_mapping

    # Build a set of keywords that are ambiguous (exist in BOTH room and object mappings)
    object_keywords = set(tag_mapping.OBJECT_MAPPINGS.keys())

    rooms: List[str] = []
    input_lower = input_text.lower()
    # Sort by length descending so longer matches ("living room") beat shorter ones ("room")
    for keyword, tag in sorted(
        tag_mapping.ROOM_MAPPINGS.items(), key=lambda x: -len(x[0])
    ):
        # Skip keywords that are also object names to avoid furniture → room confusion
        if keyword in object_keywords:
            continue
        if keyword in input_lower and tag.name not in rooms:
            rooms.append(tag.name)
    return rooms if rooms else None


def fallback_extract_stage_flags(input_text: str) -> Optional[Dict[str, bool]]:
    """Extract stage flags from input text using keyword matching.

    Used as a fallback when the LLM sets stage_exclusive / stage_types
    incorrectly.  Directly checks the raw text for "~에만" patterns.

    Args:
        input_text: Original natural language input

    Returns:
        Dict with solve_*_enabled flags, or None if no keywords found
    """
    text = input_text.lower()

    # "바닥과 벽에만" must be checked *before* "바닥에만"
    if "바닥과 벽에만" in text or "floor and wall only" in text:
        return {
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": False,
        }
    if "바닥에만" in text or "floor only" in text:
        return {
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": False,
        }
    if "벽에만" in text or "wall only" in text:
        return {
            "solve_large_enabled": False,
            "solve_medium_enabled": True,
            "solve_small_enabled": False,
        }
    if "위에만" in text or "on top only" in text:
        return {
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": True,
        }
    return None


def fill_defaults(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fill missing fields with default values.

    Args:
        parsed_data: Parsed data from LLM (may have missing fields)

    Returns:
        Parsed data with all fields filled

        None values from LLM are replaced with defaults for fields that have defaults.
        This ensures that fields with default values (like solve_max_rooms=1) are preserved
        even if LLM returns None, while explicitly None fields remain None.
    """
    defaults = parse_natural_language.get_default_parsed_data()

    # Start with defaults
    result = defaults.copy()

    # Merge parsed data with defaults, but only update non-None values
    # This preserves defaults for fields where LLM returned None
    for key, value in parsed_data.items():
        if value is not None:
            result[key] = value
        # If value is None and key exists in defaults, keep the default value
        # (This is already the case since we start with defaults.copy())

    # Clamp solve_max_rooms to at least 1 (validation will also enforce this)
    if result.get("solve_max_rooms") is not None and result["solve_max_rooms"] < 1:
        result["solve_max_rooms"] = 1

    return result


def normalize_room_names(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize room names to Semantics tag names.

    Args:
        parsed_data: Parsed data with potentially non-normalized room names

    Returns:
        Parsed data with normalized room names
    """
    from infinigen_examples.nlp import tag_mapping

    if parsed_data.get("restrict_parent_rooms"):
        normalized_rooms = []
        for room in parsed_data["restrict_parent_rooms"]:
            mapped = tag_mapping.map_room_name_to_tag(room)
            if mapped:
                normalized_rooms.append(mapped.name)
            else:
                # If mapping fails, try using the name as-is (might already be normalized)
                normalized_rooms.append(room)
        parsed_data["restrict_parent_rooms"] = normalized_rooms

    return parsed_data


def normalize_object_names(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize object names to Semantics tag names.

    Args:
        parsed_data: Parsed data with potentially non-normalized object names

    Returns:
        Parsed data with normalized object names
    """
    from infinigen_examples.nlp import tag_mapping

    for key in [
        "restrict_parent_objs",
        "restrict_child_primary",
        "restrict_child_secondary",
    ]:
        if parsed_data.get(key):
            normalized_objs = []
            for obj in parsed_data[key]:
                mapped = tag_mapping.map_object_name_to_tag(obj)
                if mapped:
                    normalized_objs.append(mapped.name)
                else:
                    # If mapping fails, try using the name as-is (might already be normalized)
                    normalized_objs.append(obj)
            parsed_data[key] = normalized_objs

    return parsed_data


def process_stage_types(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process detailed stage_types and convert to high-level stage flags if needed.

    stage_types is used in two modes:
    - Descriptive (stage_exclusive=false, default): The user described placement positions
      but did NOT restrict to those positions only. All stages remain enabled.
      Example: "책상 위에 마우스가 있게 해줘" → obj_ontop_obj mentioned, but all stages stay True.
    - Exclusive (stage_exclusive=true): The user explicitly used "only/만" semantics.
      Only stages with mentioned sub-types are enabled; others are disabled.
      Example: "바닥에만 배치해줘" → only large stage enabled.

    Args:
        parsed_data: Parsed data that may contain stage_types and stage_exclusive

    Returns:
        Parsed data with stage flags properly set
    """
    from infinigen_examples.nlp import tag_mapping

    stage_types = parsed_data.get("stage_types")
    stage_exclusive = parsed_data.get("stage_exclusive", False)

    if stage_types and isinstance(stage_types, dict):
        # Convert detailed stage types to high-level flags
        stage_flags = tag_mapping.stage_types_to_stage_flags(
            stage_types, exclusive=stage_exclusive
        )

        logger.info(
            f"stage_types={stage_types}, stage_exclusive={stage_exclusive} "
            f"-> stage_flags={stage_flags}"
        )

        # Only override solve_*_enabled when exclusive mode is active
        # In descriptive mode, stage_types is informational and doesn't touch flags
        if stage_exclusive:
            parsed_data["solve_large_enabled"] = stage_flags["solve_large_enabled"]
            parsed_data["solve_medium_enabled"] = stage_flags["solve_medium_enabled"]
            parsed_data["solve_small_enabled"] = stage_flags["solve_small_enabled"]

    # Remove stage_types/stage_exclusive from parsed_data — not used in config generation
    for key in ("stage_types", "stage_exclusive"):
        parsed_data.pop(key, None)

    # Enforce stage dependencies regardless of how flags were set:
    # - solve_small requires solve_large (objects placed on top need base objects on the floor)
    # - solve_medium with side_obj also needs solve_large, but we can't tell sub-types here,
    #   so we conservatively enforce: if small is on, large must be on.
    if parsed_data.get("solve_small_enabled") and not parsed_data.get(
        "solve_large_enabled"
    ):
        logger.info(
            "solve_small_enabled=True requires solve_large_enabled=True "
            "(base objects must be placed on the floor first). Auto-correcting."
        )
        parsed_data["solve_large_enabled"] = True

    return parsed_data


def fix_common_errors(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix common errors in LLM output.

    Args:
        parsed_data: Parsed data that may contain errors

    Returns:
        Corrected parsed data
    """
    # Ensure boolean fields are actually booleans
    bool_fields = [
        "solve_large_enabled",
        "solve_medium_enabled",
        "solve_small_enabled",
        "terrain_enabled",
        "topview",
        "animate_cameras_enabled",
        "floating_objs_enabled",
        "restrict_single_supported_roomtype",
    ]

    for field in bool_fields:
        value = parsed_data.get(field)
        if value is not None:
            if isinstance(value, str):
                # Convert string booleans
                parsed_data[field] = value.lower() in ("true", "1", "yes", "on")
            elif not isinstance(value, bool):
                # Convert other types to bool
                parsed_data[field] = bool(value)

    # Ensure integer fields are actually integers
    int_fields = ["solve_max_rooms", "solve_max_parent_obj"]
    for field in int_fields:
        value = parsed_data.get(field)
        if value is not None:
            try:
                parsed_data[field] = int(value)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert {field} to int: {value}")
                parsed_data[field] = None

    # Ensure solve_steps is a dict with integer values
    if parsed_data.get("solve_steps"):
        steps = parsed_data["solve_steps"]
        if isinstance(steps, dict):
            normalized_steps = {}
            for key in ["large", "medium", "small"]:
                value = steps.get(key)
                if value is not None:
                    try:
                        normalized_steps[key] = int(value)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Could not convert solve_steps.{key} to int: {value}"
                        )
            parsed_data["solve_steps"] = normalized_steps if normalized_steps else None
        else:
            parsed_data["solve_steps"] = None

    return parsed_data


def post_process_parsed_data(
    parsed_data: Dict[str, Any],
    input_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply all post-processing steps to parsed data.

    Args:
        parsed_data: Raw parsed data from LLM
        input_text: Original natural language input (used for fallback extraction)

    Returns:
        Post-processed parsed data ready for config generation
    """
    # Fill defaults
    processed = fill_defaults(parsed_data)

    # Process stage_types if present (convert to solve_*_enabled flags)
    processed = process_stage_types(processed)

    # Fix common errors
    processed = fix_common_errors(processed)

    # Normalize names
    processed = normalize_room_names(processed)
    processed = normalize_object_names(processed)

    # ── Keyword-based fallback when LLM missed rooms / stage flags ──
    if input_text:
        # Fallback 1: If LLM returned no rooms, try keyword extraction
        if not processed.get("restrict_parent_rooms"):
            fallback_rooms = fallback_extract_rooms(input_text)
            if fallback_rooms:
                logger.info(
                    f"LLM missed restrict_parent_rooms; "
                    f"fallback extracted: {fallback_rooms}"
                )
                processed["restrict_parent_rooms"] = fallback_rooms

        # Fallback 2: Override stage flags when input contains explicit "~에만"
        stage_override = fallback_extract_stage_flags(input_text)
        if stage_override:
            logger.info(f"Stage flag override from input keywords: {stage_override}")
            processed.update(stage_override)

    return processed
