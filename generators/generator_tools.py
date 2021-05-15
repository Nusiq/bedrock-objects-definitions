from __future__ import annotations
from typing import Dict, Iterator, List, NewType, Union, NamedTuple, Optional
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from abc import ABC, abstractmethod
import json

# Loading data from source files
def load_filters(data: Optional[Dict]) -> Optional[FiltersDef]:
    if data is None:
        return None
    items: FilterItems = []
    for i in data['items']:
        if isinstance(i, str):
            items.append(i)
        elif 'regex' in i:
            items.append(FilterItemRegex(i['regex']))
        elif 'starts_with' in i:
            items.append(FilterItemStartsWith(i['starts_with']))
        elif 'ends_with' in i:
            items.append(FilterItemEndsWith(i['ends_with']))
        else:
            raise Exception("Unknown filter option")
    return FiltersDef(exclude=data['exclude'], items=items)

def load_processing(data: Optional[Dict]) -> Optional[ProcessingDef]:
    if data is None:
        return None
    postprocessing: PostprocessingDef = []
    if 'postprocessing' in data:
        for i in data['postprocessing']:
            if 'change_case' in i:
                i = i['change_case']
                postprocessing.append(
                    PostprocessingChangeCaseDef(lower=(i == 'lower')))
            elif 'file_path' in i:
                i = i['file_path']
                # with current syntax of the object definition i should be
                # equal to "cut_extension" str
                postprocessing.append(PostprocessingFilePathDef())
            elif 'prune' in i:
                i = i['prune']
                front = i["front"] if "front" in i else None
                end = i["end"] if "end" in i else None
                postprocessing.append(PostprocessingPruneDef(front, end))
            elif 'substring' in i:
                i = i['substring']
                i = i['prune']
                front = i["front"] if "front" in i else None
                end = i["end"] if "end" in i else None
                postprocessing.append(PostprocessingSubstringDef(front, end))
            elif 'regex_replace' in i:
                i = i['regex_replace']
                postprocessing.append(PostprocessingRegexReplace(
                    case_sensitive=i['case_sensitive'],
                    match=i['match'],
                    out=i['out']))
            else:
                raise Exception("Unknown postprocessing option")

    postprocessing_filters = load_filters(
        data['postprocessing_filters']
        if 'postprocessing_filters' in data else None)
    filters = load_filters(
        data['filters']
        if 'filters' in data else None)
    return ProcessingDef(
        postprocessing=postprocessing,
        filters=filters,
        postprocessing_filters=postprocessing_filters)

def load_access_paths(data: List) -> List[Union[AccessPathKeyDef, AccessPathValueDef]]:
    access_paths: List[
        Union[AccessPathKeyDef, AccessPathValueDef]] = []
    for ap in data:
        if 'json_path_key' in ap:
            ap = ap['json_path_key']
            access_paths.append(AccessPathKeyDef(
                multi=ap['multi'], path_start=ap['path_start'],
                path=ap['path'],
                processing=load_processing(ap.get('processing'))
            ))
        elif 'json_path_value' in ap:
            ap = ap['json_path_value']
            access_paths.append(AccessPathValueDef(
                multi=ap['multi'], path_start=ap['path_start'],
                path=ap['path'],
                processing=load_processing(ap.get('processing'))
            ))
        else:
            raise Exception("Invalid access path")
    return access_paths

def load_properties(data: Dict, parent_path: List[str]) -> List[PropertyDef]:
    result: List[PropertyDef] = []
    access_paths: List
    for k, v in data.items():
        if "reference" in v:
            value = v["reference"]
            access_paths = load_access_paths(value['access_paths'])
            value = ReferenceDef(
                value['referenced_object'], access_paths=access_paths)
        elif "alias_reference" in v:
            value = v["alias_reference"]
            access_paths = load_access_paths(value['access_paths'])
            value = AliasReferenceDef(
                value['map_provider'], value['map_path'], access_paths=access_paths)
        elif "alias_mapping" in v:
            value = v["alias_mapping"]
            access_paths = []
            for ap in value['access_paths']:
                access_paths.append(AccessPathKeyValuePairDef(
                    multi=ap['multi'], path_start=ap['path_start'],
                    path=ap['path'],
                    key_processing=load_processing(ap.get('key_processing')),
                    value_processing=load_processing(ap.get('value_processing')),
                ))
            value = AliasMappingDef(
                value['referenced_object'], access_paths=access_paths)
        elif "custom_value" in v:
            value = v["custom_value"]
            access_paths = load_access_paths(value['access_paths'])
            value = CustomValueDef(
                value['expected_type'], access_paths=access_paths,
                subproperties=load_properties(
                    value['subproperties'], parent_path + [k]
                ))
        else:
            raise Exception("Invalid property")
        result.append(
            PropertyDef(name=k, value=value, parent_path=parent_path)
        )
    return result

def load_models(p: Path) -> List[RootDef]:
    result = []
    for model in p.glob('*.json'):
        with model.open('r') as f:
            data = json.load(f)
        identifier = data['identifier']
        if "file-path" in identifier:
            identifier = identifier["file-path"]
            identifier = FilePathIdentifierDef(
                processing=load_processing(identifier.get('processing')))
        elif "json-path-key" in identifier:
            identifier = identifier["json-path-key"]
            identifier = JpathKeyIdentifierDef(
                processing=load_processing(identifier.get('processing')),
                path=identifier['path'])
        elif "json-path-value" in identifier:
            identifier = identifier["json-path-value"]
            identifier = JpathValueIdentifierDef(
                processing=load_processing(identifier.get('processing')),
                path=identifier['path'])
        else:
            raise Exception("Invalid identifier")
        result.append(
            RootDef(
                name=model.stem,
                multi=data['multi'], type=data['type'], pack_type=data['pack_type'],
                path=data['path'], json_path=data['json_path'],
                identifier=identifier,
                properties=load_properties(data['properties'], [model.stem])
            )
        )
    return result

# Data classes created with load functions
@dataclass
class FilterItemRegex:
    value: str

@dataclass
class FilterItemStartsWith:
    value: str

@dataclass
class FilterItemEndsWith:
    value: str

FilterItems = List[Union[
    str, FilterItemRegex,
    FilterItemStartsWith,
    FilterItemEndsWith]]

@dataclass
class FiltersDef:
    exclude: bool
    items: FilterItems

@dataclass
class PostprocessingChangeCaseDef:
    lower: bool

@dataclass
class PostprocessingFilePathDef:
    '''No data always "cut_extension"'''

@dataclass
class PostprocessingPruneDef:
    front: Optional[str]
    end: Optional[str]

@dataclass
class PostprocessingSubstringDef:
    front: Optional[int]
    end: Optional[int]

@dataclass
class PostprocessingRegexReplace:
    case_sensitive: bool
    match: str
    out: str

PostprocessingDef = List[Union[
    PostprocessingChangeCaseDef,
    PostprocessingFilePathDef,
    PostprocessingPruneDef,
    PostprocessingSubstringDef,
    PostprocessingRegexReplace]]

@dataclass
class ProcessingDef:
    postprocessing: PostprocessingDef
    filters: Optional[FiltersDef]
    postprocessing_filters: Optional[FiltersDef]

JsonPath = List[Union[str, int]]

@dataclass
class JpathKeyIdentifierDef:
    processing: Optional[ProcessingDef]
    path: JsonPath

@dataclass
class JpathValueIdentifierDef:
    processing: Optional[ProcessingDef]
    path: JsonPath

@dataclass
class FilePathIdentifierDef:
    processing: Optional[ProcessingDef]

IdentifierDef = Union[
    JpathKeyIdentifierDef,
    JpathValueIdentifierDef,
    FilePathIdentifierDef]

@dataclass
class AccessPathValueDef:
    multi: bool
    path: JsonPath
    path_start: str
    processing: Optional[ProcessingDef]

@dataclass
class AccessPathKeyDef:
    multi: bool
    path_start: str
    path: JsonPath
    processing: Optional[ProcessingDef]

@dataclass
class AccessPathKeyValuePairDef:
    multi: bool
    path_start: str
    path: JsonPath
    key_processing: Optional[ProcessingDef]
    value_processing: Optional[ProcessingDef]

@dataclass
class ReferenceDef:
    referenced_object: str
    access_paths: List[Union[AccessPathValueDef, AccessPathKeyDef]]

@dataclass
class AliasReferenceDef:
    map_provider: str
    map_path: List[str]
    access_paths: List[Union[AccessPathValueDef, AccessPathKeyDef]]

@dataclass
class AliasMappingDef:
    referenced_object: str
    access_paths: List[AccessPathKeyValuePairDef]

@dataclass
class CustomValueDef:
    expected_type: str
    access_paths: List[Union[AccessPathValueDef, AccessPathKeyDef]]
    subproperties: List[PropertyDef]

@dataclass
class PropertyDef:
    parent_path: List[str]
    name: str
    value: Union[ReferenceDef, AliasReferenceDef, AliasMappingDef,CustomValueDef]

@dataclass
class RootDef:
    name: str
    multi: bool
    type: str
    pack_type: str
    path: List[str]
    json_path: JsonPath
    identifier: IdentifierDef
    properties: List[PropertyDef]

# Generator class
class CodeGenerator(ABC):
    @abstractmethod
    def generate(self, models: List[RootDef]): ...

    @abstractmethod
    def properties_search__reference(
        self, property: ReferenceDef, parent_names: List[str], model: RootDef,
        target_path: str): ...
    @abstractmethod
    def properties_search__alias_reference(
        self, property: AliasReferenceDef, parent_names: List[str],
        model: RootDef, target_path: str): ...
    @abstractmethod
    def properties_search__alias_mapping(
        self, property: AliasMappingDef, parent_names: List[str],
        model: RootDef, target_path: str): ...
    @abstractmethod
    def properties_search__custom_value(
        self, property: CustomValueDef, parent_names: List[str],
        model: RootDef, target_path: str): ...

    @abstractmethod
    def make_object_search(
        self, model: RootDef, target_path: str): ...

    @abstractmethod
    def make_file_search(
        self, model: RootDef, target_path: str): ...

    @abstractmethod
    def make_identifier_search(
        self, model: RootDef, target_path: str): ...

    def make_properties_search(
            self, properties: List[PropertyDef],  model: RootDef,
            target_path: str):
        for property in properties:
            parent_names = property.parent_path + [property.name]

            if isinstance(property.value, ReferenceDef):
                self.properties_search__reference(
                    property.value, parent_names, model, target_path)
            elif isinstance(property.value, AliasReferenceDef):
                self.properties_search__alias_reference(
                    property.value, parent_names, model, target_path)
            elif isinstance(property.value, AliasMappingDef):
                self.properties_search__alias_mapping(
                    property.value, parent_names, model, target_path)
            elif isinstance(property.value, CustomValueDef):
                has_subproperties = (len(property.value.subproperties) > 0)
                self.properties_search__custom_value(
                    property.value, parent_names, model, target_path)
                if has_subproperties:
                    self.make_properties_search(
                        property.value.subproperties, model, target_path)

# Text formatting
def upper_camel_case(string: str):
    return string.replace('_', ' ').title().replace(' ', '')

def unindent(n_spaces: int, string: str, ignore_errors=False):
    lines: List[str] = []
    for line in string.split('\n'):
        if not line.startswith(' '*n_spaces):
            if ignore_errors:
                lines.append(line)
            else:
                raise Exception("ERROR! Wrong indentation!")
        else:
            lines.append(line[n_spaces:])
    return '\n'.join(lines)

def indent(n_spaces: int, string: str):
    lines: List[str] = []
    for line in string.split('\n'):
            lines.append(" "*n_spaces + line)
    return '\n'.join(lines)
