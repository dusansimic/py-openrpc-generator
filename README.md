# py-openrpc-generator

A Python CLI tool that generates code from OpenRPC specifications. Currently supports:

- **TypeScript** — fully-typed JSON-RPC 2.0 client with typed interfaces and error classes
- **Go (Gorilla RPC v2)** — typed server handler stubs for `github.com/gorilla/rpc/v2` with JSON-RPC 2.0

## Features

### TypeScript Client
- Full type safety with generated interfaces from JSON Schema definitions
- JSON-RPC 2.0 protocol with `fetch`-based transport
- Typed error classes from OpenRPC error definitions
- Method organization by tags with JSDoc comments

### Go Gorilla RPC Server
- Typed `Args` / `Reply` structs for every handler method
- Service structs grouped by method namespace (`user.getById` → `UserService.GetById`)
- Named types for all nested objects — no anonymous structs
- Typed error structs implementing the `error` interface
- Complete `main()` with all services registered

### Both Targets
- `$ref` resolution for schemas, contentDescriptors, and errors
- JSON Schema support: objects, arrays, enums, oneOf, anyOf, allOf
- Deprecated method markers
- Notification / fire-and-forget methods
- Server URL / port extraction from spec

## Quick Start

```bash
# Clone and install
git clone <repository-url>
cd py-openrpc-generator
uv sync

# Generate a TypeScript client
uv run py-openrpc-generator generate examples/example-spec.json -o client.ts

# Generate a Go Gorilla RPC server
uv run py-openrpc-generator generate examples/example-spec.json -l go-gorilla -o server.go
```

Check out the [examples/](examples/) directory for example specs and generated outputs.

## Installation

```bash
git clone <repository-url>
cd py-openrpc-generator
uv sync
```

## Usage

### Basic Usage

```bash
# TypeScript client (default)
uv run py-openrpc-generator generate spec.json -o client.ts

# TypeScript with custom class name
uv run py-openrpc-generator generate spec.json -o client.ts -c MyAPIClient

# Go Gorilla RPC server
uv run py-openrpc-generator generate spec.json -l go-gorilla -o server.go

# Go with custom package name
uv run py-openrpc-generator generate spec.json -l go-gorilla -p myapi -o server.go
```

### CLI Options

```
py-openrpc-generator generate [OPTIONS] SPEC

Arguments:
  SPEC                    Path to OpenRPC specification file (JSON)

Options:
  -o, --output TEXT       Output file path
                          (default: ./client.ts for typescript,
                                    ./server.go  for go-gorilla)
  -l, --language TEXT     Target language: typescript | go-gorilla
                          (default: typescript)
  -c, --class-name TEXT   [TypeScript only] Client class name (default: RPCClient)
  -p, --package-name TEXT [Go only] Go package name (default: main)
  -h, --help              Show help message
```

### Examples

The repository includes two example OpenRPC specifications:

1. **[example-spec.json](examples/example-spec.json)** — Basic CRUD operations
2. **[example-spec-advanced.json](examples/example-spec-advanced.json)** — Comprehensive spec demonstrating:
   - paramStructure (positional and named params)
   - Typed error definitions
   - Content Descriptor `$ref`s
   - Tags for organization
   - Server configuration with variables
   - Notification methods
   - Deprecated methods

```bash
# TypeScript
uv run py-openrpc-generator generate examples/example-spec.json          -o examples/generated-client.ts
uv run py-openrpc-generator generate examples/example-spec-advanced.json -o examples/advanced-client.ts

# Go
uv run py-openrpc-generator generate examples/example-spec.json          -l go-gorilla -o examples/example-server.go
uv run py-openrpc-generator generate examples/example-spec-advanced.json -l go-gorilla -o examples/advanced-server.go
```

---

## TypeScript Client

### Using the Generated Client

```typescript
import { RPCClient, UserNotFoundError } from './generated-client';

const client = new RPCClient('https://api.example.com/rpc');

try {
  const user = await client.user_getById({ userId: '123' });
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
  age: 30  // optional
});

// Positional parameters (paramStructure: "by-position")
const sum = await client.math_add([5, 3]);

// Notification (fire-and-forget)
client.notifications_subscribe({ channel: 'users' });
```

### TypeScript Typed Error Handling

```typescript
try {
  const user = await client.user_getById({ userId: 'invalid' });
} catch (error) {
  if (error instanceof UserNotFoundError) {
    console.error('User not found:', error.code);        // 1001
  } else if (error instanceof InvalidUserIdFormatError) {
    console.error('Invalid ID format:', error.code);    // 1004
  } else if (error instanceof JsonRpcError) {
    console.error('JSON-RPC error:', error.code, error.message);
  }
}
```

---

## Go Gorilla RPC Server

### Generated Output

For an OpenRPC spec with a `user.getById` method, the generator produces:

```go
// UserServiceGetByIdArgs contains the arguments for user.getById.
type UserServiceGetByIdArgs struct {
    // The unique identifier of the user
    UserID string `json:"userId"`
}

// UserServiceGetByIdReply contains the result for user.getById.
type UserServiceGetByIdReply = User

// UserService implements the "user" RPC service.
type UserService struct{}

// GetById handles user.getById.
// Get user by ID
//
// Retrieves a user object by their unique identifier
func (s *UserService) GetById(r *http.Request, args *UserServiceGetByIdArgs, reply *UserServiceGetByIdReply) error {
    // TODO: implement user.getById
    return nil
}

func main() {
    server := rpc.NewServer()
    server.RegisterCodec(json2.NewCodec(), "application/json")

    if err := server.RegisterService(new(UserService), "user"); err != nil {
        log.Fatal(err)
    }

    http.Handle("/rpc", server)
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

### Implementing Handlers

Fill in the `// TODO: implement` stubs with your logic:

```go
func (s *UserService) GetById(r *http.Request, args *UserServiceGetByIdArgs, reply *UserServiceGetByIdReply) error {
    user, err := db.FindUser(args.UserID)
    if err != nil {
        return NewUserNotFoundError(nil) // typed error from spec
    }
    *reply = UserServiceGetByIdReply(*user)
    return nil
}
```

### Method Name Mapping

Gorilla RPC maps JSON-RPC method names to Go exported methods. The json2 codec
performs **case-insensitive** matching, so the OpenRPC method name `"user.getById"`
matches the registered Go method `user.GetById`.

| OpenRPC method | Go service | Registered as | Go handler |
|---|---|---|---|
| `user.getById` | `UserService` | `"user"` | `(*UserService).GetById` |
| `math.add` | `MathService` | `"math"` | `(*MathService).Add` |
| `ping` | `DefaultService` | `""` (type name used) | `(*DefaultService).Ping` |

### Go Error Handling

The generator creates typed error structs for each error definition in the spec:

```go
// Return a typed error from a handler
func (s *UserService) GetById(r *http.Request, args *UserServiceGetByIdArgs, reply *UserServiceGetByIdReply) error {
    return NewUserNotFoundError(nil)      // error code 1001
}

// With additional data
return NewUserNotFoundError(map[string]string{"id": args.UserID})
```

---

## Advanced Features

### Content Descriptor References

Reuse parameter definitions across methods:

```json
{
  "params": [{ "$ref": "#/components/contentDescriptors/UserId" }],
  "components": {
    "contentDescriptors": {
      "UserId": { "name": "userId", "required": true, "schema": { "type": "string" } }
    }
  }
}
```

### paramStructure

```typescript
// by-name (default) — object
await client.user_create({ name: 'John', email: 'john@example.com' });

// by-position — tuple
await client.math_add([5, 3]);
```

For Go, positional params are generated as a regular struct with a comment
noting that custom `json.Unmarshaler` may be needed for array encoding.

### Notification Methods

Methods without a `result` field are notifications (fire-and-forget):

```typescript
client.notifications_subscribe({ channel: 'users' }); // no await needed
```

In Go, notifications still get a handler with an empty reply struct. The
server simply won't send any meaningful response body.

### Tag-Based Organization (TypeScript)

Methods are organized by OpenRPC tags with section headers in the generated class:

```typescript
// --------------------------------------------------------------------------
// Users
// --------------------------------------------------------------------------
async user_getById(params: User_getByIdParams): Promise<User> { ... }
async user_create(params: User_createParams): Promise<User> { ... }
```

### Deprecation Warnings

TypeScript uses `@deprecated` JSDoc. Go uses the conventional `// Deprecated:` doc comment:

```go
// Deprecated: Update user (DEPRECATED). Updates an existing user. Use user.patch instead.
// Update handles user.update.
func (s *UserService) Update(r *http.Request, ...) error { ... }
```

### Server URL / Port

The first server entry in the spec is used. For TypeScript, the URL becomes
the default constructor argument. For Go, the port is extracted (defaults to 8080).

---

## Supported OpenRPC Features

### Fully Supported ✓
- **Info object** — title, version, description
- **Methods** — parameters and results
- **JSON Schema types** — object, array, string, number, integer, boolean, null
- **Required / optional parameters** — pointer types and `omitempty` in Go; `?` in TypeScript
- **`$ref` resolution** — schemas, contentDescriptors, errors
- **Enums** — TypeScript union literals; `string` with comment in Go
- **oneOf / anyOf** — union types (TS) / `interface{}` (Go)
- **allOf** — intersection types (TS) / merged struct (Go)
- **Nested objects** — named sub-types in Go; inline or named in TS
- **Arrays of objects** — named item types in Go (`XxxItem`)
- **Method descriptions** — JSDoc (TS) / Go doc comments
- **paramStructure** — by-position, by-name, either
- **Deprecated fields** — `@deprecated` JSDoc (TS) / `// Deprecated:` (Go)
- **Error definitions** — typed error classes (TS) / typed structs (Go)
- **Content Descriptors** — `$ref` resolution
- **Tags** — method organization (TS) / service grouping by namespace prefix (Go)
- **Server objects** — default URL (TS) / port extraction (Go)
- **Notification methods** — fire-and-forget (no result)

### Partially Supported ⚠️
- **Format strings** — preserved in schemas but not validated
- **Server variables** — default substitution only
- **Info contact / license** — parsed but not in output

### Not Yet Supported ✗
- **Links between methods** — runtime expressions
- **Examples** — Example Pairing Objects
- **Advanced JSON Schema** — pattern, minimum/maximum, format validation
- **Recursive schemas** — may cause issues with circular references
- **Multiple servers** — only the first server is used

---

## Project Structure

```
py-openrpc-generator/
├── src/
│   └── py_openrpc_generator/
│       ├── __init__.py
│       ├── cli.py                            # CLI entry point
│       ├── generators/
│       │   ├── base.py                       # Language-agnostic OpenRPC parser
│       │   ├── typescript_converter.py       # JSON Schema → TypeScript types
│       │   ├── typescript.py                 # TypeScript client generator
│       │   ├── golang_converter.py           # JSON Schema → Go types
│       │   └── golang.py                     # Go Gorilla RPC server generator
│       └── templates/
│           ├── typescript-client.ts.jinja2   # TypeScript client template
│           └── golang-gorilla-server.go.jinja2  # Go server template
├── examples/
│   ├── example-spec.json                     # Basic OpenRPC spec
│   ├── example-spec-advanced.json            # Advanced OpenRPC spec
│   ├── generated-client.ts                   # Generated TypeScript (basic)
│   ├── advanced-client.ts                    # Generated TypeScript (advanced)
│   ├── example-server.go                     # Generated Go server (basic)
│   └── advanced-server.go                    # Generated Go server (advanced)
├── pyproject.toml
├── LICENSE
└── README.md
```

## Development

### Testing the Generators

```bash
# TypeScript
uv run py-openrpc-generator generate examples/example-spec.json -o /tmp/client.ts
uv run py-openrpc-generator generate examples/example-spec-advanced.json -o /tmp/advanced-client.ts

# Go
uv run py-openrpc-generator generate examples/example-spec.json -l go-gorilla -o /tmp/server.go
uv run py-openrpc-generator generate examples/example-spec-advanced.json -l go-gorilla -o /tmp/advanced-server.go

# Validate Go syntax
gofmt -e /tmp/server.go
gofmt -e /tmp/advanced-server.go
```

### Adding Support for a New Language

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full walkthrough.

## Dependencies

- Python >= 3.14
- jinja2 >= 3.1.6
- uv (for package management)

## License

BSD 2-Clause License — see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please submit a Pull Request.

For architecture details and how to add new language targets, see [ARCHITECTURE.md](ARCHITECTURE.md).
