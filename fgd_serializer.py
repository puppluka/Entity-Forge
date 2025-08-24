# fgd_serializer.py

import re
import fgd_model

class FGDSerializer:
    """Serializes an FGDFile object into a formatted FGD text string."""

    def serialize_fgd(self, fgd_file: fgd_model.FGDFile) -> str:
        """Converts an FGDFile object into a complete FGD string."""
        lines = []
        for element in fgd_file.elements:
            if isinstance(element, fgd_model.IncludeDirective):
                lines.append(self._serialize_include_directive(element))
            elif isinstance(element, fgd_model.MapSize):
                lines.append(self._serialize_mapsize(element))
            elif isinstance(element, fgd_model.Version):
                lines.append(self._serialize_version(element))
            elif isinstance(element, fgd_model.MaterialExclusion):
                lines.append(self._serialize_material_exclusion(element))
            elif isinstance(element, fgd_model.AutoVisGroup):
                lines.append(self._serialize_autovisgroup(element))
            elif isinstance(element, fgd_model.EntityClass):
                lines.append(self._serialize_entity_class(element))
            lines.append("") # Blank line between top-level elements
        return "\n".join(lines)

    def _serialize_include_directive(self, include_dir: fgd_model.IncludeDirective) -> str:
        return f'@include "{include_dir.file_path}"'
        
    def _serialize_mapsize(self, map_size: fgd_model.MapSize) -> str:
        return f'@mapsize({map_size.min_coord}, {map_size.max_coord})'

    def _serialize_version(self, version: fgd_model.Version) -> str:
        return f'@version({version.version_number})'

    def _serialize_material_exclusion(self, mat_ex: fgd_model.MaterialExclusion) -> str:
        lines = ["@MaterialExclusion", "["]
        for path in mat_ex.excluded_paths:
            lines.append(f'    "{path}"')
        lines.append("]")
        return "\n".join(lines)

    def _serialize_autovisgroup(self, group: fgd_model.AutoVisGroup, indent_level=0) -> str:
        indent = "    " * indent_level
        lines = [f'{indent}@AutoVisGroup = "{group.parent_name}"', f"{indent}["]
        for child in group.children:
            if isinstance(child, fgd_model.AutoVisGroup):
                # This is a nested subgroup
                lines.append(self._serialize_autovisgroup_child(child, indent_level + 1))
            else:
                # This is an entity class name
                lines.append(f'{indent}    "{child}"')
        lines.append(f"{indent}]")
        return "\n".join(lines)
    
    def _serialize_autovisgroup_child(self, group: fgd_model.AutoVisGroup, indent_level: int) -> str:
        indent = "    " * indent_level
        lines = [f'{indent}"{group.parent_name}"', f"{indent}["]
        for entity_name in group.children:
            lines.append(f'{indent}    "{entity_name}"')
        lines.append(f"{indent}]")
        return "\n".join(lines)

    def _serialize_entity_class(self, entity_class: fgd_model.EntityClass) -> str:
        class_lines = []
        
        # Header: @ClassType base(...) color(...) etc. = name : "description"
        header_parts = [f"@{entity_class.class_type}"]
        if entity_class.base_classes:
            header_parts.append(f"base({', '.join(entity_class.base_classes)})")
        
        # Serialize all helpers from the dictionary
        for key, args in entity_class.helpers.items():
            # Special handling for potentially multi-line model helper
            if '\n' in args:
                # Indent the multi-line arguments for readability
                indented_args = "\n".join([" " * 4 + line.strip() for line in args.strip().split('\n')])
                header_parts.append(f"{key}(\n{indented_args}\n)")
            else:
                header_parts.append(f"{key}({args})")
        
        # Escape quotes in description for serialization and handle multiline
        description = entity_class.description.replace('"', '\\"')
        
        header_line = " ".join(header_parts)
        header_line += f' = {entity_class.name}'

        if description:
            # Join multiline descriptions with the '+' character as per FGD spec for older tools
            if '\n' in description:
                description_lines = description.split('\n')
                formatted_desc = f'"{description_lines[0]} " +'
                for line in description_lines[1:]:
                    formatted_desc += f'\n    "{line.strip()} " +'
                header_line += f' : {formatted_desc.rstrip(" +")}'
            else:
                 header_line += f' : "{description}"'

        class_lines.append(header_line)
        class_lines.append("[")

        # Inputs, Outputs, and Properties
        for io in entity_class.inputs:
            class_lines.append(self._serialize_io(io, 1))
        for io in entity_class.outputs:
            class_lines.append(self._serialize_io(io, 1))
        for prop in entity_class.properties:
            class_lines.extend(self._serialize_property(prop, 1))

        class_lines.append("]")
        return "\n".join(class_lines)

    def _serialize_io(self, io_obj: fgd_model.IO, indent_level: int) -> str:
        indent = "    " * indent_level
        desc = io_obj.description.replace('"', '\\"')
        line = f'{indent}{io_obj.io_type} {io_obj.name}({io_obj.arg_type})'
        if desc:
            line += f' : "{desc}"'
        return line

    def _serialize_property(self, prop: fgd_model.Property, indent_level: int) -> list[str]:
        indent = "    " * indent_level
        prop_lines = []

        prop_header = f"{indent}{prop.name}({prop.prop_type})"
        if prop.readonly: prop_header += " readonly"
        if prop.report: prop_header += " report"

        # --- FIX ---
        # Logic to conditionally quote the default value based on property type.
        # Numeric/vector types should not be quoted. String types should be.
        # 'choices' is a special case that can have numeric or string defaults.
        non_quoted_types = {'integer', 'float', 'bool', 'angle', 'color255', 'vector', 'flags'}
        base_prop_type = prop.prop_type.split(',')[0].strip().lower()
        
        quote_default = True # Default to quoting
        if base_prop_type in non_quoted_types:
            quote_default = False
        # For 'choices', only quote if the value is not a plain number.
        elif base_prop_type == 'choices':
            if prop.default_value and re.match(r'^-?\d+(\.\d+)?$', prop.default_value):
                quote_default = False

        # Header: ... : "DisplayName" : "DefaultValue" : "Description"
        details = []
        # FGD format requires all preceding colons.
        if prop.description:
            display_str = f'"{prop.display_name}"'
            
            val_to_use = prop.default_value
            # For non-quoted types, if the value is empty, use "0" as a safe default
            # because an empty value is not valid for a number if a description is present.
            if not quote_default and not val_to_use:
                val_to_use = "0"
            
            default_val_str = f'"{val_to_use}"' if quote_default else str(val_to_use)
            desc_str = f'"{prop.description.replace("\"", "\\\"")}"'
            details = [display_str, default_val_str, desc_str]
        elif prop.default_value:
            display_str = f'"{prop.display_name}"'
            default_val_str = f'"{prop.default_value}"' if quote_default else str(prop.default_value)
            details = [display_str, default_val_str]
        elif prop.display_name:
            display_str = f'"{prop.display_name}"'
            details = [display_str]
        
        if details:
            prop_header += " : " + " : ".join(details)
        
        # --- (End of fix section) ---
        
        is_block_prop = (isinstance(prop, fgd_model.ChoicesProperty) and prop.choices) or \
                        (isinstance(prop, fgd_model.FlagsProperty) and prop.flags)
        
        if is_block_prop:
            prop_header += " ="

        prop_lines.append(prop_header)

        # Blocks for choices or flags
        if isinstance(prop, fgd_model.ChoicesProperty) and prop.choices:
            prop_lines.append(f"{indent}[")
            for choice in prop.choices:
                prop_lines.append(self._serialize_choice_item(choice, indent_level + 1))
            prop_lines.append(f"{indent}]")
        elif isinstance(prop, fgd_model.FlagsProperty) and prop.flags:
            prop_lines.append(f"{indent}[")
            for flag in prop.flags:
                prop_lines.append(self._serialize_flag_item(flag, indent_level + 1))
            prop_lines.append(f"{indent}]")
            
        return prop_lines

    def _serialize_choice_item(self, choice: fgd_model.ChoiceItem, indent_level: int) -> str:
        indent = "    " * indent_level
        
        # Quote value if it's not a plain number
        val_str = f'"{choice.value}"' if not re.match(r'^-?\d+(\.\d+)?$', choice.value) else choice.value

        line = f'{indent}{val_str} : "{choice.display_name}"'
        if choice.description:
            line += f' : "{choice.description.replace("\"", "\\\"")}"'
        return line

    def _serialize_flag_item(self, flag: fgd_model.FlagItem, indent_level: int) -> str:
        indent = "    " * indent_level
        line = f'{indent}{flag.value} : "{flag.display_name}" : {int(flag.default_ticked)}'
        if flag.description:
            line += f' : "{flag.description.replace("\"", "\\\"")}"'
        return line