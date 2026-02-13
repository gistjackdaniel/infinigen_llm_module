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
#
# consgraph_filters uses SUBSTRING MATCH:  any(fi in key for fi in filters)
# e.g. "kitchen" matches "kitchen_counters", "kitchen_sink", "kitchen_appliance", etc.
#      "dining_chair" matches "dining_chairs"
#      "sofa" matches "sofa", "sofa_positioning"
#
# When specific objects are requested, we include their related constraint filters
# so the solver has the right bounds to place those objects.
#
# All constraint/score_term keys in home.py (for reference):
#   node_gen, node, room,
#   furniture_fullness, obj_in_obj_fullness, obj_ontop_storage_fullness,
#   obj_ontop_nonstorage_fullness, furniture_aesthetics,
#   storage, portal_accessibility,
#   rugs, wall_decorations, floor_covering,
#   plants,
#   desk,
#   lighting, ceiling_lights, lamps,
#   sidetable_objects, sidetable,
#   closets,
#   bedroom,
#   kitchen_counters, kitchen_barchairs, kitchen_island_placement,
#   kitchen_sink, kitchen_appliance, kitchen_objects, closet_kitchen,
#   sofa, sofa_positioning, tv, tvstand, livingroom, livingroom_objects,
#   dining_chairs, dining_table_objects, diningroom,
#   bathroom, toilet, bathtub,
#   aquarium_tank, birthday_balloons, cocktail_tables
TAG_TO_CONSGRAPH_FILTERS = {
    # ── Primary furniture / large objects ────────────────────────────
    # Bed bounds are in constraints["bedroom"] → comes from ROOM mapping.
    "Bed": [],
    # Storage: constraints["storage"] → storage_freestanding count/accessibility
    "Storage": ["storage"],
    # Furniture (generic): already in BASE_CONSGRAPH_FILTERS ("furniture")
    "Furniture": [],
    # ── Kitchen objects ─────────────────────────────────────────────
    # KitchenCounter: constraints["kitchen_counters"], ["kitchen_island_placement"]
    "KitchenCounter": ["kitchen_counter", "kitchen_island"],
    # Sink: constraints["kitchen_sink"] (bathroom sink is in Room→"bathroom")
    "Sink": ["kitchen_sink"],
    # KitchenAppliance: constraints["kitchen_appliance"]
    "KitchenAppliance": ["kitchen_appliance"],
    # ── Seating ─────────────────────────────────────────────────────
    # Seating (generic): sofa + dining chair + office chair constraints
    "Seating": ["sofa", "dining_chair"],
    # LoungeSeating/Sofa: constraints["sofa"], ["sofa_positioning"]
    "LoungeSeating": ["sofa"],
    # Chair: constraints["dining_chairs"], also in ["desk"] (OfficeChairFactory)
    "Chair": ["dining_chair", "desk"],
    # ── Tables ──────────────────────────────────────────────────────
    # Table: constraints["dining_chairs"] (dining table bounds),
    #        constraints["dining_table_objects"] (items on table)
    "Table": ["dining_chair", "dining_table"],
    # Desk: constraints["desk"] → desk + office chair + monitor
    "Desk": ["desk"],
    # SideTable: score_terms["sidetable"], constraints["sidetable_objects"]
    "SideTable": ["sidetable"],
    # ── Media ───────────────────────────────────────────────────────
    # Watchable/TV: constraints["tv"], score_terms["tvstand"]
    "Watchable": ["tv", "tvstand"],
    # ── Decorations & floor ─────────────────────────────────────────
    # WallDecoration: constraints["wall_decorations"]
    "WallDecoration": ["wall_decoration"],
    # FloorMat/Rug: constraints["rugs"], score_terms["floor_covering"]
    "FloorMat": ["rugs", "floor_covering"],
    # ── Lighting ────────────────────────────────────────────────────
    # CeilingLight: constraints["ceiling_lights"]
    "CeilingLight": ["ceiling_light"],
    # Lighting (generic): constraints["lighting"], ["lamps"], ["ceiling_lights"]
    "Lighting": ["lighting", "lamps", "ceiling_light"],
    # ── Items placed on surfaces ────────────────────────────────────
    # Dishware: constraints["kitchen_objects"], ["dining_table_objects"]
    "Dishware": ["kitchen_objects", "dining_table"],
    # Cookware: constraints["kitchen_objects"]
    "Cookware": ["kitchen_objects"],
    # Utensils: constraints["dining_table_objects"]
    "Utensils": ["dining_table"],
    # OfficeShelfItem: constraints["desk"], ["sidetable_objects"]
    #   (room-scoped appearances come from ROOM mapping)
    "OfficeShelfItem": ["desk", "sidetable"],
    # KitchenCounterItem: constraints["kitchen_objects"]
    "KitchenCounterItem": ["kitchen_objects"],
    # TableDisplayItem: constraints["kitchen_objects"], ["dining_table_objects"],
    #   ["sidetable_objects"]
    "TableDisplayItem": ["kitchen_objects", "dining_table", "sidetable"],
    # BathroomItem: bounds are in constraints["bathroom"] → comes from ROOM mapping
    "BathroomItem": [],
    # FoodPantryItem: constraints["kitchen_objects"], ["closet_kitchen"]
    "FoodPantryItem": ["kitchen_objects", "closet_kitchen"],
    # ShelfTrinket: no dedicated constraint key; general obj_on_support
    "ShelfTrinket": [],
    # ClothDrapeItem: no dedicated constraint key
    "ClothDrapeItem": [],
    # HandheldItem: no dedicated constraint key
    "HandheldItem": [],
    # ── Bathroom objects ────────────────────────────────────────────
    # Bathing/Bathtub: constraints["bathtub"]
    "Bathing": ["bathtub"],
    # ── Plants ──────────────────────────────────────────────────────
    "Plants": ["plants"],
}

# Room-type to constraint filter mapping.
# Maps rooms ONLY to room-level constraint bundle keys.
# Object-specific keys (sofa, tv, desk, etc.) come from TAG_TO_CONSGRAPH_FILTERS.
# auto_generate_consgraph_filters() combines both.
ROOM_TO_CONSGRAPH_FILTERS = {
    "Bedroom": ["bedroom"],
    "Kitchen": ["kitchen"],
    "LivingRoom": ["livingroom"],
    "DiningRoom": ["diningroom"],
    "Bathroom": ["bathroom"],
    "Closet": ["closet"],
    "Office": [],
    "Hallway": [],
    "Garage": [],
    "Balcony": [],
    "Utility": [],
    "StaircaseRoom": [],
    "MeetingRoom": [],
    "BreakRoom": [],
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
