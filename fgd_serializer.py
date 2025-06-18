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
            elif isinstance(element, fgd_model.EntityClass):
                lines.append(self._serialize_entity_class(element))
            lines.append("") # Blank line between top-level elements
        return "\n".join(lines)

    def _serialize_include_directive(self, include_dir: fgd_model.IncludeDirective) -> str:
        return f'@include "{include_dir.file_path}"'

    def _serialize_entity_class(self, entity_class: fgd_model.EntityClass) -> str:
        class_lines = []
        
        # Header: @ClassType base(...) color(...) etc. = name : "description"
        header_parts = [f"@{entity_class.class_type}"]
        if entity_class.base_classes:
            header_parts.append(f"base({', '.join(entity_class.base_classes)})")
        if entity_class.color:
            header_parts.append(f"color({entity_class.color[0]} {entity_class.color[1]} {entity_class.color[2]})")
        if entity_class.size:
            min_str = ' '.join(map(str, entity_class.size[0]))
            max_str = ' '.join(map(str, entity_class.size[1]))
            header_parts.append(f"size({min_str}, {max_str})")
        if entity_class.studio:
            header_parts.append(f'studio("{entity_class.studio}")')
        if entity_class.sprite:
            header_parts.append(f'sprite("{entity_class.sprite}")')
        
        # Escape quotes in description for serialization
        description = entity_class.description.replace('"', '\\"')
        header_parts.append(f'= {entity_class.name} : "{description}"')
        
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
        line = f'{indent}{io_obj.io_type} "{io_obj.name}"({io_obj.arg_type})'
        if desc:
            line += f' : "{desc}"'
        return line

    def _serialize_property(self, prop: fgd_model.Property, indent_level: int) -> list[str]:
        indent = "    " * indent_level
        prop_lines = []

        # Header: name(type) : "DisplayName" : "DefaultValue" : "Description"
        prop_header = f"{indent}{prop.name}({prop.prop_type})"
        details = []
        if prop.display_name or prop.default_value or prop.description:
            details.append(f'"{prop.display_name}"')
            details.append(f'"{prop.default_value}"')
            details.append(f'"{prop.description.replace("\"", "\\\"")}"')
        
        if details:
            prop_header += " : " + " : ".join(details)
        
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
        line = f'{indent}"{choice.value}" : "{choice.display_name}"'
        if choice.description:
            line += f' : "{choice.description.replace("\"", "\\\"")}"'
        return line

    def _serialize_flag_item(self, flag: fgd_model.FlagItem, indent_level: int) -> str:
        indent = "    " * indent_level
        # Format: value : "DisplayName" : default_state
        return f'{indent}{flag.value} : "{flag.display_name}" : {int(flag.default_ticked)}'