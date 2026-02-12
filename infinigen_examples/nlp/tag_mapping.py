# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Tag mapping utilities for converting natural language to Semantics tags."""

from __future__ import annotations

from typing import Optional

from infinigen.core import tags as t

# Room type mappings (Korean and English)
ROOM_MAPPINGS = {
    # Korean
    "주방": t.Semantics.Kitchen,
    "침실": t.Semantics.Bedroom,
    "거실": t.Semantics.LivingRoom,
    "응접실": t.Semantics.LivingRoom,
    # NOTE: "옷장" is NOT mapped here — it primarily means "wardrobe" (furniture/Storage).
    # Use unambiguous room-only keywords for the Closet room type:
    "옷방": t.Semantics.Closet,
    "드레스룸": t.Semantics.Closet,
    "붙박이장": t.Semantics.Closet,
    "복도": t.Semantics.Hallway,
    "화장실": t.Semantics.Bathroom,
    "욕실": t.Semantics.Bathroom,
    "차고": t.Semantics.Garage,
    "발코니": t.Semantics.Balcony,
    "식당": t.Semantics.DiningRoom,
    "다이닝룸": t.Semantics.DiningRoom,
    "유틸리티": t.Semantics.Utility,
    "계단실": t.Semantics.StaircaseRoom,
    "사무실": t.Semantics.Office,
    "회의실": t.Semantics.MeetingRoom,
    "휴게실": t.Semantics.BreakRoom,
    # English
    "kitchen": t.Semantics.Kitchen,
    "bedroom": t.Semantics.Bedroom,
    "living room": t.Semantics.LivingRoom,
    "livingroom": t.Semantics.LivingRoom,
    "closet": t.Semantics.Closet,
    "hallway": t.Semantics.Hallway,
    "bathroom": t.Semantics.Bathroom,
    "garage": t.Semantics.Garage,
    "balcony": t.Semantics.Balcony,
    "dining room": t.Semantics.DiningRoom,
    "diningroom": t.Semantics.DiningRoom,
    "utility": t.Semantics.Utility,
    "staircase room": t.Semantics.StaircaseRoom,
    "staircaseroom": t.Semantics.StaircaseRoom,
    "office": t.Semantics.Office,
    "meeting room": t.Semantics.MeetingRoom,
    "meetingroom": t.Semantics.MeetingRoom,
    "break room": t.Semantics.BreakRoom,
    "breakroom": t.Semantics.BreakRoom,
}

# Object type mappings (Korean and English)
OBJECT_MAPPINGS = {
    # Korean
    "침대": t.Semantics.Bed,
    "소파": t.Semantics.LoungeSeating,
    "테이블": t.Semantics.Table,
    "책상": t.Semantics.Desk,
    "옷장": t.Semantics.Storage,
    "선반": t.Semantics.Storage,
    "싱크대": t.Semantics.Sink,
    "조리대": t.Semantics.KitchenCounter,
    "가전제품": t.Semantics.KitchenAppliance,
    "가구": t.Semantics.Furniture,
    "벽장식": t.Semantics.WallDecoration,
    "그릇": t.Semantics.Dishware,
    "식기": t.Semantics.Dishware,
    "조리기구": t.Semantics.Cookware,
    "수저": t.Semantics.Utensils,
    "램프": t.Semantics.Lighting,
    "조명": t.Semantics.Lighting,
    "천장등": t.Semantics.CeilingLight,
    # Additional Korean mappings
    "러운지": t.Semantics.LoungeSeating,
    "사이드테이블": t.Semantics.SideTable,
    "보조테이블": t.Semantics.SideTable,
    "욕조": t.Semantics.Bathing,
    "목욕": t.Semantics.Bathing,
    "화면": t.Semantics.Watchable,
    "모니터": t.Semantics.Watchable,
    "티비": t.Semantics.Watchable,
    "텔레비전": t.Semantics.Watchable,
    "테이블장식": t.Semantics.TableDisplayItem,
    "테이블장식품": t.Semantics.TableDisplayItem,
    "사무실선반물품": t.Semantics.OfficeShelfItem,
    "주방조리대물품": t.Semantics.KitchenCounterItem,
    "식품저장고": t.Semantics.FoodPantryItem,
    "식료품": t.Semantics.FoodPantryItem,
    "욕실용품": t.Semantics.BathroomItem,
    "선반장식": t.Semantics.ShelfTrinket,
    "선반장식품": t.Semantics.ShelfTrinket,
    "천": t.Semantics.ClothDrapeItem,
    "천장식": t.Semantics.ClothDrapeItem,
    "의류": t.Semantics.ClothDrapeItem,
    "의자": t.Semantics.Chair,
    "창문": t.Semantics.Window,
    "문": t.Semantics.Door,
    "입구": t.Semantics.Entrance,
    "매트": t.Semantics.FloorMat,
    "바닥매트": t.Semantics.FloorMat,
    "휴대품": t.Semantics.HandheldItem,
    "손에드는물건": t.Semantics.HandheldItem,
    # English
    "bed": t.Semantics.Bed,
    "chair": t.Semantics.Chair,
    "seating": t.Semantics.Seating,
    "sofa": t.Semantics.LoungeSeating,
    "couch": t.Semantics.LoungeSeating,
    "lounge seating": t.Semantics.LoungeSeating,
    "loungeseating": t.Semantics.LoungeSeating,
    "table": t.Semantics.Table,
    "side table": t.Semantics.SideTable,
    "sidetable": t.Semantics.SideTable,
    "end table": t.Semantics.SideTable,
    "desk": t.Semantics.Desk,
    "storage": t.Semantics.Storage,
    "shelf": t.Semantics.Storage,
    "cabinet": t.Semantics.Storage,
    "sink": t.Semantics.Sink,
    "kitchen counter": t.Semantics.KitchenCounter,
    "kitchencounter": t.Semantics.KitchenCounter,
    "counter": t.Semantics.KitchenCounter,
    "appliance": t.Semantics.KitchenAppliance,
    "kitchen appliance": t.Semantics.KitchenAppliance,
    "furniture": t.Semantics.Furniture,
    "wall decoration": t.Semantics.WallDecoration,
    "dishware": t.Semantics.Dishware,
    "cookware": t.Semantics.Cookware,
    "utensils": t.Semantics.Utensils,
    "lighting": t.Semantics.Lighting,
    "lamp": t.Semantics.Lighting,
    "ceiling light": t.Semantics.CeilingLight,
    "ceilinglight": t.Semantics.CeilingLight,
    # Additional English mappings
    "bathing": t.Semantics.Bathing,
    "bathtub": t.Semantics.Bathing,
    "bath": t.Semantics.Bathing,
    "watchable": t.Semantics.Watchable,
    "tv": t.Semantics.Watchable,
    "television": t.Semantics.Watchable,
    "screen": t.Semantics.Watchable,
    "monitor": t.Semantics.Watchable,
    "table display item": t.Semantics.TableDisplayItem,
    "tabledisplayitem": t.Semantics.TableDisplayItem,
    "table decoration": t.Semantics.TableDisplayItem,
    "office shelf item": t.Semantics.OfficeShelfItem,
    "officeshelfitem": t.Semantics.OfficeShelfItem,
    "kitchen counter item": t.Semantics.KitchenCounterItem,
    "kitchencounteritem": t.Semantics.KitchenCounterItem,
    "food pantry": t.Semantics.FoodPantryItem,
    "foodpantry": t.Semantics.FoodPantryItem,
    "pantry item": t.Semantics.FoodPantryItem,
    "bathroom item": t.Semantics.BathroomItem,
    "bathroomitem": t.Semantics.BathroomItem,
    "shelf trinket": t.Semantics.ShelfTrinket,
    "shelftrinket": t.Semantics.ShelfTrinket,
    "cloth drape": t.Semantics.ClothDrapeItem,
    "clothdrape": t.Semantics.ClothDrapeItem,
    "drape": t.Semantics.ClothDrapeItem,
    "cloth": t.Semantics.ClothDrapeItem,
    "window": t.Semantics.Window,
    "door": t.Semantics.Door,
    "entrance": t.Semantics.Entrance,
    "floor mat": t.Semantics.FloorMat,
    "floormat": t.Semantics.FloorMat,
    "mat": t.Semantics.FloorMat,
    "rug": t.Semantics.FloorMat,
    "handheld item": t.Semantics.HandheldItem,
    "handhelditem": t.Semantics.HandheldItem,
    "handheld": t.Semantics.HandheldItem,
    # Common LLM output aliases (the model sometimes uses these instead of canonical names)
    "wardrobe": t.Semantics.Storage,
    "closet": t.Semantics.Storage,
    "armoire": t.Semantics.Storage,
    "bookshelf": t.Semantics.Storage,
    "nightstand": t.Semantics.SideTable,
    "armchair": t.Semantics.LoungeSeating,
    "recliner": t.Semantics.LoungeSeating,
    "stool": t.Semantics.Seating,
    "food": t.Semantics.FoodPantryItem,
    "foodpantryitem": t.Semantics.FoodPantryItem,
    "음식": t.Semantics.FoodPantryItem,
    "음식물": t.Semantics.FoodPantryItem,
    "안락의자": t.Semantics.LoungeSeating,
    "싱크": t.Semantics.Sink,  # Shortened form of 싱크대
    # Access types (less common in natural language, but included for completeness)
    "access top": t.Semantics.AccessTop,
    "accesstop": t.Semantics.AccessTop,
    "access front": t.Semantics.AccessFront,
    "accessfront": t.Semantics.AccessFront,
    "access any side": t.Semantics.AccessAnySide,
    "accessanyside": t.Semantics.AccessAnySide,
    "access all sides": t.Semantics.AccessAllSides,
    "accessallsides": t.Semantics.AccessAllSides,
    "access standing near": t.Semantics.AccessStandingNear,
    "accessstandingnear": t.Semantics.AccessStandingNear,
    "access sit": t.Semantics.AccessSit,
    "accesssit": t.Semantics.AccessSit,
    "access open door": t.Semantics.AccessOpenDoor,
    "accessopendoor": t.Semantics.AccessOpenDoor,
    "access hand": t.Semantics.AccessHand,
    "accesshand": t.Semantics.AccessHand,
}

# Location relationship keywords (for stage control)
LOCATION_KEYWORDS = {
    # Korean
    "바닥": "floor",
    "바닥에": "floor",
    "바닥에만": "floor_only",
    "벽": "wall",
    "벽에": "wall",
    "벽에만": "wall_only",
    "천장": "ceiling",
    "천장에": "ceiling",
    "천장에만": "ceiling_only",
    "위에": "on_top",
    "위에만": "on_top_only",
    # English
    "floor": "floor",
    "on floor": "floor",
    "on the floor": "floor",
    "floor only": "floor_only",
    "wall": "wall",
    "on wall": "wall",
    "on the wall": "wall",
    "wall only": "wall_only",
    "ceiling": "ceiling",
    "on ceiling": "ceiling",
    "on the ceiling": "ceiling",
    "ceiling only": "ceiling_only",
    "on top": "on_top",
    "on top of": "on_top",
    "on top only": "on_top_only",
}


def map_room_name_to_tag(room_name: str) -> Optional[t.Semantics]:
    """Map natural language room name to Semantics tag.

    Args:
        room_name: Natural language room name (Korean or English)

    Returns:
        Semantics tag if found, None otherwise
    """
    room_name_lower = room_name.lower().strip()
    return ROOM_MAPPINGS.get(room_name_lower)


def map_object_name_to_tag(object_name: str) -> Optional[t.Semantics]:
    """Map natural language object name to Semantics tag.

    Args:
        object_name: Natural language object name (Korean or English)

    Returns:
        Semantics tag if found, None otherwise
    """
    object_name_lower = object_name.lower().strip()
    return OBJECT_MAPPINGS.get(object_name_lower)


def parse_location_keyword(keyword: str) -> Optional[str]:
    """Parse location keyword to determine stage control.

    Args:
        keyword: Location keyword (Korean or English)

    Returns:
        Normalized location keyword or None
    """
    keyword_lower = keyword.lower().strip()
    return LOCATION_KEYWORDS.get(keyword_lower)


def get_all_room_types():
    """Get all available room types as Semantics tags.

    Returns:
        Set of room type Semantics tags
    """
    return set(ROOM_MAPPINGS.values())


def get_all_object_types():
    """Get all available object types as Semantics tags.

    Returns:
        Set of object type Semantics tags
    """
    return set(OBJECT_MAPPINGS.values())


# Detailed stage type keywords mapping
STAGE_TYPE_KEYWORDS = {
    # Korean
    "벽에 붙여서": "on_floor_and_wall",
    "벽에 붙은": "on_floor_and_wall",
    "벽면": "on_floor_and_wall",
    "독립형": "on_floor_freestanding",
    "프리스탠딩": "on_floor_freestanding",
    "중앙에": "on_floor_freestanding",
    "방 중앙": "on_floor_freestanding",
    "벽에만": "on_wall",
    "벽 장식": "on_wall",
    "벽 선반": "on_wall",
    "천장": "on_ceiling",
    "천장에": "on_ceiling",
    "매달린": "on_ceiling",
    "옆에": "side_obj",
    "옆으로": "side_obj",
    "나란히": "side_obj",
    "위에": "obj_ontop_obj",
    "위에만": "obj_ontop_obj",
    "지지면에": "obj_on_support",
    "표면에": "obj_on_support",
    # English
    "against wall": "on_floor_and_wall",
    "wall-mounted": "on_floor_and_wall",
    "touching wall": "on_floor_and_wall",
    "freestanding": "on_floor_freestanding",
    "center": "on_floor_freestanding",
    "middle of room": "on_floor_freestanding",
    "not against wall": "on_floor_freestanding",
    "on wall": "on_wall",
    "wall decoration": "on_wall",
    "wall shelf": "on_wall",
    "ceiling": "on_ceiling",
    "hanging": "on_ceiling",
    "ceiling light": "on_ceiling",
    "beside": "side_obj",
    "next to": "side_obj",
    "side by side": "side_obj",
    "on top of": "obj_ontop_obj",
    "ontop": "obj_ontop_obj",
    "above": "obj_ontop_obj",
    "on support": "obj_on_support",
    "on surface": "obj_on_support",
    "on counter": "obj_on_support",
    "on table": "obj_on_support",
}


def parse_stage_type_keyword(keyword: str) -> Optional[str]:
    """Parse stage type keyword to determine specific stage type.

    Args:
        keyword: Stage type keyword (Korean or English)

    Returns:
        Normalized stage type name or None
    """
    keyword_lower = keyword.lower().strip()
    return STAGE_TYPE_KEYWORDS.get(keyword_lower)


def location_to_stage_flags(location: str) -> dict[str, bool]:
    """Convert location description to stage enable/disable flags.

    Note: Location relationships cannot be directly controlled via gin config.
    Instead, we control stages indirectly:
    - "floor only" -> disable medium and small stages
    - "wall/ceiling only" -> disable large and small stages
    - "on top only" -> disable large and medium stages

    Args:
        location: Location description (e.g., "floor only", "wall", "on top")

    Returns:
        Dictionary with solve_*_enabled flags
    """
    normalized = parse_location_keyword(location)

    if normalized == "floor_only":
        return {
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": False,
        }
    elif normalized in ("wall_only", "ceiling_only"):
        return {
            "solve_large_enabled": False,
            "solve_medium_enabled": True,
            "solve_small_enabled": False,
        }
    elif normalized in ("on_top_only"):
        return {
            "solve_large_enabled": False,
            "solve_medium_enabled": False,
            "solve_small_enabled": True,
        }
    else:
        # Default: enable all stages
        return {
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": True,
        }


def stage_types_to_stage_flags(
    stage_types: dict[str, bool],
    exclusive: bool = False,
) -> dict[str, bool]:
    """Convert detailed stage types to high-level stage enable/disable flags.

    This function maps the 7 detailed stage types to the 3 main stages:
    - solve_large: on_floor_and_wall, on_floor_freestanding
    - solve_medium: on_wall, on_ceiling, side_obj
    - solve_small: obj_ontop_obj, obj_on_support

    The behavior depends on the exclusive flag:
    - exclusive=False (default): stage_types is purely descriptive.
      All stages remain True regardless of stage_types content.
      This is the case for descriptions like "책상 위에 마우스가 있게 해줘".
    - exclusive=True: stage_types is restrictive ("only/만" semantics).
      Only stages with at least one sub-type set to True are enabled;
      stages with no sub-types mentioned or all False are disabled.
      This is the case for descriptions like "바닥에만 배치해줘".

    Args:
        stage_types: Dictionary with stage type flags (e.g., {"on_floor_and_wall": True, ...})
        exclusive: If True, only enable stages that have at least one sub-type True.
                   If False, all stages remain True (stage_types is informational only).

    Returns:
        Dictionary with solve_*_enabled flags
    """
    # Default: all stages enabled
    default_flags = {
        "solve_large_enabled": True,
        "solve_medium_enabled": True,
        "solve_small_enabled": True,
    }

    if not stage_types:
        return default_flags

    # If not exclusive, stage_types is descriptive only — don't restrict anything
    if not exclusive:
        return default_flags

    # Exclusive mode: only enable stages that have at least one sub-type explicitly True
    large_types = ["on_floor_and_wall", "on_floor_freestanding"]
    medium_types = ["on_wall", "on_ceiling", "side_obj"]
    small_types = ["obj_ontop_obj", "obj_on_support"]

    def _any_explicitly_true(sub_types: list[str]) -> bool:
        """Return True if any sub-type is explicitly set to True."""
        return any(stage_types.get(st) is True for st in sub_types)

    solve_large = _any_explicitly_true(large_types)
    solve_medium = _any_explicitly_true(medium_types)
    solve_small = _any_explicitly_true(small_types)

    # Enforce stage dependencies:
    # - solve_small requires solve_large (objects on top need base objects on floor first)
    # - side_obj (in medium) requires solve_large (objects beside need base objects first)
    if solve_small:
        solve_large = True
    if stage_types.get("side_obj") is True:
        solve_large = True

    return {
        "solve_large_enabled": solve_large,
        "solve_medium_enabled": solve_medium,
        "solve_small_enabled": solve_small,
    }
