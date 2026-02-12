# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Gin config file generation from parsed constraints."""

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Mapping from Semantics tag names to relevant constraint graph filter keywords.
# These keywords match the keys used in home_furniture_constraints() in
# infinigen_examples/constraints/home.py (constraints["..."] and score_terms["..."]).
# When specific objects are requested, we include their related constraint filters
# so the solver has the right bounds to place those objects.
TAG_TO_CONSGRAPH_FILTERS = {
    # Bedroom objects
    "Bed": ["bedroom"],
    # Storage is used across many rooms
    "Storage": ["storage", "closets"],
    # Kitchen objects
    "KitchenCounter": ["kitchen_counter", "kitchen_island"],
    "Sink": ["kitchen_sink"],
    "KitchenAppliance": ["kitchen_appliance"],
    # Living room objects
    "Seating": ["sofa", "livingroom"],
    "LoungeSeating": ["sofa", "livingroom"],
    "Watchable": ["tv", "tvstand"],
    # Dining/office
    "Table": ["furniture"],
    "Desk": ["desk"],
    "Chair": ["furniture"],
    "SideTable": ["sidetable"],
    # Decorations and lighting
    "WallDecoration": ["wall_decoration"],
    "CeilingLight": ["ceiling_light"],
    "Lighting": ["lighting", "lamps"],
    # Items placed on surfaces
    "Dishware": ["kitchen_objects"],
    "Cookware": ["kitchen_objects"],
    "Utensils": ["kitchen_objects"],
    "OfficeShelfItem": ["bedroom", "closets"],
    "KitchenCounterItem": ["kitchen_objects"],
    "TableDisplayItem": ["sidetable_objects"],
    "BathroomItem": [],
    "FoodPantryItem": ["closet_kitchen"],
    "Furniture": ["furniture"],
}

# Room-type to constraint filter mapping
ROOM_TO_CONSGRAPH_FILTERS = {
    "Bedroom": ["bedroom"],
    "Kitchen": ["kitchen"],
    "LivingRoom": ["livingroom", "sofa", "tv"],
    "DiningRoom": ["furniture"],
    "Bathroom": [],
    "Office": ["desk"],
}

# Base filters always included for fundamental constraint satisfaction
BASE_CONSGRAPH_FILTERS = ["node", "furniture", "fullness"]


def auto_generate_consgraph_filters(parsed_data: Dict[str, Any]) -> list[str]:
    """Auto-generate consgraph_filters from object/room types in parsed_data.

    Following the pattern from HelloRoom.md, consgraph_filters are used alongside
    restrict_child_primary/secondary to tell the solver which constraints to keep.
    This ensures the solver has the right bounds to place the requested objects.
    """
    filters = set(BASE_CONSGRAPH_FILTERS)

    # Add filters from room types
    for room in parsed_data.get("restrict_parent_rooms") or []:
        for f in ROOM_TO_CONSGRAPH_FILTERS.get(room, []):
            filters.add(f)

    # Add filters from primary objects
    for obj in parsed_data.get("restrict_child_primary") or []:
        for f in TAG_TO_CONSGRAPH_FILTERS.get(obj, []):
            filters.add(f)

    # Add filters from secondary objects
    for obj in parsed_data.get("restrict_child_secondary") or []:
        for f in TAG_TO_CONSGRAPH_FILTERS.get(obj, []):
            filters.add(f)

    return sorted(filters)


def format_list_value(value: list) -> str:
    """Format a list value for gin config.

    Args:
        value: List of values

    Returns:
        Formatted string for gin config
    """
    if not value:
        return "[]"

    # Format as list with quoted strings
    formatted_items = [f"'{item}'" for item in value]
    return "[" + ", ".join(formatted_items) + "]"


def format_value(value: Any) -> str:
    """Format a value for gin config.

    Args:
        value: Value to format

    Returns:
        Formatted string for gin config
    """
    if value is None:
        return "None"
    elif isinstance(value, bool):
        return "True" if value else "False"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return f"'{value}'"
    elif isinstance(value, list):
        return format_list_value(value)
    elif isinstance(value, dict):
        # Format dict as Python dict literal
        items = []
        for k, v in value.items():
            items.append(f"'{k}': {format_value(v)}")
        return "{" + ", ".join(items) + "}"
    else:
        return str(value)


def generate_restrict_solving_config(parsed_data: Dict[str, Any]) -> list[str]:
    """Generate restrict_solving config lines.

    Following the HelloRoom.md pattern, when restrict_child_primary/secondary
    are specified, consgraph_filters are auto-generated to keep only the
    relevant constraints in the solver. This ensures the solver has proper
    bounds to place each requested object type.

    Args:
        parsed_data: Parsed constraint data

    Returns:
        List of gin config lines
    """
    lines = []

    if parsed_data.get("restrict_parent_rooms"):
        value = format_list_value(parsed_data["restrict_parent_rooms"])
        lines.append(f"restrict_solving.restrict_parent_rooms = {value}")

    if parsed_data.get("restrict_parent_objs"):
        value = format_list_value(parsed_data["restrict_parent_objs"])
        lines.append(f"restrict_solving.restrict_parent_objs = {value}")

    if parsed_data.get("restrict_child_primary"):
        value = format_list_value(parsed_data["restrict_child_primary"])
        lines.append(f"restrict_solving.restrict_child_primary = {value}")

    if parsed_data.get("restrict_child_secondary"):
        value = format_list_value(parsed_data["restrict_child_secondary"])
        lines.append(f"restrict_solving.restrict_child_secondary = {value}")

    if parsed_data.get("solve_max_rooms") is not None:
        lines.append(
            f"restrict_solving.solve_max_rooms = {parsed_data['solve_max_rooms']}"
        )

    if parsed_data.get("solve_max_parent_obj") is not None:
        lines.append(
            f"restrict_solving.solve_max_parent_obj = {parsed_data['solve_max_parent_obj']}"
        )

    # Auto-generate consgraph_filters when specific objects are requested
    # (following HelloRoom.md pattern: restrict_child + consgraph_filters together)
    consgraph_filters = parsed_data.get("consgraph_filters")
    if consgraph_filters is None and (
        parsed_data.get("restrict_child_primary")
        or parsed_data.get("restrict_child_secondary")
    ):
        consgraph_filters = auto_generate_consgraph_filters(parsed_data)
        logger.info(f"Auto-generated consgraph_filters: {consgraph_filters}")

    if consgraph_filters:
        value = format_list_value(consgraph_filters)
        lines.append(f"restrict_solving.consgraph_filters = {value}")

    return lines


def generate_compose_indoors_config(parsed_data: Dict[str, Any]) -> list[str]:
    """Generate compose_indoors config lines.

    Args:
        parsed_data: Parsed constraint data

    Returns:
        List of gin config lines
    """
    lines = []

    # Solve steps
    solve_steps = parsed_data.get("solve_steps")
    if solve_steps:
        if solve_steps.get("large") is not None:
            lines.append(f"compose_indoors.solve_steps_large = {solve_steps['large']}")
        if solve_steps.get("medium") is not None:
            lines.append(
                f"compose_indoors.solve_steps_medium = {solve_steps['medium']}"
            )
        if solve_steps.get("small") is not None:
            lines.append(f"compose_indoors.solve_steps_small = {solve_steps['small']}")

    # Stage enable/disable flags
    if "solve_large_enabled" in parsed_data:
        lines.append(
            f"compose_indoors.solve_large_enabled = {format_value(parsed_data['solve_large_enabled'])}"
        )

    if "solve_medium_enabled" in parsed_data:
        lines.append(
            f"compose_indoors.solve_medium_enabled = {format_value(parsed_data['solve_medium_enabled'])}"
        )

    if "solve_small_enabled" in parsed_data:
        lines.append(
            f"compose_indoors.solve_small_enabled = {format_value(parsed_data['solve_small_enabled'])}"
        )

    # Scene configuration
    if "terrain_enabled" in parsed_data:
        lines.append(
            f"compose_indoors.terrain_enabled = {format_value(parsed_data['terrain_enabled'])}"
        )

    if "topview" in parsed_data:
        lines.append(
            f"compose_indoors.topview = {format_value(parsed_data['topview'])}"
        )

    if "animate_cameras_enabled" in parsed_data:
        lines.append(
            f"compose_indoors.animate_cameras_enabled = {format_value(parsed_data['animate_cameras_enabled'])}"
        )

    if "floating_objs_enabled" in parsed_data:
        lines.append(
            f"compose_indoors.floating_objs_enabled = {format_value(parsed_data['floating_objs_enabled'])}"
        )

    if parsed_data.get("num_floating") is not None:
        lines.append(f"compose_indoors.num_floating = {parsed_data['num_floating']}")

    if "restrict_single_supported_roomtype" in parsed_data:
        lines.append(
            f"compose_indoors.restrict_single_supported_roomtype = {format_value(parsed_data['restrict_single_supported_roomtype'])}"
        )

    return lines


def generate_gin_config(
    parsed_data: Dict[str, Any],
    base_config: str = "infinigen_examples/configs_indoor/base_indoors.gin",
) -> str:
    """Generate gin config file content from parsed data.

    Args:
        parsed_data: Parsed constraint data
        base_config: Base config file to include

    Returns:
        Complete gin config file content as string
    """
    lines = []

    # Include base config
    lines.append(f"include '{base_config}'")
    lines.append("")

    # Generate restrict_solving config
    restrict_lines = generate_restrict_solving_config(parsed_data)
    if restrict_lines:
        lines.append("# restrict_solving parameters")
        lines.extend(restrict_lines)
        lines.append("")

    # Generate compose_indoors config
    compose_lines = generate_compose_indoors_config(parsed_data)
    if compose_lines:
        lines.append("# compose_indoors parameters")
        lines.extend(compose_lines)
        lines.append("")

    # If solve_max_rooms is set, add single-room optimizations
    if parsed_data.get("solve_max_rooms") is not None:
        lines.append("# Single-room configuration")
        lines.append("BlueprintSolidifier.enable_open = False")
        lines.append("")
        # Hide rooms that don't have furniture to show only the solved room
        lines.append("# Hide non-solved rooms for cleaner output")
        lines.append("compose_indoors.hide_other_rooms_enabled = True")
        lines.append("compose_indoors.invisible_room_ceilings_enabled = True")
        lines.append("")

    return "\n".join(lines)


def save_gin_config(
    config_content: str,
    output_path: Path,
) -> Path:
    """Save gin config content to file.

    Args:
        config_content: Gin config file content
        output_path: Path to save config file

    Returns:
        Path to saved config file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(config_content, encoding="utf-8")
    logger.info(f"Saved gin config to {output_path}")
    return output_path
