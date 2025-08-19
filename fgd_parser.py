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
        """
        Parses a .fgd file from the given path into an FGDFile object.
        """
        self.fgd_file = FGDFile()
        self.lines = []
        self.current_line_idx = 0

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Pre-process content to handle descriptions split by '+'
                content = re.sub(r'"\s*\+\s*\n\s*"', '', content)
                
                # FIX 1 (Retained): Handle stacked closing brackets.
                content = content.replace(']]', ']\n]')
                
                self.lines = content.splitlines()
        except Exception as e:
            raise IOError(f"Could not read file at {filepath}: {e}")

        while self.current_line_idx < len(self.lines):
            line = self._get_next_meaningful_line()
            if not line:
                break

            if line.lower().startswith('@'):
                self._parse_directive(line)
            else:
                print(f"Warning: Unrecognized top-level line (skipped): {line}")
        
        return self.fgd_file

    def _peek_next_meaningful_line(self):
        """
        Looks at the next non-comment, non-empty line without advancing the parser.
        """
        idx = self.current_line_idx
        while idx < len(self.lines):
            line = self.lines[idx].strip()
            if line and not line.startswith('//'):
                return line
            idx += 1
        return None

    def _get_next_meaningful_line(self):
        """
        Gets the next non-comment, non-empty line and advances the parser.
        """
        while self.current_line_idx < len(self.lines):
            line = self.lines[self.current_line_idx].strip()
            self.current_line_idx += 1
            if line and not line.startswith('//'):
                return line
        return None

    def _parse_directive(self, line: str):
        """
        Routes a directive line (starting with '@') to the correct parsing function.
        """
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
        if self._peek_next_meaningful_line() == '[':
            self._get_next_meaningful_line() # Consume '['
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
        if self._peek_next_meaningful_line() != '[': return content
        self._get_next_meaningful_line() # Consume '['
        
        while self._peek_next_meaningful_line() != ']':
            line = self._get_next_meaningful_line()
            if not line: break
            child_name_match = re.search(r'"([^"]+)"', line)
            if not child_name_match: continue
            child_name = child_name_match.group(1)
            
            if self._peek_next_meaningful_line() == '[':
                content.append(AutoVisGroup(child_name, self._parse_autovisgroup_block()))
            else:
                content.append(child_name)
        self._get_next_meaningful_line() # Consume ']'
        return content

    def _parse_entity_class(self, first_line: str):
        """
        Parses a complete entity class definition, robustly handling multi-line headers.
        """
        header_lines = [first_line]
        body_started = '[' in first_line
        
        if not body_started:
            while self.current_line_idx < len(self.lines):
                next_line = self.lines[self.current_line_idx]
                if next_line.strip().startswith('['): break
                header_lines.append(next_line)
                self.current_line_idx += 1
                if '[' in next_line:
                    body_started = True
                    break

        full_header_text = "\n".join(header_lines)
        body_start_index = full_header_text.find('[')
        header_text = full_header_text
        body_remainder = None
        if body_start_index != -1:
            header_text = full_header_text[:body_start_index]
            body_remainder = full_header_text[body_start_index + 1:].strip()
        
        # NEW FIX: Robustly find the top-level '=' separator, ignoring '=' inside helpers.
        paren_level = 0
        brace_level = 0
        equals_index = -1
        for i, char in enumerate(header_text):
            if char == '(': paren_level += 1
            elif char == ')': paren_level -= 1
            elif char == '{': brace_level += 1
            elif char == '}': brace_level -= 1
            elif char == '=' and paren_level == 0 and brace_level == 0:
                equals_index = i
                break

        if equals_index == -1:
            print(f"Error: Malformed entity directive (no top-level '=' found): {first_line}")
            return

        before_equals = header_text[:equals_index]
        after_equals = header_text[equals_index + 1:]

        name_and_desc_match = re.search(r'^\s*([a-zA-Z0-9_]+)\s*(?::\s*"((?:.|\n)*)")?\s*$', after_equals.strip(), re.DOTALL)
        if not name_and_desc_match:
            print(f"Error: Malformed entity directive (no name found after '='): {first_line}")
            return
        name, description = name_and_desc_match.groups()
        description = description.strip().replace('\\"', '"') if description else ""
        
        class_match = re.match(r'@(\w+)\s*(.*)', before_equals.strip(), re.DOTALL | re.IGNORECASE)
        if not class_match:
            print(f"Error: Malformed entity directive (no class type found): {first_line}")
            return
            
        class_type_raw, helpers_str = class_match.groups()
        
        base_name = class_type_raw
        if base_name.lower().endswith('class'):
            base_name = base_name[:-5]
        class_type = base_name.capitalize() + "Class"

        helpers, base_classes = self._parse_helpers_and_bases(helpers_str)

        new_entity = EntityClass(name=name, class_type=class_type, description=description, base_classes=base_classes, helpers=helpers)
        self.fgd_file.add_element(new_entity)

        if body_remainder and body_remainder.strip() == ']':
            return
        
        if body_started or self._peek_next_meaningful_line() == '[':
            self._parse_entity_content(new_entity, body_remainder)
        
        # NEW FIX: After parsing an entity, check for and consume a stray ']' that might have
        # been left behind by our pre-processing of ']]' into ']\n]'.
        if self._peek_next_meaningful_line() == ']':
            self._get_next_meaningful_line()

    def _parse_helpers_and_bases(self, helper_str: str):
        """
        Parses helper functions, now with support for nested curly braces.
        """
        helpers, base_classes = {}, []
        cursor = 0
        while cursor < len(helper_str):
            match = re.search(r'\b([a-zA-Z0-9_]+)\s*\(', helper_str[cursor:])
            if not match: break
            
            key = match.group(1).lower()
            start_paren = cursor + match.end()
            
            paren_level = 1
            brace_level = 0
            end_pos = start_paren
            
            while end_pos < len(helper_str):
                char = helper_str[end_pos]
                if char == '(': paren_level += 1
                elif char == ')': paren_level -= 1
                elif char == '{': brace_level += 1
                elif char == '}': brace_level -= 1
                
                if paren_level == 0 and brace_level == 0: break
                end_pos += 1
            
            if paren_level == 0 and brace_level == 0:
                args = helper_str[start_paren:end_pos].strip()
                if key == 'base':
                    base_classes.extend([b.strip() for b in args.split(',') if b.strip()])
                else:
                    helpers[key] = args
                cursor = end_pos + 1
            else:
                cursor += 1 
        return helpers, base_classes

    def _parse_entity_content(self, entity: EntityClass, remainder: str | None):
        """
        Parses the body of an entity, now with logic for compact, non-empty bodies.
        """
        if remainder and remainder.strip():
            rem = remainder.strip()
            if rem.endswith(']'):
                content_on_line = rem[:-1].strip()
                if content_on_line:
                    self._parse_entity_line(entity, content_on_line)
                return
            else:
                self._parse_entity_line(entity, rem)

        if self._peek_next_meaningful_line() == '[':
            self._get_next_meaningful_line()

        while self._peek_next_meaningful_line() not in (']', None):
            line = self._get_next_meaningful_line()
            if line:
                self._parse_entity_line(entity, line)
        
        if self._peek_next_meaningful_line() == ']':
            self._get_next_meaningful_line()

    def _parse_entity_line(self, entity: EntityClass, line: str):
        """
        Parses a single line within an entity's content block (a property, input, or output).
        """
        line = line.strip()
        if not line: return

        io_match = re.match(r'^\s*(input|output)\s+([^\s(]+)\s*\(([^)]*)\)\s*(?::\s*"((?:[^"]|\\")*)")?', line, re.IGNORECASE)
        if io_match:
            io_type, io_name, arg_type, io_desc = io_match.groups()
            entity.add_io(IO(io_type.lower(), io_name, arg_type, io_desc.replace('\\"', '"') if io_desc else ""))
            return

        prop_match = re.match(r'^\s*([\w."]+)\s*\(([^)]+)\)\s*(readonly)?\s*(report)?\s*(.*)', line, re.IGNORECASE)
        if prop_match:
            prop_name, prop_type_raw, readonly, report, rest_of_line = prop_match.groups()
            is_block = rest_of_line.strip().endswith('=') or self._peek_next_meaningful_line() == '['
            
            display_name, default_value, description = self._extract_prop_details(rest_of_line)
            prop_type_base = prop_type_raw.split(',')[0].strip().lower()
            prop = None
            
            if prop_type_base == 'choices':
                prop = ChoicesProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
                if is_block: self._parse_choices_or_flags_block(prop, self._parse_choice_item)
            elif prop_type_base == 'flags':
                prop = FlagsProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
                if is_block: self._parse_choices_or_flags_block(prop, self._parse_flag_item)
            else:
                prop = KeyvalueProperty(prop_name, prop_type_raw, display_name, default_value, description, readonly=bool(readonly), report=bool(report))
            
            if prop: entity.properties.append(prop)
            return
        
        print(f"Warning: Unrecognized line in entity content (skipped): {line}")
    
    def _extract_prop_details(self, s: str):
        """
        Extracts the display name, default value, and description from the end of a property line.
        """
        s = s.strip()
        if s.endswith('='): s = s[:-1].strip()
        
        parts = re.findall(r'"(?:\\.|[^"\\])*"|\S+', s)
        
        cleaned_parts = []
        for part in parts:
            part = part.strip()
            if part == ':': continue
            if (part.startswith('"') and part.endswith('"')) or \
               (part.startswith("'") and part.endswith("'")):
                cleaned_parts.append(part[1:-1].replace('\\"', '"'))
            else:
                cleaned_parts.append(part)

        return (cleaned_parts + ["", "", ""])[:3]

    def _parse_choices_or_flags_block(self, prop, item_parser_func):
        """
        Generic, safer parser for a block of items (like choices or flags) enclosed in [...].
        """
        if self._peek_next_meaningful_line() != '[':
             print(f"Warning: Expected block '[' for property '{prop.name}', but not found.")
             return
        self._get_next_meaningful_line() # Consume '['
        
        while True:
            next_line = self._peek_next_meaningful_line()
            if next_line is None or next_line == ']':
                break
            item_parser_func(self._get_next_meaningful_line(), prop)
        
        if self._peek_next_meaningful_line() == ']':
            self._get_next_meaningful_line() # Consume ']'
            
    def _parse_choice_item(self, line, prop: ChoicesProperty):
        choice_match = re.match(r'^\s*("?[^"]+"?)\s*:\s*"([^"]+)"(?:\s*:\s*"((?:[^"]|\\")*)")?', line.strip())
        if choice_match:
            value, display_name, description = choice_match.groups()
            prop.choices.append(ChoiceItem(value.strip('"'), display_name, description.replace('\\"', '"') if description else ""))
        else:
            print(f"Warning: Unrecognized line in choices block (skipped): {line}")

    def _parse_flag_item(self, line, prop: FlagsProperty):
        flag_match = re.match(r'^\s*(-?\d+)\s*:\s*"([^"]+)"(?:\s*:\s*(\d))?(?:\s*:\s*"((?:[^"]|\\")*)")?', line.strip())
        if flag_match:
            value, display_name, ticked, description = flag_match.groups()
            ticked_bool = bool(int(ticked)) if ticked is not None else False
            prop.flags.append(FlagItem(int(value), display_name, description.replace('\\"', '"') if description else "", ticked_bool))
        else:
            print(f"Warning: Unrecognized line in flags block (skipped): {line}")