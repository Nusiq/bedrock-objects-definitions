# AUTOGENERATED! DON'T EDIT!
from .jpath import *


def files(*resource_pack_paths: Path) -> Iterator[Path]:
    for pack_path in resource_pack_paths:
        for file in pack_path.glob("sounds/sound_definitions.json"):
            yield file


def objects(*paths: Path) -> Iterator[Json]:
    for item_path in paths:
        try:
            with item_path.open('r') as f:
                yield from get_jpath_multi(Json(None, json.load(f)), ["sound_definitions", Jpath.STR])
        except:
            continue


def identifiers(*objects: Json) -> Iterator[str]:
    for obj in objects:
        identifier = get_jpath_single(obj, [])
        if identifier is not None and isinstance(identifier.key, str):
            result = identifier.key

            yield result
