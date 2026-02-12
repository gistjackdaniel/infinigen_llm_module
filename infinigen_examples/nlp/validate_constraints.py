# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Validation module for parsed constraints."""

import logging
from typing import Any, Dict, List, Optional, Set

from infinigen_examples.nlp import tag_mapping

logger = logging.getLogger(__name__)

# Object classification rules based on home.py constraint relationships
# These define which objects should be in which category

# Primary objects: Objects placed directly in rooms (on floor, against wall, etc.)
PRIMARY_OBJECTS: Set[str] = {
    "Bed",
    "Storage",
    "Table",
    "Desk",
    "Seating",
    "LoungeSeating",
    "KitchenCounter",
    "KitchenAppliance",
    "Furniture",
    "WallDecoration",
    "CeilingLight",
    "Chair",
    "SideTable",
    # Note: TVStand is not a Semantics tag - TVStandFactory uses Storage tag
}

# Secondary objects: Objects placed on top of other objects
SECONDARY_OBJECTS: Set[str] = {
    "Sink",  # Placed on KitchenCounter
    "Dishware",
    "Cookware",
    "Utensils",
    "OfficeShelfItem",
    "KitchenCounterItem",
    "TableDisplayItem",
    "BathroomItem",
    "FoodPantryItem",
    "Lighting",  # Some lighting (lamps) placed on furniture
    "Watchable",  # TV, Monitor placed on Storage/TVStand (which uses Storage tag)
}

# Parent objects: Objects that can have other objects placed on them
PARENT_OBJECTS: Set[str] = {
    "KitchenCounter",
    "Storage",
    "Table",
    "Desk",
    "SideTable",
    "Bed",  # Some objects can be placed on beds
    # Note: TVStand is not a Semantics tag - TVStandFactory uses Storage tag
}

# Mapping from secondary objects to their typical parent objects.
# Used to auto-infer restrict_parent_objs and restrict_child_primary when
# the LLM provides secondary objects but forgets the parent.
SECONDARY_TO_PARENT: Dict[str, str] = {
    "Sink": "KitchenCounter",
    "Dishware": "Table",
    "Cookware": "KitchenCounter",
    "Utensils": "Table",
    "KitchenCounterItem": "KitchenCounter",
    "FoodPantryItem": "KitchenCounter",
    "TableDisplayItem": "Table",
    "OfficeShelfItem": "Storage",
    "BathroomItem": "Storage",
    "Lighting": "SideTable",
    "Watchable": "Storage",
    "ShelfTrinket": "Storage",
    "HandheldItem": "Desk",
}


def validate_room_types(room_types: Optional[List[str]]) -> tuple[List[str], List[str]]:
    """Validate room types against available Semantics tags.

    Args:
        room_types: List of room type names (strings)

    Returns:
        Tuple of (valid_room_types, invalid_room_types)
    """
    if room_types is None:
        return [], []

    valid = []
    invalid = []
    available_rooms = tag_mapping.get_all_room_types()
    available_room_names = {tag.name for tag in available_rooms}

    for room in room_types:
        # Try to map the room name
        mapped = tag_mapping.map_room_name_to_tag(room)
        if mapped is not None or room in available_room_names:
            valid.append(room)
        else:
            invalid.append(room)
            logger.warning(f"Unknown room type: {room}")

    return valid, invalid


def validate_object_types(
    object_types: Optional[List[str]],
) -> tuple[List[str], List[str]]:
    """Validate object types against available Semantics tags.

    Args:
        object_types: List of object type names (strings)

    Returns:
        Tuple of (valid_object_types, invalid_object_types)
    """
    if object_types is None:
        return [], []

    valid = []
    invalid = []
    available_objects = tag_mapping.get_all_object_types()
    available_object_names = {tag.name for tag in available_objects}

    for obj in object_types:
        # Try to map the object name
        mapped = tag_mapping.map_object_name_to_tag(obj)
        if mapped is not None or obj in available_object_names:
            valid.append(obj)
        else:
            invalid.append(obj)
            logger.warning(f"Unknown object type: {obj}")

    return valid, invalid


def validate_stage_flags(parsed_data: Dict[str, Any]) -> bool:
    """Validate that at least one stage is enabled.

    Args:
        parsed_data: Parsed constraint data

    Returns:
        True if valid, False if all stages are disabled
    """
    large_enabled = parsed_data.get("solve_large_enabled", True)
    medium_enabled = parsed_data.get("solve_medium_enabled", True)
    small_enabled = parsed_data.get("solve_small_enabled", True)

    if not (large_enabled or medium_enabled or small_enabled):
        logger.error("All stages are disabled. At least one stage must be enabled.")
        return False

    return True


def validate_quantity_limits(parsed_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate quantity limits and clamp invalid values.

    Args:
        parsed_data: Parsed constraint data (may be modified in place)

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings: List[str] = []
    is_valid = True

    max_rooms = parsed_data.get("solve_max_rooms")
    max_parent_obj = parsed_data.get("solve_max_parent_obj")

    if max_rooms is not None and max_rooms < 1:
        logger.warning(
            f"solve_max_rooms must be at least 1, got {max_rooms}. Setting to 1."
        )
        warnings.append("solve_max_rooms should be at least 1; was adjusted to 1.")
        parsed_data["solve_max_rooms"] = 1

    if max_parent_obj is not None and max_parent_obj < 0:
        logger.error(f"solve_max_parent_obj must be non-negative, got {max_parent_obj}")
        is_valid = False

    return is_valid, warnings


def validate_object_classification(
    parsed_data: Dict[str, Any],
) -> tuple[bool, List[str]]:
    """Validate and reclassify objects into correct categories.

    This function checks if objects are in the correct category based on their
    relationships defined in home.py constraints. Objects are automatically
    reclassified if they are in the wrong category.

    Args:
        parsed_data: Parsed constraint data that may contain misclassified objects

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    is_valid = True

    # Get current classifications
    restrict_parent_objs = parsed_data.get("restrict_parent_objs") or []
    restrict_child_primary = parsed_data.get("restrict_child_primary") or []
    restrict_child_secondary = parsed_data.get("restrict_child_secondary") or []

    # Track objects that need to be moved
    to_remove_from_parent = []
    to_remove_from_primary = []
    to_remove_from_secondary = []

    to_add_to_parent = []
    to_add_to_primary = []
    to_add_to_secondary = []

    # Check restrict_parent_objs
    for obj in restrict_parent_objs:
        obj_normalized = obj  # Already normalized in post_process
        if obj_normalized not in PARENT_OBJECTS:
            # This object shouldn't be a parent
            to_remove_from_parent.append(obj)
            # Check if it should be primary or secondary
            if obj_normalized in PRIMARY_OBJECTS:
                to_add_to_primary.append(obj)
                warnings.append(
                    f"Object '{obj}' was in restrict_parent_objs but should be in "
                    f"restrict_child_primary. Automatically reclassified."
                )
            elif obj_normalized in SECONDARY_OBJECTS:
                to_add_to_secondary.append(obj)
                warnings.append(
                    f"Object '{obj}' was in restrict_parent_objs but should be in "
                    f"restrict_child_secondary. Automatically reclassified."
                )

    # Check restrict_child_primary
    for obj in restrict_child_primary:
        obj_normalized = obj
        if obj_normalized in SECONDARY_OBJECTS:
            # This object should be secondary, not primary
            to_remove_from_primary.append(obj)
            to_add_to_secondary.append(obj)
            warnings.append(
                f"Object '{obj}' was in restrict_child_primary but should be in "
                f"restrict_child_secondary. Automatically reclassified."
            )
        elif (
            obj_normalized not in PRIMARY_OBJECTS
            and obj_normalized not in SECONDARY_OBJECTS
        ):
            # Unknown object, but if it's in PARENT_OBJECTS, it might be valid as primary
            # We'll keep it but warn
            if obj_normalized not in PARENT_OBJECTS:
                logger.debug(
                    f"Object '{obj}' in restrict_child_primary is not in known categories"
                )

    # Check restrict_child_secondary
    for obj in restrict_child_secondary:
        obj_normalized = obj
        if (
            obj_normalized in PRIMARY_OBJECTS
            and obj_normalized not in SECONDARY_OBJECTS
        ):
            # This object should be primary, not secondary
            to_remove_from_secondary.append(obj)
            to_add_to_primary.append(obj)
            warnings.append(
                f"Object '{obj}' was in restrict_child_secondary but should be in "
                f"restrict_child_primary. Automatically reclassified."
            )
        elif (
            obj_normalized not in SECONDARY_OBJECTS
            and obj_normalized not in PRIMARY_OBJECTS
        ):
            # Unknown object, keep it but warn
            logger.debug(
                f"Object '{obj}' in restrict_child_secondary is not in known categories"
            )

    # Apply reclassifications
    if to_remove_from_parent:
        restrict_parent_objs = [
            obj for obj in restrict_parent_objs if obj not in to_remove_from_parent
        ]
    if to_remove_from_primary:
        restrict_child_primary = [
            obj for obj in restrict_child_primary if obj not in to_remove_from_primary
        ]
    if to_remove_from_secondary:
        restrict_child_secondary = [
            obj
            for obj in restrict_child_secondary
            if obj not in to_remove_from_secondary
        ]

    # Add objects to correct categories (avoid duplicates)
    for obj in to_add_to_parent:
        if obj not in restrict_parent_objs:
            restrict_parent_objs.append(obj)
    for obj in to_add_to_primary:
        if obj not in restrict_child_primary:
            restrict_child_primary.append(obj)
    for obj in to_add_to_secondary:
        if obj not in restrict_child_secondary:
            restrict_child_secondary.append(obj)

    # Auto-infer parent objects from secondary objects when LLM omitted them
    for obj in restrict_child_secondary:
        parent = SECONDARY_TO_PARENT.get(obj)
        if parent:
            if parent not in restrict_parent_objs:
                restrict_parent_objs.append(parent)
                warnings.append(
                    f"Auto-inferred parent '{parent}' for secondary object '{obj}'."
                )
            # Parent must also appear in restrict_child_primary (it is placed in the room)
            if parent not in restrict_child_primary:
                restrict_child_primary.append(parent)

    # Update parsed_data
    parsed_data["restrict_parent_objs"] = (
        restrict_parent_objs if restrict_parent_objs else None
    )
    parsed_data["restrict_child_primary"] = (
        restrict_child_primary if restrict_child_primary else None
    )
    parsed_data["restrict_child_secondary"] = (
        restrict_child_secondary if restrict_child_secondary else None
    )

    # Ensure solve_small_enabled is True when there are secondary objects
    if restrict_child_secondary and not parsed_data.get("solve_small_enabled", True):
        parsed_data["solve_small_enabled"] = True
        warnings.append(
            "restrict_child_secondary has objects; auto-enabled solve_small_enabled."
        )

    if warnings:
        is_valid = True  # Reclassification is a correction, not an error

    return is_valid, warnings


def validate_constraints(parsed_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate all constraints in parsed data.

    Args:
        parsed_data: Parsed constraint data from LLM

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    is_valid = True

    # Validate room types
    restrict_parent_rooms = parsed_data.get("restrict_parent_rooms")
    if restrict_parent_rooms:
        valid_rooms, invalid_rooms = validate_room_types(restrict_parent_rooms)
        if invalid_rooms:
            warnings.append(f"Invalid room types (will be ignored): {invalid_rooms}")
            # Update parsed_data to only include valid rooms
            parsed_data["restrict_parent_rooms"] = valid_rooms if valid_rooms else None

    # Validate object types (check if they exist)
    for key in [
        "restrict_parent_objs",
        "restrict_child_primary",
        "restrict_child_secondary",
    ]:
        obj_types = parsed_data.get(key)
        if obj_types:
            valid_objs, invalid_objs = validate_object_types(obj_types)
            if invalid_objs:
                warnings.append(
                    f"Invalid object types in {key} (will be ignored): {invalid_objs}"
                )
                # Update parsed_data to only include valid objects
                parsed_data[key] = valid_objs if valid_objs else None

    # Validate and reclassify object categories
    classification_valid, classification_warnings = validate_object_classification(
        parsed_data
    )
    warnings.extend(classification_warnings)
    if not classification_valid:
        is_valid = False

    # Validate stage flags
    if not validate_stage_flags(parsed_data):
        is_valid = False
        warnings.append("All stages are disabled. Enabling all stages by default.")
        parsed_data["solve_large_enabled"] = True
        parsed_data["solve_medium_enabled"] = True
        parsed_data["solve_small_enabled"] = True

    # Validate quantity limits (may clamp solve_max_rooms to 1 and add warnings)
    quantity_valid, quantity_warnings = validate_quantity_limits(parsed_data)
    warnings.extend(quantity_warnings)
    if not quantity_valid:
        is_valid = False

    return is_valid, warnings
