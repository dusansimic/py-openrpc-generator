"""
JSON Schema to TypeScript type converter.

This converter is TypeScript-specific and handles conversion of JSON Schema
definitions to TypeScript types, interfaces, and unions.
"""
from typing import Any, Dict, List, Set, Optional


class TypeScriptConverter:
    """Converts JSON Schema definitions to TypeScript types.

    This is a TypeScript-specific implementation. For other languages,
    create a similar converter (e.g., PythonConverter, JavaConverter).
    """

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self.schemas = self.components.get("schemas", {})
        self.generated_types: Set[str] = set()
        self.type_definitions: List[str] = []

    def convert_schema(self, schema: Dict[str, Any], type_name: Optional[str] = None) -> str:
        """Convert a JSON Schema to TypeScript type."""
        if not schema:
            return "any"

        # Handle $ref
        if "$ref" in schema:
            return self.resolve_ref(schema["$ref"])

        # Handle type
        schema_type = schema.get("type")

        if schema_type == "object":
            return self._convert_object(schema, type_name)
        elif schema_type == "array":
            return self._convert_array(schema)
        elif schema_type == "string":
            return self._convert_string(schema)
        elif schema_type == "number" or schema_type == "integer":
            return self._convert_number(schema)
        elif schema_type == "boolean":
            return "boolean"
        elif schema_type == "null":
            return "null"

        # Handle oneOf, anyOf, allOf
        if "oneOf" in schema:
            return self._convert_one_of(schema["oneOf"])
        elif "anyOf" in schema:
            return self._convert_any_of(schema["anyOf"])
        elif "allOf" in schema:
            return self._convert_all_of(schema["allOf"])

        # Handle enum
        if "enum" in schema:
            return self._convert_enum(schema["enum"])

        return "any"

    def _convert_object(self, schema: Dict[str, Any], type_name: Optional[str] = None) -> str:
        """Convert object schema to TypeScript interface."""
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if not properties:
            # Generic object
            additional_properties = schema.get("additionalProperties", True)
            if additional_properties is True:
                return "Record<string, any>"
            elif isinstance(additional_properties, dict):
                value_type = self.convert_schema(additional_properties)
                return f"Record<string, {value_type}>"
            else:
                return "Record<string, never>"

        # Build inline object type
        fields = []
        for prop_name, prop_schema in properties.items():
            is_required = prop_name in required
            optional_marker = "" if is_required else "?"
            prop_type = self.convert_schema(prop_schema)

            # Handle property names with special characters
            if self._needs_quotes(prop_name):
                prop_name = f'"{prop_name}"'

            fields.append(f"  {prop_name}{optional_marker}: {prop_type};")

        if type_name and type_name not in self.generated_types:
            # Generate a named interface
            self.generated_types.add(type_name)
            interface_def = f"export interface {type_name} {{\n" + "\n".join(fields) + "\n}"
            self.type_definitions.append(interface_def)
            return type_name
        else:
            # Return inline type
            return "{\n" + "\n".join(fields) + "\n}"

    def _convert_array(self, schema: Dict[str, Any]) -> str:
        """Convert array schema to TypeScript array type."""
        items = schema.get("items", {})
        if not items:
            return "any[]"

        item_type = self.convert_schema(items)

        # Handle complex types with parentheses
        if "|" in item_type or "&" in item_type:
            return f"Array<{item_type}>"

        return f"{item_type}[]"

    def _convert_string(self, schema: Dict[str, Any]) -> str:
        """Convert string schema, handling enums."""
        if "enum" in schema:
            return self._convert_enum(schema["enum"])
        return "string"

    def _convert_number(self, schema: Dict[str, Any]) -> str:
        """Convert number schema, handling enums."""
        if "enum" in schema:
            return self._convert_enum(schema["enum"])
        return "number"

    def _convert_enum(self, enum_values: List[Any]) -> str:
        """Convert enum to TypeScript union type."""
        formatted_values = []
        for value in enum_values:
            if isinstance(value, str):
                formatted_values.append(f'"{value}"')
            elif value is None:
                formatted_values.append("null")
            else:
                formatted_values.append(str(value))
        return " | ".join(formatted_values)

    def _convert_one_of(self, schemas: List[Dict[str, Any]]) -> str:
        """Convert oneOf to TypeScript union type."""
        types = [self.convert_schema(s) for s in schemas]
        return " | ".join(types)

    def _convert_any_of(self, schemas: List[Dict[str, Any]]) -> str:
        """Convert anyOf to TypeScript union type."""
        types = [self.convert_schema(s) for s in schemas]
        return " | ".join(types)

    def _convert_all_of(self, schemas: List[Dict[str, Any]]) -> str:
        """Convert allOf to TypeScript intersection type."""
        types = [self.convert_schema(s) for s in schemas]
        return " & ".join(types)

    def resolve_ref(self, ref: str) -> str:
        """Resolve a $ref to a type name."""
        # Handle #/components/schemas/TypeName format
        if ref.startswith("#/components/schemas/"):
            type_name = ref.split("/")[-1]

            # Generate the type if not already generated
            if type_name not in self.generated_types and type_name in self.schemas:
                self.convert_schema(self.schemas[type_name], type_name)

            return type_name

        # Handle other $ref formats
        return "any"

    def _needs_quotes(self, prop_name: str) -> bool:
        """Check if property name needs quotes."""
        return not prop_name.replace("_", "").isalnum() or prop_name[0].isdigit()

    def get_all_type_definitions(self) -> str:
        """Get all generated type definitions as a string."""
        return "\n\n".join(self.type_definitions)
