# This is the fil is NOT autogenerated
from typing import (
    NamedTuple, Tuple, List, Dict, Any, Iterator, Optional, Union,
    Iterable)
from pathlib import Path
import re
import json
from enum import Enum

class Jpath(Enum):
    INT = 0
    STR = 1
    ANY = 2
    SKIP_LIST = 3

JsonKey = Union[str, int]

class Json(NamedTuple):
    key: Optional[JsonKey]
    value: Union[str, float, int, bool, None, List, Dict]

JPathSingle = List[Union[str, int]]
JPathMulti = List[Union[str, int, Jpath, re.Pattern]]

def get_jpath_multi(obj: Json, path: JPathMulti) -> Iterator[Json]:
    """
    Returns values from given Json path
    """
    if len(path) == 0:
        yield obj
        return
    k, new_path = path[0], path[1:]
    if isinstance(k, str) or isinstance(k, int):
        try:
            new_obj = Json(k, obj.value[k])  # type: ignore
        except:
            return
        yield from get_jpath_multi(new_obj, new_path)
    if isinstance(k, Jpath):
        if k == Jpath.INT:
            if not isinstance(obj.value, list):
                return
            for new_obj_k, new_obj_v in enumerate(obj.value):
                yield from get_jpath_multi(Json(new_obj_k, new_obj_v), new_path)
        if k == Jpath.STR:
            if not isinstance(obj.value, dict):
                return
            for new_obj_k, new_obj_v in obj.value.items():
                yield from get_jpath_multi(Json(new_obj_k, new_obj_v), new_path)
        if k == Jpath.ANY:
            if isinstance(obj.value, list):
                for new_obj_k, new_obj_v in enumerate(obj.value):
                    yield from get_jpath_multi(Json(new_obj_k, new_obj_v), new_path)
            elif isinstance(obj.value, dict):
                for new_obj_k, new_obj_v in obj.value.items():
                    yield from get_jpath_multi(Json(new_obj_k, new_obj_v), new_path)
            else:
                return
        if k == Jpath.SKIP_LIST:
            if isinstance(obj.value, list):
                for new_obj_k, new_obj_v in enumerate(obj.value):
                    yield from get_jpath_multi(Json(new_obj_k, new_obj_v), new_path)
            else:
                yield from get_jpath_multi(obj, new_path)
    if isinstance(k, re.Pattern):
            if not isinstance(obj.value, dict):
                return
            for new_obj_k, new_obj_v in obj.value.items():
                if not k.fullmatch(new_obj_k):
                    continue
                yield from get_jpath_multi(Json(new_obj_k, new_obj_v), new_path)

def get_jpath_single(obj: Json, path: JPathSingle) -> Optional[Json]:
    """
    Returns value from given Json path
    """
    for p in path:
        try:
            if isinstance(obj.value, dict):
                obj = Json(p, obj.value[p])
            elif isinstance(obj.value, list):
                obj = Json(p, obj.value[p])
            else:
                return None
        except:
            return None
    return obj
