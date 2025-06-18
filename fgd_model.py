# fgd_model.py

import re

class FGDElement:
    """Base class for any named element in an FGD file."""
    def __init__(self, name: str, description: str = ""):
        if not isinstance(name, str) or not name:
            raise ValueError("Name must be a non-empty string.")
        if not isinstance(description, str):
            raise ValueError("Description must be a string.")
        self.name = name
        self.description = description

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description[:30]}...')'"

class IncludeDirective(FGDElement):
    """Represents an @include directive in an FGD file."""
    def __init__(self, file_path: str):
        super().__init__(name=f"@include \"{file_path}\"", description=f"Includes definitions from '{file_path}'")
        self.file_path = file_path
        self.class_type = "Include"

    def __repr__(self):
        return f"IncludeDirective(file_path='{self.file_path}')"

class Property(FGDElement):
    """Base class for all types of properties (keyvalues, flags, etc.)."""
    def __init__(self, name: str, prop_type: str, display_name: str = "", default_value: str = "", description: str = ""):
        super().__init__(name, description)
        self.prop_type = prop_type
        self.display_name = display_name if isinstance(display_name, str) else ""
        self.default_value = default_value if isinstance(default_value, str) else ""

    def __repr__(self):
        return f"Property(name='{self.name}', type='{self.prop_type}', default='{self.default_value}')"

class KeyvalueProperty(Property):
    def __init__(self, name: str, prop_type: str, display_name: str = "", default_value: str = "", description: str = ""):
        super().__init__(name, prop_type, display_name, default_value, description)

class ChoiceItem(FGDElement):
    """Represents a single choice option within a ChoicesProperty."""
    def __init__(self, value: str, display_name: str = "", description: str = ""):
        super().__init__(name=value, description=description)
        self.value = value
        self.display_name = display_name

    def __repr__(self):
        return f"ChoiceItem(value='{self.value}', display_name='{self.display_name}')"

class ChoicesProperty(Property):
    def __init__(self, name: str, prop_type: str, display_name: str = "", default_value: str = "", description: str = "", choices: list = None):
        super().__init__(name, prop_type, display_name, default_value, description)
        self.choices = choices if choices is not None else []
        if not all(isinstance(choice, ChoiceItem) for choice in self.choices):
            raise ValueError("Choices must be a list of ChoiceItem objects.")

    def __repr__(self):
        return f"ChoicesProperty(name='{self.name}', choices={len(self.choices)} items)"

class FlagItem(FGDElement):
    """Represents a single flag option within a FlagsProperty."""
    def __init__(self, value: int, display_name: str = "", description: str = "", default_ticked: bool = False):
        super().__init__(name=str(value), description=description)
        self.value = value
        self.display_name = display_name
        self.default_ticked = default_ticked

    def __repr__(self):
        return f"FlagItem(value={self.value}, display_name='{self.display_name}', default_ticked={self.default_ticked})"

class FlagsProperty(Property):
    def __init__(self, name: str, prop_type: str, display_name: str = "", default_value: str = "", description: str = "", flags: list = None):
        super().__init__(name, prop_type, display_name, default_value, description)
        self.flags = flags if flags is not None else []
        if not all(isinstance(flag, FlagItem) for flag in self.flags):
            raise ValueError("Flags must be a list of FlagItem objects.")

    def __repr__(self):
        return f"FlagsProperty(name='{self.name}', flags={len(self.flags)} items)"

class IO(FGDElement):
    def __init__(self, io_type: str, name: str, arg_type: str = "", description: str = ""):
        super().__init__(name, description)
        self.io_type = io_type # 'input' or 'output'
        self.arg_type = arg_type

    def __repr__(self):
        return f"IO(type='{self.io_type}', name='{self.name}', arg_type='{self.arg_type}')"

class EntityClass(FGDElement):
    """Represents a @SolidClass, @PointClass, @BaseClass, etc."""
    def __init__(self, class_type: str, name: str, description: str = "", base_classes: list = None,
                 properties: list = None, inputs: list = None, outputs: list = None,
                 color: tuple = None, size: tuple = None, studio: str = None, sprite: str = None):
        super().__init__(name, description)
        self.class_type = class_type
        self.base_classes = list(base_classes) if base_classes is not None else []
        self.properties = properties if properties is not None else []
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.color = color
        self.size = size
        self.studio = studio
        self.sprite = sprite

        if not all(isinstance(prop, Property) for prop in self.properties):
            raise ValueError("Properties must be a list of Property objects.")
        if not all(isinstance(io, IO) for io in self.inputs + self.outputs):
            raise ValueError("Inputs/Outputs must be a list of IO objects.")

    def add_io(self, io_obj: IO):
        """Adds an IO object to the correct list (inputs or outputs)."""
        if io_obj.io_type == 'input':
            self.inputs.append(io_obj)
        elif io_obj.io_type == 'output':
            self.outputs.append(io_obj)

    def __repr__(self):
        return (f"EntityClass(type='{self.class_type}', name='{self.name}', "
                f"props={len(self.properties)}, inputs={len(self.inputs)}, outputs={len(self.outputs)})")

class FGDFile:
    """Represents an entire FGD file, holding all its elements."""
    def __init__(self):
        self.elements = []
        self.class_map = {}
        self.base_classes = {}

    def add_element(self, element: FGDElement):
        """Adds an FGD element to the file and updates internal maps."""
        self.elements.append(element)
        if isinstance(element, EntityClass):
            self.class_map[element.name] = element
            if element.class_type == "BaseClass":
                self.base_classes[element.name] = element

    def __repr__(self):
        return f"FGDFile(elements={len(self.elements)})"