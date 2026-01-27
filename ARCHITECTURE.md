# Architecture

This document explains the architecture of py-openrpc-generator and how to extend it for new languages.

## Design Philosophy

The generator is designed with **separation of concerns** between language-agnostic and language-specific code:

- **Language-Agnostic**: OpenRPC specification parsing
- **Language-Specific**: JSON Schema to target language type conversion

This allows adding new language targets without modifying the core OpenRPC parsing logic.

## Component Overview

### Language-Agnostic Layer

#### `generators/base.py` - OpenRPCSpec
Parses and validates OpenRPC specifications. This class is **completely language-agnostic** and used by all language generators.

**Responsibilities:**
- Load JSON spec from file
- Validate required fields (`openrpc`, `info`, `methods`)
- Parse methods with parameters, results, errors
- Resolve `$ref` pointers for:
  - Content Descriptors (`#/components/contentDescriptors/`)
  - Errors (`#/components/errors/`)
  - Schemas (delegated to converters)
- Extract metadata (servers, tags, deprecation flags)

**Output:** Structured Python dictionaries with parsed OpenRPC data

### Language-Specific Layer

#### `generators/typescript_converter.py` - TypeScriptConverter
Converts JSON Schema definitions to TypeScript types.

**Responsibilities:**
- Map JSON Schema types to TypeScript primitives:
  - `"string"` → `string`
  - `"number"` / `"integer"` → `number`
  - `"boolean"` → `boolean`
  - `"null"` → `null`
- Generate TypeScript interfaces from object schemas
- Handle arrays: `Type[]` or `Array<Type>`
- Handle unions: `oneOf` / `anyOf` → `Type1 | Type2`
- Handle intersections: `allOf` → `Type1 & Type2`
- Handle enums: `["a", "b"]` → `"a" | "b"`
- Generate `export interface` declarations
- Resolve schema `$ref` pointers

**Input:** JSON Schema objects (from OpenRPCSpec)
**Output:** TypeScript type strings and interface definitions

#### `generators/typescript.py` - TypeScriptGenerator
Orchestrates TypeScript client generation.

**Responsibilities:**
- Initialize TypeScriptConverter
- Process methods to generate parameter and result types
- Generate error classes from error definitions
- Extract default server URL
- Organize methods by tags
- Render Jinja2 template with context
- Write output file

**Input:** OpenRPCSpec instance
**Output:** TypeScript client file (`.ts`)

#### `templates/typescript-client.ts.jinja2`
Jinja2 template for TypeScript client output.

**Contains:**
- Type definitions (from converter)
- JSON-RPC infrastructure (request/response types)
- Error classes (generated from error definitions)
- Client class with typed methods
- JSDoc comments

## Data Flow

```
OpenRPC JSON File
      ↓
OpenRPCSpec.from_file()
      ↓
OpenRPCSpec (parsed data)
      ↓
TypeScriptGenerator.generate()
      ↓
  ┌─────────────────┴──────────────┐
  ↓                                ↓
TypeScriptConverter         Process Methods,
(JSON Schema → TS types)    Errors, Tags, etc.
  ↓                                ↓
  └─────────────────┬──────────────┘
                    ↓
         Template Context (dict)
                    ↓
         Jinja2 Template Rendering
                    ↓
         TypeScript Client (.ts file)
```

## Adding a New Language

Let's walk through adding Python support as an example.

### Step 1: Create Python Converter

Create `generators/python_converter.py`:

```python
"""JSON Schema to Python type converter."""
from typing import Any, Dict, List, Set, Optional


class PythonConverter:
    """Converts JSON Schema definitions to Python types.

    Generates TypedDict, dataclass, or Pydantic model definitions
    depending on the target framework.
    """

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self.schemas = self.components.get("schemas", {})
        self.generated_types: Set[str] = set()
        self.type_definitions: List[str] = []

    def convert_schema(self, schema: Dict[str, Any], type_name: Optional[str] = None) -> str:
        """Convert a JSON Schema to Python type annotation."""
        if not schema:
            return "Any"

        # Handle $ref
        if "$ref" in schema:
            return self.resolve_ref(schema["$ref"])

        schema_type = schema.get("type")

        # Map JSON types to Python types
        if schema_type == "string":
            if "enum" in schema:
                return self._convert_enum(schema["enum"])
            return "str"
        elif schema_type == "number":
            return "float"
        elif schema_type == "integer":
            return "int"
        elif schema_type == "boolean":
            return "bool"
        elif schema_type == "null":
            return "None"
        elif schema_type == "object":
            return self._convert_object(schema, type_name)
        elif schema_type == "array":
            return self._convert_array(schema)

        # Handle composition
        if "oneOf" in schema or "anyOf" in schema:
            types = [self.convert_schema(s) for s in schema.get("oneOf", schema.get("anyOf", []))]
            return f"Union[{', '.join(types)}]"

        return "Any"

    def _convert_object(self, schema: Dict[str, Any], type_name: Optional[str]) -> str:
        """Generate TypedDict definition."""
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if not type_name:
            return "dict[str, Any]"

        if type_name in self.generated_types:
            return type_name

        self.generated_types.add(type_name)

        # Generate TypedDict
        fields = []
        for prop_name, prop_schema in properties.items():
            prop_type = self.convert_schema(prop_schema)
            if prop_name not in required:
                prop_type = f"NotRequired[{prop_type}]"
            fields.append(f"    {prop_name}: {prop_type}")

        definition = f"class {type_name}(TypedDict):\n" + "\n".join(fields)
        self.type_definitions.append(definition)

        return type_name

    def _convert_array(self, schema: Dict[str, Any]) -> str:
        """Generate list type annotation."""
        items = schema.get("items", {})
        if not items:
            return "list[Any]"

        item_type = self.convert_schema(items)
        return f"list[{item_type}]"

    def _convert_enum(self, values: List[Any]) -> str:
        """Generate Literal union."""
        formatted = [f'"{v}"' if isinstance(v, str) else str(v) for v in values]
        return f"Literal[{', '.join(formatted)}]"

    def resolve_ref(self, ref: str) -> str:
        """Resolve $ref to type name."""
        if ref.startswith("#/components/schemas/"):
            type_name = ref.split("/")[-1]
            if type_name not in self.generated_types and type_name in self.schemas:
                self.convert_schema(self.schemas[type_name], type_name)
            return type_name
        return "Any"

    def get_all_type_definitions(self) -> str:
        """Get all generated type definitions."""
        imports = [
            "from typing import Any, Literal, NotRequired",
            "from typing_extensions import TypedDict",
            "",
        ]
        return "\n".join(imports) + "\n\n".join(self.type_definitions)
```

### Step 2: Create Python Generator

Create `generators/python.py`:

```python
"""Python client generator."""
from pathlib import Path
from typing import Any, Dict, List
from jinja2 import Environment, PackageLoader, select_autoescape
from .base import OpenRPCSpec
from .python_converter import PythonConverter


class PythonGenerator:
    """Generates Python client from OpenRPC spec."""

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("py_openrpc_generator", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, spec: OpenRPCSpec, output_path: str, class_name: str = "RPCClient") -> None:
        """Generate Python client file."""
        template = self.env.get_template("python-client.py.jinja2")

        # Initialize Python converter
        converter = PythonConverter(spec.components)

        # Process methods (similar to TypeScript)
        methods = self._process_methods(spec.get_method_list(), converter)

        # ... rest similar to TypeScriptGenerator
```

### Step 3: Create Python Template

Create `templates/python-client.py.jinja2`:

```python
"""
{{ info.title }}
{{ info.description }}
Version: {{ info.version }}

Auto-generated by py-openrpc-generator
"""

import requests
from typing import Any, Optional

{{ type_definitions }}


class JsonRpcError(Exception):
    """JSON-RPC error."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC Error {code}: {message}")


class {{ class_name }}:
    """{{ info.title }} client."""

    def __init__(self, url: str{% if default_server_url %} = "{{ default_server_url }}"{% endif %}):
        self.url = url
        self.request_id = 0

    def _request(self, method: str, params: Any = None) -> Any:
        """Execute JSON-RPC request."""
        self.request_id += 1
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id,
        }

        response = requests.post(self.url, json=body)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error = data["error"]
            raise JsonRpcError(error["code"], error["message"], error.get("data"))

        return data.get("result")

    {% for method in methods %}
    def {{ method.safe_name }}(self{% if method.has_params %}, params: {{ method.params_type }}{% endif %}) -> {{ method.result_type }}:
        """{{ method.summary or method.name }}"""
        return self._request("{{ method.name }}"{% if method.has_params %}, params{% endif %})
    {% endfor %}
```

### Step 4: Update CLI

Update `cli.py` to support the new language:

```python
# In cli.py generate command
if args.language == "typescript":
    from .generators.typescript import TypeScriptGenerator
    generator = TypeScriptGenerator()
elif args.language == "python":
    from .generators.python import PythonGenerator
    generator = PythonGenerator()

generator.generate(spec, args.output, args.class_name)
```

## Testing New Languages

1. **Use existing examples**: Test with `examples/example-spec.json`
2. **Verify type conversion**: Check that JSON Schema types map correctly
3. **Test advanced features**: Try with `examples/example-spec-advanced.json`
4. **Manual testing**: Run the generated client against a real JSON-RPC API

## Best Practices

1. **Keep base.py language-agnostic** - Never add language-specific logic there
2. **Consistent converter interface** - All converters should have similar methods
3. **Comprehensive type mapping** - Cover all JSON Schema types and keywords
4. **Error handling** - Generate appropriate error classes for the language
5. **Documentation** - Add JSDoc/docstrings/comments to generated code
6. **Testing** - Test with both simple and complex OpenRPC specs

## Future Enhancements

Potential improvements for the architecture:

1. **Abstract base converter** - Create a base class that all converters inherit from
2. **Plugin system** - Allow loading converters/generators dynamically
3. **Configuration files** - Allow per-language configuration (e.g., style preferences)
4. **Validation** - Add JSON Schema validation for OpenRPC specs
5. **Multiple output modes** - Support different frameworks (e.g., Axios vs Fetch for TS)
