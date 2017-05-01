#!/usr/bin/env python3

import xmltodict
import json
from pprint import pprint

with open('flatpak-manifest.xml', 'rb') as f:
    d = xmltodict.parse(f)

schema = {
    'title': 'Flatpak Builder Manifest',
    'definitions': {},
    'type': 'object',
}


def text_to_type(text: str) -> str:
    if text.startswith('(array'):
        return 'array'
    return text.rpartition(' ')[2].strip('()')


def entry_to_desc(entry) -> str:
    if not isinstance(entry, str):
        return r'\n'.join(entry)  # FIXME
    return entry


entries = d['refentry']['refsect1'][1]['refsect2']
for entry in entries:
    # pprint(entry)
    entry_props = {}

    variables = entry.get('variablelist', {}).get('varlistentry', [])
    for var in variables:
        # pprint(var)
        variable_info = {
            'type': text_to_type(var['term']['#text']),
            'description': entry_to_desc(var['listitem']['para']),
        }

        # pprint(var['listitem']['para'])

        name = var['term']['option']
        if isinstance(name, list):
            name = name[0]  # app-id/id are shared

        if name == 'build-options':
            del variable_info['type']
            variable_info['$ref'] = '#/definitions/build-options'

        entry_props[name] = variable_info

    if 'refsect3' in entry:
        pass # TODO: Sources

    title = entry['title']
    if title == 'Toplevel properties':
        schema['properties'] = entry_props
    else:
        schema['definitions'][title.lower().replace(' ', '-')] = {
            'type': 'object',
            'properties': entry_props
        }

with open('flatpak-manifest.schema', 'w') as f:
    json.dump(schema, f, indent=2)
# pprint(schema, width=200)
