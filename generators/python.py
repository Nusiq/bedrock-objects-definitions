'''
Example python code generator.
'''
from __future__ import annotations
from generator_tools import *

# Helper functions for the generator
def to_jpath(keys: List[Union[str, int]]) -> str:
    result: List[str] = []
    for k in keys:
        if not isinstance(k, str):
            result.append(str(k))
        elif k == "@INT":
            result.append("Jpath.INT")
        elif k == "@STR":
            result.append("Jpath.STR")
        elif k == "@ANY":
            result.append("Jpath.ANY")
        elif k == "@SKIP_LIST":
            result.append("Jpath.SKIP_LIST")
        elif k.startswith('@'):
            result.append(f"re.compile('{k[1:]}')")
        else:
            result.append(f'"{k}"')
    return f'[{", ".join(result)}]'

def to_type(string: str) -> str:
    return {
        "array": "List",
        "boolean": "bool",
        "integer": "int",
        "null": "None",
        "number": "float",
        "object": "Dict",
        "string": "str"
    }[string]

def make_value_filter(filters: FiltersDef, value: str, results: List[str]):
    exclude = filters.exclude
    literal_filters = []
    for processing_fileter in filters.items:
        if isinstance(processing_fileter, str):
            literal_filters.append(processing_fileter)
        elif isinstance(processing_fileter, FilterItemRegex):
            results.append(unindent(12, f'''\
            if {"" if exclude else "not "}bool(re.fullmatch("{processing_fileter.value}", {value})):
                continue'''))
        elif isinstance(processing_fileter, FilterItemStartsWith):
            results.append(unindent(12, f'''\
            if {"" if exclude else "not "}{value}.startswith("{processing_fileter.value}"):
                continue'''))
        elif isinstance(processing_fileter, FilterItemEndsWith):
            results.append(unindent(12, f'''\
            if {"" if exclude else "not "}{value}.startswith("{processing_fileter.value}"):
                continue'''))
    if len(literal_filters) > 0:
        results.append(unindent(8, f'''\
        if {value} {"" if exclude else "not "}in {literal_filters}:
            continue'''))

def make_value_processing(value: str, processing: Optional[ProcessingDef]) -> str:
    if processing is None:
        return ''
    results: List[str] = []
    if processing.filters is not None:
        make_value_filter(processing.filters, value, results)
    if len(processing.postprocessing) > 0:
        for p in processing.postprocessing:
            if isinstance(p, PostprocessingChangeCaseDef):
                results.append(
                    f'    {value} = {value}{"lower" if p.lower else "upper"}()')
            elif isinstance(p, PostprocessingFilePathDef):
                results.append(
                    f'    {value} = Path({value}).with_suffix("").as_posix()')
            elif isinstance(p, PostprocessingPruneDef):
                if p.front:
                    results.append(
                        f'    {value} = {value}.lstrip("{p.front}")')
                if p.end is not None:
                    results.append(
                        f'    {value} = {value}.rstrip("{p.end}")')
            elif isinstance(p, PostprocessingSubstringDef):
                if p.front:
                    results.append(
                        f'    {value} = {value}[{p.front}:]')
                if p.end is not None:
                    results.append(
                        f'    {value} = {value}[:{p.end}]')
            elif isinstance(p, PostprocessingRegexReplace):
                if p.case_sensitive:
                    results.append(
                        f'    {value} = re.sub("{p.match}", "{p.out}", {value})'
                    )
                else:
                    results.append(
                        f'    {value} = re.sub("{p.match}", "{p.out}", {value}, re.IGNORECASE)'
                    )
    if processing.postprocessing_filters is not None:
        make_value_filter(processing.postprocessing_filters, value, results)
    return '\n'.join(results)

class PyIteratorsGenerator(CodeGenerator):
    def __init__(self):
        self.files: Dict[str, list] = defaultdict(list)  # The files to generate

    def generate(self, models: List[RootDef]):
        for model in models:
            target_path = f"{model.name}.py"
            self.make_file_search(model, target_path)
            self.make_object_search(model, target_path)
            self.make_identifier_search(model, target_path)
            self.make_properties_search(model.properties, model, target_path)

    def make_file_search(self, model: RootDef, target_path: str):
        name = model.name
        pack_type = model.pack_type
        glob_patterns = model.path
        if len(glob_patterns) > 1:
            pack_name = pack_type.replace('-', '_')
            pack_paths = f'{pack_name}_paths'
            self.files[target_path].append(unindent(12, f'''\
            def files(*{pack_paths}: Path) -> Iterator[Path]:
                for pattern in {glob_patterns}:
                    for pack_path in {pack_paths}:
                        for file in pack_path.glob(pattern):
                            yield file
            '''))
        else:
            pack_name = pack_type.replace('-', '_')
            pack_paths = f'{pack_name}_paths'
            glob_pattern = f'"{glob_patterns[0]}"'
            self.files[target_path].append(unindent(12, f'''\
            def files(*{pack_paths}: Path) -> Iterator[Path]:
                for pack_path in {pack_paths}:
                    for file in pack_path.glob({glob_pattern}):
                        yield file
            '''))

    def make_object_search(self, model: RootDef, target_path: str):
        name = model.name
        json_path = to_jpath(model.json_path)
        if model.multi:
            self.files[target_path].append(unindent(12, f'''\
            def objects(*paths: Path) -> Iterator[Json]:
                for item_path in paths:
                    try:
                        with item_path.open('r') as f:
                            yield from get_jpath_multi(Json(None, json.load(f)), {json_path})
                    except:
                        continue
            '''))
        else:
            self.files[target_path].append(unindent(12, f'''\
            def objects(*paths: Path) -> Iterator[Optional[Json]]:
                for item_path in paths:
                    try:
                        with item_path.open('r') as f:
                            yield get_jpath_single(Json(None, json.load(f)), {json_path})
                    except:
                        yield None
            '''))

    def make_identifier_search(self, model: RootDef, target_path: str):
        result: List[str] = []
        if isinstance(model.identifier, FilePathIdentifierDef):
            result.append(unindent(12, f'''\
            def identifiers(*paths: Path) -> Iterator[str]:
                for item_path in paths:
                    result = item_path.as_posix()'''))
            result.append(indent(8,
                make_value_processing('result', model.identifier.processing) +
                '\nyield result\n'
            ))
        elif isinstance(model.identifier, JpathKeyIdentifierDef):
            json_path = to_jpath(model.identifier.path)
            result.append(unindent(12, f'''\
            def identifiers(*objects: Json) -> Iterator[str]:
                for obj in objects:
                    identifier = get_jpath_single(obj, {json_path})
                    if identifier is not None and isinstance(identifier.key, str):
                        result = identifier.key'''))
            result.append(indent(12,
                make_value_processing('result', model.identifier.processing) +
                '\nyield result\n'
            ))
        elif isinstance(model.identifier, JpathValueIdentifierDef):
            json_path = to_jpath(model.identifier.path)
            result.append(unindent(12, f'''\
            def identifiers(*objects: Json) -> Iterator[str]:
                for obj in objects:
                    identifier = get_jpath_single(obj, {json_path})
                    if identifier is not None and isinstance(identifier.value, str):
                        result = identifier.value'''))
            result.append(indent(12,
                make_value_processing('result', model.identifier.processing) +
                '\nyield result\n'
            ))
        self.files[target_path].append('\n'.join(result))

    def properties_search__reference(
            self, property: ReferenceDef,  parent_names: List[str],
            model: RootDef, target_path: str):
        func_name = '__'.join(parent_names[1:])
        result: List[str] = []
        result.append(f'def {func_name}(*objects: Json) -> Iterator[str]:')
        for access_path in property.access_paths:
            if isinstance(access_path, AccessPathKeyDef):
                if access_path.multi:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                            if isinstance(ref.key, str):
                                result = ref.key
                    '''))
                    result.append(indent(16,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
                else:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                        if ref is not None and isinstance(ref.key, str):
                            result = ref.key
                    '''))
                    result.append(indent(12,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
            elif isinstance(access_path, AccessPathValueDef):
                if access_path.multi:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                            if isinstance(ref.value, str):
                                result = ref.value
                    '''))
                    result.append(indent(16,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
                else:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                        if ref is not None and isinstance(ref.value, str):
                            result = ref.value
                    '''))
                    result.append(indent(12,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
        self.files[target_path].append('\n'.join(result))

    def properties_search__alias_reference(
            self, property: AliasReferenceDef,  parent_names: List[str],
            model: RootDef, target_path: str):
        func_name = '__'.join(parent_names[1:])
        result: List[str] = []
        result.append(f'def {func_name}(*objects: Json) -> Iterator[str]:')
        for access_path in property.access_paths:
            if isinstance(access_path, AccessPathKeyDef):
                if access_path.multi:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                            if isinstance(ref.key, str):
                                result = ref.key'''))
                    result.append(indent(16,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
                else:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                        if ref is not None and isinstance(ref.key, str):
                            result = ref.key'''))
                    result.append(indent(12,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
            elif isinstance(access_path, AccessPathValueDef):
                if access_path.multi:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                            if isinstance(ref.value, str):
                                result = ref.value'''))
                    result.append(indent(16,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
                else:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                        if isinstance(ref.value, str):
                            result = ref.value'''))
                    result.append(indent(12,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
        self.files[target_path].append('\n'.join(result))

    def properties_search__alias_mapping(
            self, property: AliasMappingDef,  parent_names: List[str],
            model: RootDef, target_path: str):
        func_name = '__'.join(parent_names[1:])
        result: List[str] = []
        result.append(
            f'def {func_name}(*objects: Json) -> Iterator[Tuple[str, str]]:')
        for access_path in property.access_paths:
            if access_path.multi:
                result.append(unindent(12, f'''\
                for obj in objects:
                    for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                        if isinstance(ref.key, str) and isinstance(ref.value, str):'''))
                result.append(indent(16,
                    make_value_processing('ref.key', access_path.key_processing)
                ))
                result.append(indent(16,
                    make_value_processing('ref.value', access_path.value_processing) +
                    '\nyield ref.key, ref.value\n'
                ))
            else:
                result.append(unindent(12, f'''\
                for obj in objects:
                    ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                    if ref is not None and isinstance(ref.key, str) and isinstance(ref.value, str):'''))
                result.append(indent(16,
                    make_value_processing('ref.key', access_path.key_processing)
                ))
                result.append(indent(16,
                    make_value_processing('ref.value', access_path.value_processing) +
                    '\nyield ref.key, ref.value\n'
                ))
        self.files[target_path].append('\n'.join(result))

    def properties_search__custom_value(
            self, property: CustomValueDef,  parent_names: List[str],
            model: RootDef, target_path: str):
        func_name = '__'.join(parent_names[1:])
        result: List[str] = []
        result.append(f'def {func_name}(*objects: Json):')
        for access_path in property.access_paths:
            if isinstance(access_path, AccessPathKeyDef):
                if access_path.multi:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                            if isinstance(ref.key, str):
                                result = ref.key'''))
                    result.append(indent(16,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
                else:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                        if ref is not None and isinstance(ref.key, str):
                            result = ref.key'''))
                    result.append(indent(12,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
            elif isinstance(access_path, AccessPathValueDef):
                if access_path.multi:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        for ref in get_jpath_multi(obj, {to_jpath(access_path.path)}):
                            if isinstance(ref.value, str):
                                result = ref.value'''))
                    result.append(indent(16,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
                else:
                    result.append(unindent(16, f'''\
                    for obj in objects:
                        ref = get_jpath_single(obj, {to_jpath(access_path.path)})
                        if isinstance(ref.value, str):
                            result = ref.value'''))
                    result.append(indent(12,
                        make_value_processing('result', access_path.processing) +
                        '\nyield result\n'
                    ))
        self.files[target_path].append('\n'.join(result))

# MAIN
def main():
    file_header = unindent(4, '''\
    # AUTOGENERATED! DON'T EDIT!
    from .jpath import *
    ''')

    models_path = Path('../models')
    models: List[RootDef] = load_models(models_path)

    generator = PyIteratorsGenerator()
    generator.generate(models)
    for k, v in generator.files.items():
        k = Path('python/src/bedrock_example') / k
        k.parent.mkdir(exist_ok=True, parents=True)
        text = '\n\n'.join([file_header] + v)

        # Very inefficient way of removing trailing spaces
        striptext = []
        for i in text.split('\n'):
            striptext.append(i.rstrip())
        text = '\n'.join(striptext)
        with k.open('w') as f:
            f.write(text)

if __name__ == '__main__':
    main()
