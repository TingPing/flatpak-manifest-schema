#!/usr/bin/env python3

import re
import json
import xmltodict
from pprint import pprint

with open('flatpak-manifest.xml', 'rb') as f:
    d = xmltodict.parse(f)

schema = {
    'title': 'Flatpak Builder Manifest',
    'definitions': {},
    'type': 'object',
    'oneOf': [
        {
            'required': ['app-id']
        },
        {
            'required': ['id']
        }
    ]
}


def entry_to_desc(entry) -> str:
    if not isinstance(entry, str):
        entry_str = ''
        for item in entry:
            if isinstance(item, str):
                entry_str += item + ' '
            elif isinstance(item, dict):
                # FIXME: <command>foo</command> is stripped from the text
                #        and its not clear how to recombine them.
                entry_str += item['#text'] + ' '
            else:
                assert(False)
        entry = entry_str.rstrip()
    return re.sub(r'\s(\s+)', r' ', entry).replace(' #text', '')


def extract_item_types(text: str) -> [str]:
    # This will never be perfect but is close enough
    words = text.rstrip(')').split(' ')[2:]
    if len(words) is 1:
        return words[0].rstrip('s')
    return [word.rstrip('s') for word in words if word != 'or']


def handle_property(name: str, variable_info: dict, entry_dict: dict):
    if name == 'type':  # Sources type property doesn't have a type
        type_text = 'string'
    else:
        type_text = var['term']['#text'].strip()

    if name == 'sources':  # Modules sources property
        variable_info['type'] = 'array'
        variable_info['items'] = {
            'anyOf': [
                {'type': 'string'},
                {'$ref': '#/definitions/archive-source'},
                {'$ref': '#/definitions/git-source'},
                {'$ref': '#/definitions/bzr-source'},
                {'$ref': '#/definitions/svn-source'},
                {'$ref': '#/definitions/file-source'},
                {'$ref': '#/definitions/directory-source'},
                {'$ref': '#/definitions/script-source'},
                {'$ref': '#/definitions/shell-source'},
                {'$ref': '#/definitions/patch-source'},
                {'$ref': '#/definitions/extra-data-source'},
            ]
        }
    elif name == 'modules':  # Module/toplevel property
        variable_info['type'] = 'array'
        variable_info['items'] = {
            'anyOf': [
                {'type': 'string'},
                {'$ref': '#/definitions/module'},
            ]
        }
    elif name == 'type':  # Sources property
        variable_info['type'] = 'string'
        variable_info['enum'] = [
            'archive', 'git', 'bzr', 'svn', 'dir', 'file', 'script', 'shell', 'patch', 'extra-data'
        ]
    elif name == 'buildsystem':  # Sources property
        variable_info['type'] = 'string'
        variable_info['enum'] = [
            'autotools', 'cmake', 'cmake-ninja', 'meson', 'simple', 'qmake'
        ]
        variable_info['default'] = 'autotools'
    elif type_text.startswith('(array'):
        variable_info['type'] = 'array'
        variable_info['items'] = {'type': extract_item_types(type_text)}
    else:
        variable_info['type'] = type_text.rpartition(' ')[2].strip('()')

    if name == 'build-options':
        del variable_info['type']
        variable_info['$ref'] = '#/definitions/build-options'

    variable_info['description'] = entry_to_desc(var['listitem']['para'])
    entry_dict[name] = variable_info

entries = d['refentry']['refsect1'][1]['refsect2']
for entry in entries:
    # pprint(entry)
    entry_props = {}

    variables = entry.get('variablelist', {}).get('varlistentry', [])
    for var in variables:
        # pprint(var)
        variable_info = {}

        name = var['term']['option']
        if isinstance(name, list):  # app-id/id are shared
            for n in name:
                handle_property(n, variable_info, entry_props)
        else:
            handle_property(name, variable_info, entry_props)

    if 'refsect3' in entry:
        all_source_variables = entry['refsect3'][0]['variablelist']['varlistentry']
        for source in entry['refsect3'][1:]:
            title = source['title']
            if title.endswith(' (tar, zip)'):
                title = title[:-11]
            variables = source['variablelist']['varlistentry']

            for var in all_source_variables + variables:
                # pprint(var)
                variable_info = {}
                name = var['term']['option']
                handle_property(name, variable_info, entry_props)
            # pprint(source)

            schema['definitions'][title.lower().replace(' ', '-').rstrip('s')] = {
                'type': 'object',
                'required': ['type'],
                'properties': entry_props
            }
    else:
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
