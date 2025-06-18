# fgd_parser.py

import re
from fgd_model import FGDFile, EntityClass, KeyvalueProperty, ChoicesProperty, FlagsProperty, IO, ChoiceItem, FlagItem, IncludeDirective, Property

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
        elif line_lower.startswith(('@pointclass', '@solidclass', '@baseclass', '@npcclass', '@keyframeclass', '@moveclass', '@filterclass', '@extendclass')):
            self._parse_entity_class(line)
        else:
            print(f"Warning: Unknown directive: {line}")

    def _parse_include(self, line: str):
        match = re.match(r'@include\s+"([^"]+)"', line, re.IGNORECASE)
        if match:
            self.fgd_file.add_element(IncludeDirective(match.group(1)))

    def _parse_entity_class(self, first_line: str):
        entity_match = re.match(r'@(\w+)\s*'
                                r'((?:base\([^)]+\)\s*)*)'
                                r'((?:[a-zA-Z]+\([^)]*\)\s*)*)'
                                r'\s*=\s*([a-zA-Z0-9_]+)\s*'
                                r'(?::\s*"((?:[^"]|\\")*)")?', first_line, re.IGNORECASE)

        if not entity_match:
            print(f"Error: Malformed entity directive: {first_line}")
            return

        class_type_raw, bases_str, inline_attrs_str, name, description = entity_match.groups()
        
        # --- THIS IS THE FIX ---
        # The line below was incorrectly adding "Class" to the end.
        # It has been corrected to just capitalize the parsed type.
        class_type = class_type_raw.capitalize()
        # --- END OF FIX ---

        base_classes = re.findall(r'base\(([^)]+)\)', bases_str, re.IGNORECASE)
        base_classes = [b.strip() for bc in base_classes for b in bc.split(',')]

        description = description.replace('\\"', '"') if description else ""

        new_entity = EntityClass(name=name, class_type=class_type, description=description, base_classes=base_classes)
        self.fgd_file.add_element(new_entity)

        if inline_attrs_str:
            self._parse_inline_entity_attributes(new_entity, inline_attrs_str)

        self._parse_entity_content(new_entity)

    def _parse_inline_entity_attributes(self, entity: EntityClass, line: str):
        color_match = re.search(r'color\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)', line, re.IGNORECASE)
        if color_match:
            entity.color = tuple(map(int, color_match.groups()))

        size_match = re.search(r'size\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*,\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)', line, re.IGNORECASE)
        if size_match:
            entity.size = ((int(size_match.group(1)), int(size_match.group(2)), int(size_match.group(3))),
                           (int(size_match.group(4)), int(size_match.group(5)), int(size_match.group(6))))

        studio_match = re.search(r'studio\("([^"]+)"\)', line, re.IGNORECASE)
        if studio_match:
            entity.studio = studio_match.group(1)

        sprite_match = re.search(r'sprite\("([^"]+)"\)', line, re.IGNORECASE)
        if sprite_match:
            entity.sprite = sprite_match.group(1)

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

            io_match = re.match(r'(input|output)\s+"([^"]+)"\s*\(([^)]*)\)\s*(?::\s*"((?:[^"]|\\")*)")?', line, re.IGNORECASE)
            if io_match:
                io_type, io_name, arg_type, io_desc = io_match.groups()
                entity.add_io(IO(io_type.lower(), io_name, arg_type, io_desc if io_desc else ""))
                continue

            prop_match = re.match(r'(\w+)\s*\(([^)]+)\)\s*(.*)', line)
            if prop_match:
                prop_name, prop_type_raw, rest_of_line = prop_match.groups()
                display_name, default_value, description = self._extract_prop_details(rest_of_line)
                prop_type_base = prop_type_raw.split(',')[0].strip().lower()

                if prop_type_base == 'choices':
                    prop = ChoicesProperty(prop_name, prop_type_raw, display_name, default_value, description)
                    self._parse_choices_block(prop)
                elif prop_type_base == 'flags':
                    prop = FlagsProperty(prop_name, prop_type_raw, display_name, default_value, description)
                    self._parse_flags_block(prop)
                else:
                    prop = KeyvalueProperty(prop_name, prop_type_raw, display_name, default_value, description)
                entity.properties.append(prop)
                continue
            
            print(f"Warning: Unrecognized line in entity content (skipped): {line}")

    def _extract_prop_details(self, s: str):
        s = s.strip()
        if s.startswith(':'): s = s[1:].strip()
        
        parts = re.findall(r'"((?:[^"]|\\")*)"|([^:\s]+)', s)
        details = [p[0].replace('\\"', '"') if p[0] else p[1] for p in parts]
        
        display_name = details[0] if len(details) > 0 else ""
        default_value = details[1] if len(details) > 1 else ""
        description = details[2] if len(details) > 2 else ""
        return display_name, default_value, description

    def _parse_choices_block(self, prop: ChoicesProperty):
        line = self._get_next_meaningful_line()
        if line != '[': self.current_line_idx -= 1
        
        while True:
            line = self._get_next_meaningful_line()
            if not line or line == ']': break
            
            choice_match = re.match(r'"([^"]+)"\s*:\s*"([^"]+)"(?:\s*:\s*"([^"]*)")?', line)
            if choice_match:
                value, display_name, description = choice_match.groups()
                prop.choices.append(ChoiceItem(value, display_name, description if description else ""))
            else:
                print(f"Warning: Unrecognized line in choices block (skipped): {line}")

    def _parse_flags_block(self, prop: FlagsProperty):
        line = self._get_next_meaningful_line()
        if line != '[': self.current_line_idx -= 1

        while True:
            line = self._get_next_meaningful_line()
            if not line or line == ']': break
            
            flag_match = re.match(r'(\d+)\s*:\s*"([^"]+)"\s*:\s*(\d)', line)
            if flag_match:
                value, display_name, ticked = flag_match.groups()
                prop.flags.append(FlagItem(int(value), display_name, "", bool(int(ticked))))
            else:
                print(f"Warning: Unrecognized line in flags block (skipped): {line}")