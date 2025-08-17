# fgd_parser.py

import re
from fgd_model import (
    FGDFile, EntityClass, KeyvalueProperty, ChoicesProperty, FlagsProperty, 
    IO, ChoiceItem, FlagItem, IncludeDirective, Property, MapSize, Version, 
    MaterialExclusion, AutoVisGroup
)

class FGDParser:
    def __init__(self):
        self.fgd_file = FGDFile()
        self.lines = []
        self.current_line_idx = 0

    def parse_fgd_file(self, filepath: str) -> FGDFile:
        self.fgd_file = FGDFile()
        self.lines = []
        self.current_line_idx = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()

        while self.current_line_idx < len(self.lines):
            line = self._get_next_meaningful_line()
            if not line:
                break

            if line.lower().startswith('@'):
                self._parse_directive(line)
            else:
                print(f"Warning: Unrecognized top-level line (skipped): {line}")
        return self.fgd_file

    def _get_next_meaningful_line(self):
        while self.current_line_idx < len(self.lines):
            line = self.lines[self.current_line_idx].strip()
            self.current_line_idx += 1
            if line and not line.startswith('//'):
                return line
        return None

    def _parse_directive(self, line: str):
        line_lower = line.lower()
        if line_lower.startswith('@include'):
            self._parse_include(line)
        elif line_lower.startswith('@mapsize'):
            self._parse_mapsize(line)
        elif line_lower.startswith('@version'):
            self._parse_version(line)
        elif line_lower.startswith('@materialexclusion'):
            self._parse_material_exclusion()
        elif line_lower.startswith('@autovisgroup'):
            self._parse_autovisgroup(line)
        elif line_lower.startswith(('@pointclass', '@solidclass', '@baseclass', '@npcclass', '@keyframeclass', '@moveclass', '@filterclass', '@extendclass')):
            self._parse_entity_class(line)
        else:
            print(f"Warning: Unknown directive: {line}")

    def _parse_include(self, line: str):
        match = re.match(r'@include\s+"([^"]+)"', line, re.IGNORECASE)
        if match:
            self.fgd_file.add_element(IncludeDirective(match.group(1)))
            
    def _parse_mapsize(self, line: str):
        match = re.search(r'@mapsize\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', line, re.IGNORECASE)
        if match:
            self.fgd_file.add_element(MapSize(int(match.group(1)), int(match.group(2))))

    def _parse_version(self, line: str):
        match = re.search(r'@version\s*\((\d+)\)', line, re.IGNORECASE)
        if match:
            self.fgd_file.add_element(Version(int(match.group(1))))
            
    def _parse_material_exclusion(self):
        paths = []
        if self._get_next_meaningful_line() == '[':
            while True:
                line = self._get_next_meaningful_line()
                if not line or line == ']': break
                match = re.search(r'"([^"]+)"', line)
                if match: paths.append(match.group(1))
            self.fgd_file.add_element(MaterialExclusion(paths))

    def _parse_autovisgroup(self, line: str):
        match = re.search(r'@autovisgroup\s*=\s*"([^"]+)"', line, re.IGNORECASE)
        if match:
            parent_name = match.group(1)
            children = self._parse_autovisgroup_block()
            self.fgd_file.add_element(AutoVisGroup(parent_name, children))

    def _parse_autovisgroup_block(self):
        content = []
        if self._get_next_meaningful_line() != '[':
            self.current_line_idx -= 1
            return content
        
        while True:
            line = self._get_next_meaningful_line()
            if not line or line == ']': break
            
            peek_line = self._get_next_meaningful_line()
            self.current_line_idx -= 1 
            
            child_name_match = re.search(r'"([^"]+)"', line)
            if not child_name_match: continue
            child_name = child_name_match.group(1)
            
            if peek_line == '[':
                sub_group_children = self._parse_autovisgroup_block()
                content.append(AutoVisGroup(child_name, sub_group_children))
            else:
                content.append(child_name)
        return content


    def _parse_entity_class(self, first_line: str):
        entity_match = re.match(r'@(\w+)\s*'
                                r'((?:[a-zA-Z]+\(.*\)\s*)*)' 
                                r'\s*=\s*([a-zA-Z0-9_]+)\s*'
                                r'(?::\s*"((?:[^"]|\\")*)")?', first_line, re.IGNORECASE)

        if not entity_match:
            print(f"Error: Malformed entity directive: {first_line}")
            return

        class_type_raw, helpers_str, name, description = entity_match.groups()
        
        # --- THIS IS THE FIX ---
        # This logic correctly formats the class type (e.g., "pointclass" -> "PointClass")
        # without duplicating the "Class" suffix.
        class_type = class_type_raw
        if class_type.lower().endswith('class'):
            class_type = class_type[:-5].capitalize() + 'Class'
        else:
            class_type = class_type.capitalize()
        # --- END OF FIX ---

        description = description.replace('\\"', '"') if description else ""
        
        helpers, base_classes = self._parse_helpers_and_bases(helpers_str)

        new_entity = EntityClass(name=name, class_type=class_type, description=description, base_classes=base_classes, helpers=helpers)
        self.fgd_file.add_element(new_entity)

        self._parse_entity_content(new_entity)

    def _parse_helpers_and_bases(self, line: str):
        helpers = {}
        base_classes = []
        pattern = re.compile(r'(\w+)\s*\(((?:[^()]|\([^)]*\))*)\)', re.IGNORECASE)
        
        for match in pattern.finditer(line):
            key, args = match.groups()
            key_lower = key.lower()

            if key_lower == 'base':
                bases = [b.strip() for b in args.split(',')]
                base_classes.extend(bases)
            else:
                helpers[key_lower] = args

        return helpers, base_classes

    def _parse_entity_content(self, entity: EntityClass):
        line = self._get_next_meaningful_line()
        if line != '[':
            self.current_line_idx -= 1
        
        while True:
            line = self._get_next_meaningful_line()
            if not line or line == ']':
                break
            
            if line.lower().startswith('@'):
                self.current_line_idx -= 1
                break

            io_match = re.match(r'(input|output)\s+([^\s(]+)\s*\(([^)]*)\)\s*(?::\s*"((?:[^"]|\\")*)")?', line, re.IGNORECASE)
            if io_match:
                io_type, io_name, arg_type, io_desc = io_match.groups()
                entity.add_io(IO(io_type.lower(), io_name, arg_type, io_desc.replace('\\"', '"') if io_desc else ""))
                continue

            prop_match = re.match(r'(\w+)\s*\(([^)]+)\)\s*(readonly)?\s*(report)?\s*(.*)', line, re.IGNORECASE)
            if prop_match:
                prop_name, prop_type_raw, readonly, report, rest_of_line = prop_match.groups()
                display_name, default_value, description = self._extract_prop_details(rest_of_line)
                prop_type_base = prop_type_raw.split(',')[0].strip().lower()

                if line.strip().startswith("spawnflags(flags)"):
                    prop = FlagsProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
                    self._parse_flags_block(prop)
                elif prop_type_base == 'choices':
                    prop = ChoicesProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
                    self._parse_choices_block(prop)
                elif prop_type_base == 'flags':
                    prop = FlagsProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
                    self._parse_flags_block(prop)
                else:
                    prop = KeyvalueProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
                entity.properties.append(prop)
                continue
            
            print(f"Warning: Unrecognized line in entity content (skipped): {line}")
    
    def _extract_prop_details(self, s: str):
        s = s.strip()
        if s.startswith('='):
            s = ""
        if s.startswith(':'): s = s[1:].strip()
        
        parts = []
        in_quotes = False
        current_part = ""
        
        for char in s:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ':' and not in_quotes and current_part.strip():
                parts.append(current_part.strip())
                current_part = ""
                continue
            current_part += char
        if current_part.strip():
            parts.append(current_part.strip())

        def clean_part(p):
            p = p.strip()
            if p.startswith('"') and p.endswith('"'):
                return p[1:-1].replace('\\"', '"')
            return p

        details = [clean_part(p) for p in parts]
        
        display_name = details[0] if len(details) > 0 else ""
        default_value = details[1] if len(details) > 1 else ""
        description = details[2] if len(details) > 2 else ""
        return display_name, default_value, description

    def _parse_choices_block(self, prop: ChoicesProperty):
        line = self._get_next_meaningful_line()
        if line and line.strip().endswith('='):
            line = self._get_next_meaningful_line()

        if line != '[': self.current_line_idx -= 1
        
        while True:
            line = self._get_next_meaningful_line()
            if not line or line == ']': break
            
            choice_match = re.match(r'("?[^"]+"?)\s*:\s*"([^"]+)"(?:\s*:\s*"((?:[^"]|\\")*)")?', line.strip())
            if choice_match:
                value, display_name, description = choice_match.groups()
                value = value.strip('"')
                prop.choices.append(ChoiceItem(value, display_name, description.replace('\\"', '"') if description else ""))
            else:
                print(f"Warning: Unrecognized line in choices block (skipped): {line}")

    def _parse_flags_block(self, prop: FlagsProperty):
        line = self._get_next_meaningful_line()
        if line and line.strip().endswith('='):
            line = self._get_next_meaningful_line()

        if line != '[': self.current_line_idx -= 1

        while True:
            line = self._get_next_meaningful_line()
            if not line or line == ']': break
            
            flag_match = re.match(r'(-?\d+)\s*:\s*"([^"]+)"\s*:\s*(\d)(?:\s*:\s*"((?:[^"]|\\")*)")?', line.strip())
            if flag_match:
                value, display_name, ticked, description = flag_match.groups()
                prop.flags.append(FlagItem(int(value), display_name, description.replace('\\"', '"') if description else "", bool(int(ticked))))
            else:
                print(f"Warning: Unrecognized line in flags block (skipped): {line}")
