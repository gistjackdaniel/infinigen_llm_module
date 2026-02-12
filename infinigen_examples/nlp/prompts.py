# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Prompt templates for LLM-based natural language parsing."""

from __future__ import annotations

from infinigen.core import tags as t


def get_room_types_for_prompt() -> str:
    """Get formatted list of available room types for prompt.

    Returns:
        Comma-separated string of room type names
    """
    room_types = t.get_room_types()
    return ", ".join(rt.name for rt in room_types)


def get_object_types_for_prompt() -> str:
    """Get formatted list of available object types for prompt.

    Returns:
        Comma-separated string of object type names
    """
    object_types = t.get_object_types()
    return ", ".join(ot.name for ot in object_types)


PROMPT_TEMPLATE = """You are a natural language parser for indoor scene generation. 
Your task is to extract structured information from natural language descriptions 
that can be used to configure an indoor scene generator.

IMPORTANT: You MUST return ONLY valid JSON. Do not include any explanatory text, 
markdown formatting, or code blocks. Return the JSON object directly.

Extract ONLY information that can be controlled via gin config parameters. 
Do not extract information that cannot be controlled.

Available room types: {room_types}.

Available object types: {object_types}.

IMPORTANT - Object Classification Rules:
- restrict_parent_objs: Objects that can have other objects placed ON them (e.g., KitchenCounter, Storage, Table, Desk)
- restrict_child_primary: Objects placed directly IN rooms (on floor, against wall) (e.g., Bed, Storage, Table, Desk, KitchenCounter, Seating, KitchenAppliance)
- restrict_child_secondary: Objects that can be placed ON TOP OF other objects (e.g., Sink on KitchenCounter, Dishware on Table, Watchable on Storage)


Location relationships cannot be directly controlled, but can be indirectly controlled 
via stage flags. Each stage handles different object placement types:

STAGE DESCRIPTIONS:
The placement system uses 3 main stages, each containing specific sub-stages (total 8 placement types):

1. solve_large (large stage): Places objects on the floor
   - on_floor_and_wall: Objects touching both floor and wall (e.g., beds against wall, wall-mounted cabinets)
   - on_floor_freestanding: Objects on floor but not touching wall (e.g., center tables, freestanding beds)
  
2. solve_medium (medium stage): Places objects on walls/ceiling or beside other objects
   - on_wall: Objects attached to walls only (not touching floor or ceiling) (e.g., wall shelves, wall decorations)
   - on_ceiling: Objects attached to ceiling (e.g., ceiling lights)
   - side_obj: Objects placed beside other objects (not on top)
  
3. solve_small (small stage): Places objects on top of other objects
   - obj_ontop_obj: Objects placed on top of other objects (ontop relation) (e.g., dishes on table)
   - obj_on_support: Objects placed on support surfaces of other objects (on relation) (e.g., sink on counter)

STAGE DEPENDENCIES (IMPORTANT):
Stages have a dependency chain. Later stages need earlier stages to place base objects first:
- solve_small ALWAYS requires solve_large (objects on top need base objects on the floor first)
  e.g., "책상 위에만 물건을 배치해줘" → solve_large=True AND solve_small=True
  (the desk must be placed on the floor before anything can go on top of it)
- solve_medium's side_obj also requires solve_large (objects beside need base objects first)
- solve_large has no dependencies (it places objects directly on the floor)

STAGE FLAG MAPPING (High-level control):
- "floor only" or "on floor only" or "바닥에만" -> solve_large_enabled=True, solve_medium_enabled=False, solve_small_enabled=False
  (Only places objects directly on floor, not on walls/ceiling or on other objects)
- "floor and wall only" or "바닥과 벽에만" -> solve_large_enabled=True, solve_medium_enabled=True, solve_small_enabled=False
  (Floor and wall placement only; no objects on top of other objects)
  
- "wall only" or "ceiling only" -> solve_large_enabled=False, solve_medium_enabled=True, solve_small_enabled=False
  (Only places objects on walls/ceiling, not on floor or on top of objects)
  
- "on top only" or "on objects only" -> solve_large_enabled=True, solve_medium_enabled=False, solve_small_enabled=True
  (Places base objects on floor AND objects on top of them — large is always needed for small)

DETAILED STAGE TYPE KEYWORDS (for more precise control):
When users specify placement preferences, record the mentioned sub-stages in stage_types:

- "against wall", "wall-mounted", "touching wall" -> on_floor_and_wall
- "freestanding", "center", "middle of room", "not against wall" -> on_floor_freestanding
- "on wall", "wall decoration", "wall shelf" -> on_wall
- "ceiling", "hanging", "ceiling light" -> on_ceiling
- "beside", "next to", "side by side" -> side_obj
- "on top of", "ontop", "above" -> obj_ontop_obj
- "on support", "on surface", "on counter/table" -> obj_on_support

CRITICAL: stage_exclusive flag
- stage_exclusive = false (DEFAULT): The user merely described WHERE something is placed,
  NOT that placement should be restricted to ONLY that location.
  Example: "책상 위에 마우스가 있게 해줘" → stage_types.obj_ontop_obj=true, stage_exclusive=false
  Result: ALL stages remain enabled (solve_large/medium/small all True).
  
- stage_exclusive = true: The user explicitly said "only" / "만" / "~에만" to restrict placement.
  Example: "바닥에만 배치해줘" → stage_types.on_floor_and_wall=true, stage_types.on_floor_freestanding=true, stage_exclusive=true
  Result: ONLY the mentioned stages are enabled; others are disabled.

If stage_exclusive is false (or absent), solve_large_enabled / solve_medium_enabled / solve_small_enabled should ALL remain true.

Return a JSON object with the following structure (use null for missing values):
{{
    "restrict_parent_rooms": ["RoomType1"] or null,
    "restrict_parent_objs": ["ObjectType1"] or null,
    "restrict_child_primary": ["ObjectType1", "ObjectType2"] or null,
    "restrict_child_secondary": ["ObjectType1"] or null,
    "solve_max_rooms": 1 or null,  # Extract number from phrases like "1개 주방", "2개 방", "maximum 2 rooms", "1 room"
    "solve_max_parent_obj": 5 or null,
    "consgraph_filters": ["keyword1", "keyword2"] or null,
    "solve_steps": {{"large": 200, "medium": 100, "small": 30}} or null,
    "solve_large_enabled": true or false,
    "solve_medium_enabled": true or false,
    "solve_small_enabled": true or false,
    "stage_types": {{  # Optional: Records which placement sub-stages the user mentioned
        "on_floor_and_wall": true or null,  # Objects touching both floor and wall
        "on_floor_freestanding": true or null,  # Objects on floor but not touching wall
        "on_wall": true or null,  # Objects attached to walls only
        "on_ceiling": true or null,  # Objects attached to ceiling
        "side_obj": true or null,  # Objects placed beside other objects
        "obj_ontop_obj": true or null,  # Objects placed on top (ontop relation)
        "obj_on_support": true or null  # Objects placed on support surfaces (on relation)
    }} or null,  # Set mentioned sub-stages to true, leave unmentioned as null
    "stage_exclusive": false,  # IMPORTANT: true ONLY when user explicitly says "only/만/~에만"
    "terrain_enabled": false,
    "topview": false,
    "animate_cameras_enabled": false,
    "floating_objs_enabled": false,
    "restrict_single_supported_roomtype": false
}}

If a parameter is not mentioned in the input, set it to null (or default value for booleans).
Only extract information that is explicitly mentioned or can be inferred.

IMPORTANT: When extracting solve_max_rooms, look for number patterns:
- Korean: "1개 주방", "2개 방", "3개 방" -> extract the number (1, 2, 3)
- English: "1 room", "maximum 2 rooms", "at most 3 rooms" -> extract the number (1, 2, 3)
- If no number is mentioned, set to null (default value will be applied later)
- "0개 방" or "0 rooms" is invalid; use 1 (system will clamp to 1 if 0 is given)

Input: {input_text}

Return ONLY the JSON object, nothing else:"""


EXAMPLE_INPUTS_OUTPUTS = [
    # Example 1: Simple placement — no stage restriction
    {
        "input": "침실에 침대와 옷장을 배치한 씬을 1개 생성해줘.",
        "output": {
            "restrict_parent_rooms": ["Bedroom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Bed", "Storage"],
            "restrict_child_secondary": None,
            "solve_max_rooms": 1,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": None,
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 2: "바닥에만" = "only" → stage_exclusive=True, restricts to large stage
    {
        "input": "주방에 조리대와 싱크대만 배치하고, 바닥에만 배치해줘.",
        "output": {
            "restrict_parent_rooms": ["Kitchen"],
            "restrict_parent_objs": ["KitchenCounter"],
            "restrict_child_primary": ["KitchenCounter"],
            "restrict_child_secondary": ["Sink"],
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": False,
            "stage_types": {
                "on_floor_and_wall": True,
                "on_floor_freestanding": True,
            },
            "stage_exclusive": True,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 3: Simple description — no stage restriction
    {
        "input": "Create a scene with a dining table and chairs in the dining room. Maximum 2 rooms.",
        "output": {
            "restrict_parent_rooms": ["DiningRoom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Table", "Seating"],
            "restrict_child_secondary": None,
            "solve_max_rooms": 2,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": None,
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 4: "위에" = describes placement (NOT "only") → stage_exclusive=False, all stages True
    {
        "input": "1개 주방에 조리대를 배치하고 조리대 위에 음식을 배치해줘.",
        "output": {
            "restrict_parent_rooms": ["Kitchen"],
            "restrict_parent_objs": ["KitchenCounter"],
            "restrict_child_primary": ["KitchenCounter"],
            "restrict_child_secondary": ["FoodPantryItem"],
            "solve_max_rooms": 1,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": {
                "obj_ontop_obj": True,
            },
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 5: "위에만" = "only on top" → stage_exclusive=True
    # But solve_large must stay True (desk needs to be placed on floor first!)
    {
        "input": "책상 위에만 물건을 배치해줘.",
        "output": {
            "restrict_parent_rooms": None,
            "restrict_parent_objs": ["Desk"],
            "restrict_child_primary": None,
            "restrict_child_secondary": None,
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": True,
            "stage_types": {
                "obj_ontop_obj": True,
            },
            "stage_exclusive": True,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 6: "Put a mouse on the desk" — describes placement, NOT restriction → all stages True
    {
        "input": "책상 위에 마우스가 있게 해줘.",
        "output": {
            "restrict_parent_rooms": None,
            "restrict_parent_objs": ["Desk"],
            "restrict_child_primary": ["Desk"],
            "restrict_child_secondary": ["HandheldItem"],
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": {
                "obj_ontop_obj": True,
            },
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 7: "싱크대" in kitchen — Sink goes on KitchenCounter → restrict_child_secondary
    {
        "input": "주방에 싱크대를 배치해줘.",
        "output": {
            "restrict_parent_rooms": ["Kitchen"],
            "restrict_parent_objs": ["KitchenCounter"],
            "restrict_child_primary": ["KitchenCounter"],
            "restrict_child_secondary": ["Sink"],
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": None,
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 8: Negation — "침대만", "다른 가구는 없이" → Bedroom, Bed only
    {
        "input": "침실에 침대만 배치하고 다른 가구는 없이 해줘.",
        "output": {
            "restrict_parent_rooms": ["Bedroom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Bed"],
            "restrict_child_secondary": None,
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": None,
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 9: Real-world — "침대와 옷장이 있고, 창가에 책상" → include Desk
    {
        "input": "아늑한 침실을 만들어줘. 침대와 옷장이 있고, 창가에 책상이 있으면 좋겠어. 최대 2개 방으로 해줘.",
        "output": {
            "restrict_parent_rooms": ["Bedroom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Bed", "Storage", "Desk"],
            "restrict_child_secondary": None,
            "solve_max_rooms": 2,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": None,
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 10: "바닥과 벽에만" → solve_small_enabled=False
    {
        "input": "거실에 가구를 바닥과 벽에만 배치해줘.",
        "output": {
            "restrict_parent_rooms": ["LivingRoom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Furniture"],
            "restrict_child_secondary": None,
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": False,
            "stage_types": {
                "on_floor_and_wall": True,
                "on_floor_freestanding": True,
                "on_wall": True,
            },
            "stage_exclusive": True,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 11a: Ambiguous "가구" (furniture) → use Furniture tag when unspecified
    {
        "input": "침실에 적당히 가구를 배치해줘.",
        "output": {
            "restrict_parent_rooms": ["Bedroom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Furniture"],
            "restrict_child_secondary": None,
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
            "stage_types": None,
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 11b: Multiple rooms + "바닥에만" → solve_small_enabled=False
    {
        "input": "침실과 거실에 침대, 소파, 테이블을 배치하고, 최대 3개 방, 바닥에만 배치해줘.",
        "output": {
            "restrict_parent_rooms": ["Bedroom", "LivingRoom"],
            "restrict_parent_objs": None,
            "restrict_child_primary": ["Bed", "LoungeSeating", "Table"],
            "restrict_child_secondary": None,
            "solve_max_rooms": 3,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": False,
            "stage_types": {"on_floor_and_wall": True, "on_floor_freestanding": True},
            "stage_exclusive": True,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
    # Example 12: Floor + on table only (no wall) → solve_medium_enabled=False
    {
        "input": "거실에 소파를 바닥에 배치하고, 테이블 위에 그릇을 올려줘.",
        "output": {
            "restrict_parent_rooms": ["LivingRoom"],
            "restrict_parent_objs": ["Table"],
            "restrict_child_primary": ["LoungeSeating", "Table"],
            "restrict_child_secondary": ["Dishware"],
            "solve_max_rooms": None,
            "solve_max_parent_obj": None,
            "consgraph_filters": None,
            "solve_steps": None,
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": True,
            "stage_types": {
                "on_floor_and_wall": True,
                "on_floor_freestanding": True,
                "obj_ontop_obj": True,
            },
            "stage_exclusive": False,
            "terrain_enabled": False,
            "topview": False,
            "animate_cameras_enabled": False,
            "floating_objs_enabled": False,
            "restrict_single_supported_roomtype": False,
        },
    },
]


def get_prompt(input_text: str) -> str:
    """Get formatted prompt for LLM.

    Args:
        input_text: Natural language input text

    Returns:
        Formatted prompt string
    """
    room_types_str = get_room_types_for_prompt()
    object_types_str = get_object_types_for_prompt()
    return PROMPT_TEMPLATE.format(
        room_types=room_types_str, object_types=object_types_str, input_text=input_text
    )


def get_examples() -> list[dict]:
    """Get example inputs and outputs for few-shot learning.

    Returns:
        List of example dictionaries with 'input' and 'output' keys
    """
    return EXAMPLE_INPUTS_OUTPUTS
