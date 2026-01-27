# py-openrpc-generator

A Python CLI tool that generates fully-typed TypeScript clients from OpenRPC specifications. This generator converts your OpenRPC spec into a ready-to-use TypeScript client with proper type safety, including support for JSON Schema to TypeScript type conversion.

## Features

- **Full Type Safety**: Generates TypeScript interfaces from JSON Schema definitions
- **$ref Resolution**: Automatically resolves schema references
- **JSON Schema Support**: Handles objects, arrays, enums, oneOf, anyOf, allOf
- **Parameter Types**: Generates typed interfaces for method parameters
- **Return Types**: Generates typed interfaces for method results
- **Single File Output**: Generates a complete client in one TypeScript file
- **JSON-RPC 2.0**: Built-in support for JSON-RPC 2.0 protocol
- **Error Handling**: Custom error class for JSON-RPC errors

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd py-openrpc-generator

# Install with UV
uv sync

# Try it with an example
uv run py-openrpc-generator generate examples/example-spec.json -o examples/my-client.ts
```

Check out the [examples/](examples/) directory for more example OpenRPC specifications and generated clients.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd py-openrpc-generator

# Install with UV
uv sync
```

## Usage

### Basic Usage

```bash
# Generate TypeScript client from OpenRPC spec
uv run py-openrpc-generator generate spec.json -o client.ts

# Specify custom class name
uv run py-openrpc-generator generate spec.json -o client.ts -c MyAPIClient
```

### CLI Options

```
py-openrpc-generator generate [OPTIONS] SPEC

Arguments:
  SPEC                Path to OpenRPC specification file (JSON)

Options:
  -o, --output TEXT   Output file path (default: ./client.ts)
  -l, --language      Target language (default: typescript)
  -c, --class-name    Generated client class name (default: RPCClient)
  -h, --help          Show help message
```

### Examples

The repository includes two example OpenRPC specifications in the [examples/](examples/) directory:

1. **[example-spec.json](examples/example-spec.json)** - Basic example with simple CRUD operations
2. **[example-spec-advanced.json](examples/example-spec-advanced.json)** - Comprehensive example demonstrating all features:
   - paramStructure (positional and named params)
   - Error definitions with typed error classes
   - Content Descriptor $refs
   - Tags for organization
   - Server configuration with variables
   - Notification methods
   - Deprecated methods

```bash
# Generate client from basic example
uv run py-openrpc-generator generate examples/example-spec.json -o examples/client.ts

# Generate client from advanced example
uv run py-openrpc-generator generate examples/example-spec-advanced.json -o examples/advanced-client.ts
```

This generates a TypeScript client with:
- Typed interfaces for all parameters and results
- Type-safe method signatures with positional/named parameter support
- JSDoc comments with descriptions, deprecation warnings, and error codes
- Proper enum types
- Referenced schema types from components
- Typed error classes for application-specific errors
- Methods organized by tags
- Default server URL from spec
- Notification method support

### Using the Generated Client

```typescript
import { RPCClient, UserNotFoundError } from './generated-client';

// Initialize the client (uses default URL from spec if provided)
const client = new RPCClient('https://api.example.com/rpc');
// Or use default from spec:
// const client = new RPCClient();

// Call methods with full type safety
try {
  const user = await client.user_getById({ userId: '123' });
  // user is typed as User interface
  console.log(user.name, user.email);
} catch (error) {
  if (error instanceof UserNotFoundError) {
    console.error('User not found!');
  }
}

// Create a new user
const newUser = await client.user_create({
  name: 'John Doe',
  email: 'john@example.com',
  age: 30  // optional parameter
});

// Positional parameters (when paramStructure: "by-position")
const sum = await client.math_add([5, 3]); // Returns 8

// Notification methods (fire-and-forget, no response)
client.notifications_subscribe({ channel: 'users' });
// Returns immediately without waiting for server response
```

## Advanced Features

### Typed Error Handling

The generator creates typed error classes from error definitions in your OpenRPC spec:

```typescript
// Error definitions in spec create typed error classes
try {
  const user = await client.user_getById({ userId: 'invalid' });
} catch (error) {
  if (error instanceof UserNotFoundError) {
    console.error('User not found:', error.code); // 1001
  } else if (error instanceof InvalidUserIdFormatError) {
    console.error('Invalid ID format:', error.code); // 1004
  } else if (error instanceof JsonRpcError) {
    console.error('JSON-RPC error:', error.code, error.message);
  }
}
```

### Parameter Structure Support

The generator respects the `paramStructure` field:

```typescript
// by-name (default) - object parameters
await client.user_create({
  name: 'John',
  email: 'john@example.com'
});

// by-position - tuple/array parameters
await client.math_add([5, 3]); // [a, b]

// either - accepts both formats
```

### Notification Methods

Methods without a `result` field are treated as notifications (fire-and-forget):

```typescript
// Regular method - waits for response
const user = await client.user_getById({ userId: '123' });

// Notification method - returns immediately
client.notifications_subscribe({ channel: 'users' });
```

### Content Descriptor References

Reuse parameter definitions across methods using `$ref`:

```json
{
  "params": [
    { "$ref": "#/components/contentDescriptors/UserId" }
  ],
  "components": {
    "contentDescriptors": {
      "UserId": {
        "name": "userId",
        "required": true,
        "schema": { "type": "string" }
      }
    }
  }
}
```

### Tag-Based Organization

Methods are automatically organized by tags in the generated code:

```typescript
// Methods grouped by tags with clear section headers:
// --------------------------------------------------------------------------
// Users
// --------------------------------------------------------------------------
async user_getById(params: User_getByIdParams): Promise<User> { ... }
async user_create(params: User_createParams): Promise<User> { ... }

// --------------------------------------------------------------------------
// Orders
// --------------------------------------------------------------------------
async order_list(params: Order_listParams): Promise<Order[]> { ... }
```

### Deprecation Warnings

Deprecated methods and parameters are marked with `@deprecated` JSDoc tags:

```typescript
/**
 * @deprecated This method is deprecated. Use user.patch instead.
 */
async user_update(params: User_updateParams): Promise<User> { ... }
```

### Server URL Configuration

If your spec includes servers, the first server URL becomes the default:

```typescript
// With server in spec:
const client = new RPCClient(); // Uses default from spec

// Override the default:
const client = new RPCClient('https://custom-api.example.com');
```

Server variables are automatically substituted with their default values.

## Supported OpenRPC Features

### Fully Supported ✓
- **Info object** - title, version, description, contact, license
- **Methods** - with parameters and results
- **JSON Schema types** - object, array, string, number, integer, boolean, null
- **Required and optional parameters** - proper TypeScript optional fields
- **$ref resolution** - for schemas, contentDescriptors, and errors
- **Enums** - converted to TypeScript union types
- **oneOf, anyOf, allOf** - converted to union/intersection types
- **Nested objects and arrays** - full support
- **Method descriptions** - comprehensive JSDoc generation
- **paramStructure** - by-position (tuples), by-name (objects), or either
- **Deprecated fields** - @deprecated JSDoc tags for methods and parameters
- **Error definitions** - typed error classes with automatic error handling
- **Content Descriptors** - full support with $ref resolution
- **Tags** - methods organized by tags in generated code
- **Server objects** - default URL with variable substitution
- **Notification methods** - methods without results (fire-and-forget)
- **External docs** - @see links in JSDoc

### Partially Supported ⚠️
- **Format strings** - preserved in schemas but not validated at runtime
- **Server variables** - basic substitution with defaults (no enum validation)
- **Info contact/license** - parsed but not included in generated output

### Not Yet Supported ✗
- **Links between methods** - runtime expressions and method chaining
- **Examples** - Example Pairing Objects not included in JSDoc
- **Advanced JSON Schema** - pattern, minimum/maximum, format validation
- **Recursive schemas** - may cause issues with circular references
- **Multiple servers** - only first server used
- **Method-level servers** - server overrides per method
- **Multiple language targets** - only TypeScript currently

## Project Structure

```
py-openrpc-generator/
├── src/
│   └── py_openrpc_generator/
│       ├── __init__.py
│       ├── cli.py                       # CLI entry point
│       ├── generators/
│       │   ├── base.py                  # Language-agnostic OpenRPC parser
│       │   ├── typescript_converter.py  # TypeScript-specific type converter
│       │   └── typescript.py            # TypeScript client generator
│       └── templates/
│           └── typescript-client.ts.jinja2  # TypeScript client template
├── examples/
│   ├── example-spec.json                # Basic OpenRPC spec
│   ├── example-spec-advanced.json       # Advanced OpenRPC spec
│   └── *.ts                             # Generated client examples
├── pyproject.toml
├── LICENSE
└── README.md
```

## Development

### Running Tests

```bash
# Test with example spec
uv run py-openrpc-generator generate examples/example-spec.json -o examples/test-output.ts
```

### Adding New Features

The project is organized into modular components:

1. **Base Loader** ([generators/base.py](src/py_openrpc_generator/generators/base.py)): Language-agnostic OpenRPC spec parser
2. **TypeScript Converter** ([generators/typescript_converter.py](src/py_openrpc_generator/generators/typescript_converter.py)): Converts JSON Schema to TypeScript types
3. **TypeScript Generator** ([generators/typescript.py](src/py_openrpc_generator/generators/typescript.py)): Orchestrates TypeScript client generation
4. **Template** ([templates/typescript-client.ts.jinja2](src/py_openrpc_generator/templates/typescript-client.ts.jinja2)): Jinja2 template for output

### Extending to Other Languages

The project is designed with multi-language support in mind:

**Language-Agnostic Components:**
- `base.py` - Parses OpenRPC specs (works for all languages)

**Language-Specific Components:**
- `typescript_converter.py` - JSON Schema → TypeScript type conversion
- `typescript.py` - TypeScript client generation logic
- `typescript-client.ts.jinja2` - TypeScript output template

**To add support for a new language** (e.g., Python):

1. **Create a converter** - `generators/python_converter.py`
   ```python
   class PythonConverter:
       """Converts JSON Schema to Python types (str, int, TypedDict, etc.)"""
       def convert_schema(self, schema, type_name=None):
           # Map "string" → "str", "number" → "float", etc.
           # Generate TypedDict or dataclass definitions
   ```

2. **Create a generator** - `generators/python.py`
   ```python
   class PythonGenerator:
       """Generates Python client using PythonConverter"""
       def generate(self, spec, output_path):
           converter = PythonConverter(spec.components)
           # Process methods, render template
   ```

3. **Create a template** - `templates/python-client.py.jinja2`
   ```python
   # Python client template with type hints, requests library, etc.
   ```

4. **Update CLI** - `cli.py`
   ```python
   if args.language == "python":
       from .generators.python import PythonGenerator
       generator = PythonGenerator()
       generator.generate(spec, args.output)
   ```

The key insight: **JSON Schema → Language Types is language-specific, but OpenRPC parsing is universal**.

## Dependencies

- Python >= 3.14
- jinja2 >= 3.1.6
- uv (for package management)

## License

This project is licensed under the BSD 2-Clause License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

For information about the project architecture and how to add support for new languages, see [ARCHITECTURE.md](ARCHITECTURE.md).
