"""
JSON Schema to Go type converter for Gorilla RPC server generation.

This converter is Go-specific and handles conversion of JSON Schema
definitions to Go types and struct definitions.
"""
from typing import Any, Dict, List, Optional, Set


class GolangConverter:
    """Converts JSON Schema definitions to Go types.

    Generates Go struct definitions for object types and returns
    Go type strings for primitives, arrays, and references.
    """

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self.schemas = self.components.get("schemas", {})
        self.generated_types: Set[str] = set()
        self.type_definitions: List[str] = []

    def convert_schema(self, schema: Dict[str, Any], type_name: Optional[str] = None) -> str:
        """Convert a JSON Schema to a Go type string."""
        if not schema:
            return "interface{}"

        # Handle $ref
        if "$ref" in schema:
            return self.resolve_ref(schema["$ref"])

        schema_type = schema.get("type")

        if schema_type == "object":
            return self._convert_object(schema, type_name)
        elif schema_type == "array":
            return self._convert_array(schema)
        elif schema_type == "string":
            return self._convert_string(schema)
        elif schema_type == "integer":
            return "int64"
        elif schema_type == "number":
            return "float64"
        elif schema_type == "boolean":
            return "bool"
        elif schema_type == "null":
            return "interface{}"

        # Handle oneOf, anyOf, allOf
        if "oneOf" in schema:
            return "interface{}"
        elif "anyOf" in schema:
            return "interface{}"
        elif "allOf" in schema:
            return self._convert_all_of(schema["allOf"], type_name)

        # Handle top-level enum
        if "enum" in schema:
            return self._convert_enum(schema["enum"])

        return "interface{}"

    def _convert_object(self, schema: Dict[str, Any], type_name: Optional[str] = None) -> str:
        """Convert object schema to a Go struct."""
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        if not properties:
            additional = schema.get("additionalProperties", True)
            if isinstance(additional, dict):
                val_type = self.convert_schema(additional)
                return f"map[string]{val_type}"
            return "map[string]interface{}"

        fields = self._build_struct_fields(properties, required_fields, type_name)

        if type_name and type_name not in self.generated_types:
            self.generated_types.add(type_name)
            struct_def = f"type {type_name} struct {{\n" + "\n".join(fields) + "\n}"
            self.type_definitions.append(struct_def)
            return type_name
        elif type_name:
            # Already generated, just return the name
            return type_name
        else:
            # Should not reach here in normal usage; fall back to map
            return "map[string]interface{}"

    def _build_struct_fields(
        self,
        properties: Dict[str, Any],
        required_fields: Set[str],
        parent_type_name: Optional[str] = None,
    ) -> List[str]:
        """Build Go struct field lines for the given properties.

        When parent_type_name is provided, nested object fields get named types
        rather than anonymous structs (e.g. ParentTypeFieldName).
        """
        fields = []
        for json_name, prop_schema in properties.items():
            is_required = json_name in required_fields
            go_name = self.go_field_name(json_name)

            go_type = self._field_go_type(prop_schema, go_name, parent_type_name)

            # Wrap optional scalars/structs as pointers
            if not is_required and not go_type.startswith(("*", "[]", "map[", "interface")):
                go_type = f"*{go_type}"

            omitempty = "" if is_required else ",omitempty"
            tag = f'`json:"{json_name}{omitempty}"`'
            fields.append(f"\t{go_name} {go_type} {tag}")
        return fields

    def _field_go_type(
        self,
        prop_schema: Dict[str, Any],
        go_name: str,
        parent_type_name: Optional[str],
    ) -> str:
        """Determine the Go type for a struct field, generating named sub-types when
        parent_type_name is provided (avoids anonymous structs and untyped maps).
        """
        if not parent_type_name:
            return self.convert_schema(prop_schema)

        schema_type = prop_schema.get("type")

        # Nested object → generate a named type e.g. ParentData
        if schema_type == "object" and prop_schema.get("properties"):
            type_hint = f"{parent_type_name}{go_name}"
            return self.convert_schema(prop_schema, type_hint)

        # Array whose items are an object → generate a named item type
        if schema_type == "array":
            items = prop_schema.get("items", {})
            if items.get("type") == "object" and items.get("properties"):
                # Derive singular name: "Items" -> "Item", "Results" -> "Result"
                base = go_name[:-1] if go_name.endswith("s") and len(go_name) > 1 else go_name
                item_type_name = f"{parent_type_name}{base}"
                item_type = self.convert_schema(items, item_type_name)
                return f"[]{item_type}"

        return self.convert_schema(prop_schema)

    def _convert_array(self, schema: Dict[str, Any]) -> str:
        """Convert array schema to a Go slice type."""
        items = schema.get("items", {})
        if not items:
            return "[]interface{}"
        item_type = self.convert_schema(items)
        return f"[]{item_type}"

    def _convert_string(self, schema: Dict[str, Any]) -> str:
        """Convert string schema, noting enums as a comment."""
        if "enum" in schema:
            return self._convert_enum(schema["enum"])
        return "string"

    def _convert_enum(self, enum_values: List[Any]) -> str:
        """Return string for enum types (Go uses string with const block for named types)."""
        # For inline enums, we just use string; named const blocks are generated separately
        # Check if all values are strings
        if all(isinstance(v, str) for v in enum_values):
            return "string"
        elif all(isinstance(v, (int, float)) for v in enum_values if v is not None):
            return "int64"
        return "interface{}"

    def _convert_all_of(
        self, schemas: List[Dict[str, Any]], type_name: Optional[str] = None
    ) -> str:
        """Convert allOf by merging all properties into one struct."""
        merged_properties: Dict[str, Any] = {}
        merged_required: Set[str] = set()

        for sub_schema in schemas:
            # Resolve $ref if needed
            if "$ref" in sub_schema:
                ref_name = self.resolve_ref(sub_schema["$ref"])
                # We can't easily merge a $ref at this point; embed as anonymous struct
                # For simplicity, treat as interface{}
                return "interface{}"

            props = sub_schema.get("properties", {})
            required = sub_schema.get("required", [])
            merged_properties.update(props)
            merged_required.update(required)

        if not merged_properties:
            return "interface{}"

        mock_schema = {
            "type": "object",
            "properties": merged_properties,
            "required": list(merged_required),
        }
        return self._convert_object(mock_schema, type_name)

    def resolve_ref(self, ref: str) -> str:
        """Resolve a $ref to a Go type name, generating the type if needed."""
        if ref.startswith("#/components/schemas/"):
            type_name = ref.split("/")[-1]
            if type_name not in self.generated_types and type_name in self.schemas:
                self.convert_schema(self.schemas[type_name], type_name)
            return type_name
        return "interface{}"

    def go_field_name(self, json_name: str) -> str:
        """Convert a JSON field name to an exported Go field name.

        Examples:
            userId    -> UserID
            createdAt -> CreatedAt
            id        -> ID
            url       -> URL
            name      -> Name
        """
        # Common abbreviations that should be all-caps in Go
        acronyms = {
            "id", "url", "uri", "api", "http", "https", "json", "rpc",
            "sql", "db", "ip", "ui", "uuid", "html", "xml", "csv",
        }

        # Split camelCase / PascalCase into words
        words = self._split_camel(json_name)

        result = []
        for word in words:
            lower = word.lower()
            if lower in acronyms:
                result.append(lower.upper())
            else:
                result.append(word[0].upper() + word[1:].lower() if word else "")

        return "".join(result) if result else json_name.capitalize()

    def _split_camel(self, name: str) -> List[str]:
        """Split a camelCase or snake_case name into words."""
        if not name:
            return []

        # Handle snake_case
        if "_" in name:
            return [w for w in name.split("_") if w]

        # Split camelCase
        words = []
        current = []
        for i, char in enumerate(name):
            if char.isupper() and current:
                words.append("".join(current))
                current = [char]
            else:
                current.append(char)
        if current:
            words.append("".join(current))
        return words

    def generate_enum_consts(
        self, type_name: str, go_type: str, values: List[Any]
    ) -> str:
        """Generate a Go const block for an enum type."""
        lines = [f"const ("]
        for val in values:
            const_name = self.go_field_name(str(val)) if isinstance(val, str) else f"Val{val}"
            const_name = f"{type_name}{const_name}"
            if isinstance(val, str):
                lines.append(f'\t{const_name} {type_name} = "{val}"')
            else:
                lines.append(f"\t{const_name} {type_name} = {val}")
        lines.append(")")
        return "\n".join(lines)

    def get_all_type_definitions(self) -> str:
        """Get all generated type definitions as a string."""
        return "\n\n".join(self.type_definitions)
