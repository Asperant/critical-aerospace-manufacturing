"""Safe embedded YAML reader retaining duplicate record identities and source spans."""
import re
import yaml

from ..provenance import SourceRef


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def records(text, path, start_title, end_title):
    start = text.index(start_title)
    end = text.index(end_title, start)
    region = text[start:end]
    for fence in re.finditer(r"^```yaml\n(.*?)^```", region, re.M | re.S):
        raw = fence[1]
        data = yaml.load(raw, Loader=UniqueLoader)
        if not isinstance(data, dict):
            raise ValueError("Expected YAML record mapping")
        marks = list(re.finditer(r"^([^\s:]+):", raw, re.M))
        if {m[1] for m in marks} != set(data):
            raise ValueError("Unsupported YAML top-level record syntax")
        for i, mark in enumerate(marks):
            stop = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
            absolute = start + fence.start(1) + mark.start()
            line = text[:absolute].count("\n") + 1
            context = raw[mark.start():stop].rstrip()
            ref = SourceRef(path=path, heading=mark[1], line_start=line,
                            line_end=line + len(context.splitlines()) - 1, raw_context=context)
            yield mark[1], data[mark[1]], ref
