# fgd_serializer.py

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
        
        # UPDATED: Serialize all helpers from the dictionary
        for key, args in entity_class.helpers.items():
            header_parts.append(f"{key}({args})")
        
        # Escape quotes in description for serialization
        description = entity_class.description.replace('"', '\\"')
        header_parts.append(f'= {entity_class.name}')
        if description:
            header_parts.append(f': "{description}"')
        
        class_lines.append(" ".join(header_parts))
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

        # UPDATED: Add readonly and report keywords
        prop_header = f"{indent}{prop.name}({prop.prop_type})"
        if prop.readonly: prop_header += " readonly"
        if prop.report: prop_header += " report"

        # Header: ... : "DisplayName" : "DefaultValue" : "Description"
        details = []
        if prop.display_name or prop.default_value or prop.description:
            # The FGD format uses an empty field for "no default" when a description is present
            default_val_str = f'"{prop.default_value}"' if prop.default_value else ""
            desc_str = f'"{prop.description.replace("\"", "\\\"")}"' if prop.description else ""
            
            # Logic to avoid trailing colons
            if prop.description:
                details = [f'"{prop.display_name}"', default_val_str, desc_str]
            elif prop.default_value:
                 details = [f'"{prop.display_name}"', default_val_str]
            elif prop.display_name:
                details = [f'"{prop.display_name}"']
        
        if details:
            prop_header += " : " + " : ".join(details)
        
        is_block_prop = isinstance(prop, (fgd_model.ChoicesProperty, fgd_model.FlagsProperty))
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
        # UPDATED: Add optional description
        val_str = f'"{choice.value}"'
        if not re.match(r'^-?\d+(\.\d+)?$', choice.value): # Quote if not a number
             val_str = f'"{choice.value}"'
        else:
            val_str = choice.value

        line = f'{indent}{val_str} : "{choice.display_name}"'
        if choice.description:
            line += f' : "{choice.description.replace("\"", "\\\"")}"'
        return line

    def _serialize_flag_item(self, flag: fgd_model.FlagItem, indent_level: int) -> str:
        indent = "    " * indent_level
        # UPDATED: Add optional description
        line = f'{indent}{flag.value} : "{flag.display_name}" : {int(flag.default_ticked)}'
        if flag.description:
            line += f' : "{flag.description.replace("\"", "\\\"")}"'
        return line