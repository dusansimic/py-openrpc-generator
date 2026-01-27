# Examples

This directory contains example OpenRPC specifications and their generated TypeScript clients.

## Example Specifications

### [example-spec.json](example-spec.json)
Basic OpenRPC specification demonstrating:
- Simple CRUD operations (user.getById, user.create, user.list)
- Basic parameter and result types
- Schema references
- Enum types in schemas

**Generate client:**
```bash
uv run py-openrpc-generator generate examples/example-spec.json -o examples/client.ts
```

### [example-spec-advanced.json](example-spec-advanced.json)
Comprehensive OpenRPC specification demonstrating all features:
- **paramStructure**: Positional (`by-position`) and named (`by-name`) parameters
- **Error definitions**: Typed error classes with custom error codes
- **Content Descriptor $refs**: Reusable parameter definitions
- **Tags**: Method organization and grouping
- **Server configuration**: With variables and substitution
- **Notification methods**: Fire-and-forget methods without results
- **Deprecated methods**: Methods and parameters marked as deprecated
- **Multiple schemas**: Complex nested types

**Generate client:**
```bash
uv run py-openrpc-generator generate examples/example-spec-advanced.json -o examples/advanced-client.ts
```

## Generated Clients

The generated TypeScript clients demonstrate:
- Full type safety with TypeScript interfaces
- Proper handling of optional/required parameters
- Custom error classes for application errors
- JSDoc comments with descriptions and deprecation warnings
- Method organization by tags
- Default server URLs from spec

## Usage

To try the examples yourself:

```bash
# From the project root
cd ..

# Generate basic client
uv run py-openrpc-generator generate examples/example-spec.json -o examples/my-client.ts

# Generate advanced client with custom class name
uv run py-openrpc-generator generate examples/example-spec-advanced.json -o examples/my-advanced-client.ts -c MyAPIClient
```

## Creating Your Own Spec

Use these examples as templates for your own OpenRPC specifications:
1. Start with `example-spec.json` for a simple API
2. Refer to `example-spec-advanced.json` for advanced features
3. Follow the [OpenRPC specification](https://spec.open-rpc.org/) for complete documentation
