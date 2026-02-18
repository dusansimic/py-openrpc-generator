from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from jinja2 import Environment, PackageLoader, select_autoescape
from .base import OpenRPCSpec
from .golang_converter import GolangConverter


class GolangGenerator:
    """Generates Go Gorilla RPC v2 server handler stubs from an OpenRPC spec."""

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("py_openrpc_generator", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        spec: OpenRPCSpec,
        output_path: str,
        package_name: str = "main",
    ) -> None:
        """Generate Go server files from the OpenRPC spec.

        Two files are produced:

        - <output_path>          — types, args/reply structs, and handler
                                   interfaces.  Always regenerated; do not
                                   hand-edit this file.
        - <stem>_main<ext>       — placeholder service structs and main().
                                   Written once; subsequent runs leave it
                                   untouched so hand-written code is safe.
        """
        types_template = self.env.get_template("golang-gorilla-types.go.jinja2")
        main_template = self.env.get_template("golang-gorilla-main.go.jinja2")

        converter = GolangConverter(spec.components)

        # Process methods — builds Go-specific metadata per method
        processed_methods = self._process_methods(spec.get_method_list(), converter)

        # Extract and deduplicate error types
        error_types = self._process_errors(processed_methods)

        # Group methods into services by namespace
        services = self._process_services(processed_methods)

        # Default port from server URL (or 8080)
        default_port = self._get_default_port(spec.servers)

        context = {
            "info": spec.info,
            "package_name": package_name,
            "type_definitions": converter.get_all_type_definitions(),
            "services": services,
            "error_types": error_types,
            "default_port": default_port,
        }

        # Always regenerate the types file.
        types_file = Path(output_path)
        types_file.parent.mkdir(parents=True, exist_ok=True)
        types_file.write_text(types_template.render(**context), encoding="utf-8")
        print(f"Generated Go types/interfaces: {types_file}")

        # Write the main/wiring file only on first run.
        main_file = types_file.parent / f"{types_file.stem}_main{types_file.suffix}"
        if not main_file.exists():
            main_file.write_text(main_template.render(**context), encoding="utf-8")
            print(f"Generated Go server wiring:   {main_file}")
            print(f"  (this file will not be overwritten on future runs)")
        else:
            print(f"Skipped Go server wiring:     {main_file}  (already exists)")

    # -------------------------------------------------------------------------
    # Method processing
    # -------------------------------------------------------------------------

    def _process_methods(
        self,
        methods: List[Dict[str, Any]],
        converter: GolangConverter,
    ) -> List[Dict[str, Any]]:
        """Enrich each method dict with Go-specific fields."""
        processed = []

        for method in methods:
            method_name = method["name"]
            namespace, suffix = self._extract_namespace(method_name)
            service_name = self._namespace_to_service(namespace)
            go_method = self._suffix_to_go_method(suffix)

            args_type = f"{service_name}{go_method}Args"
            reply_type = f"{service_name}{go_method}Reply"

            params = method.get("params", [])
            result = method.get("result")
            is_notification = result is None
            param_structure = method.get("param_structure", "either")
            is_positional = param_structure == "by-position"

            # Build args struct fields (pass args_type for nested object naming)
            args_fields = self._build_args_fields(params, converter, is_positional, args_type)

            # Determine reply type
            reply_inline_type: Optional[str] = None
            reply_fields: List[Dict[str, Any]] = []
            reply_is_alias = False
            result_struct_name = f"{service_name}{go_method}Result"

            if result and not is_notification:
                result_schema = result.get("schema", {})
                if result_schema:
                    if "$ref" in result_schema:
                        # Alias to the referenced named type
                        ref_type = converter.resolve_ref(result_schema["$ref"])
                        reply_inline_type = ref_type
                        reply_is_alias = True
                    elif result_schema.get("type") == "object":
                        # Generate a named result struct
                        reply_inline_type = converter.convert_schema(
                            result_schema, result_struct_name
                        )
                        reply_is_alias = True
                    elif result_schema.get("type") == "array":
                        # Wrap array in a named result struct with an Items field
                        item_type = converter.convert_schema(result_schema)
                        if result_struct_name not in converter.generated_types:
                            converter.generated_types.add(result_struct_name)
                            struct_def = (
                                f"type {result_struct_name} struct {{\n"
                                f'\tItems {item_type} `json:"items"`\n'
                                f"}}"
                            )
                            converter.type_definitions.append(struct_def)
                        reply_inline_type = result_struct_name
                        reply_is_alias = True
                    else:
                        # Scalar type — wrap in a named result struct
                        go_type = converter.convert_schema(result_schema)
                        if result_struct_name not in converter.generated_types:
                            converter.generated_types.add(result_struct_name)
                            struct_def = (
                                f"type {result_struct_name} struct {{\n"
                                f'\tResult {go_type} `json:"result"`\n'
                                f"}}"
                            )
                            converter.type_definitions.append(struct_def)
                        reply_inline_type = result_struct_name
                        reply_is_alias = True

            processed.append(
                {
                    **method,
                    "namespace": namespace,
                    "service_name": service_name,
                    "go_method_name": go_method,
                    "args_type": args_type,
                    "reply_type": reply_type,
                    "reply_inline_type": reply_inline_type,
                    "reply_is_alias": reply_is_alias,
                    "args_fields": args_fields,
                    "reply_fields": reply_fields,
                    "has_args": bool(params),
                    "is_notification": is_notification,
                    "is_positional": is_positional,
                }
            )

        return processed

    def _build_args_fields(
        self,
        params: List[Dict[str, Any]],
        converter: GolangConverter,
        is_positional: bool,
        args_type_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build field metadata for an Args struct.

        args_type_name is used to derive named types for nested object params
        (e.g. UserServiceUpdateArgs + Data -> UserServiceUpdateArgsData).
        """
        fields = []
        for param in params:
            json_name = param["name"]
            is_required = param.get("required", False)
            go_name = converter.go_field_name(json_name)
            schema = param.get("schema", {})

            # Delegate to the converter's field type logic which handles
            # nested objects and arrays-of-objects with named sub-types.
            go_type = converter._field_go_type(schema, go_name, args_type_name)

            if not is_required and not go_type.startswith(("*", "[]", "map[", "interface")):
                go_type = f"*{go_type}"

            omitempty = "" if is_required else ",omitempty"

            fields.append(
                {
                    "json_name": json_name,
                    "go_name": go_name,
                    "go_type": go_type,
                    "required": is_required,
                    "tag": f'`json:"{json_name}{omitempty}"`',
                    "description": param.get("description", ""),
                }
            )
        return fields

    # -------------------------------------------------------------------------
    # Service grouping
    # -------------------------------------------------------------------------

    def _process_services(
        self, processed_methods: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Group methods into service dicts by namespace."""
        service_map: Dict[str, Dict[str, Any]] = {}

        for method in processed_methods:
            ns = method["namespace"]
            svc_name = method["service_name"]

            if ns not in service_map:
                service_map[ns] = {
                    "name": svc_name,
                    "namespace": ns,
                    "methods": [],
                }
            service_map[ns]["methods"].append(method)

        # Stable ordering: non-default services first, default last
        services = []
        default_svc = None
        for ns, svc in service_map.items():
            if ns == "default":
                default_svc = svc
            else:
                services.append(svc)

        services.sort(key=lambda s: s["name"])
        if default_svc:
            services.append(default_svc)

        return services

    # -------------------------------------------------------------------------
    # Error processing
    # -------------------------------------------------------------------------

    def _process_errors(
        self, processed_methods: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract unique error definitions from all methods."""
        errors_map: Dict[int, Dict[str, Any]] = {}

        for method in processed_methods:
            for error in method.get("errors", []):
                code = error.get("code")
                if code is not None and code not in errors_map:
                    message = error.get("message", "")
                    struct_name = self._error_to_struct_name(code, message)
                    errors_map[code] = {
                        "code": code,
                        "message": message,
                        "struct_name": struct_name,
                    }

        return list(errors_map.values())

    def _error_to_struct_name(self, code: int, message: str) -> str:
        """Derive a Go struct name for an error from its code and message."""
        if message:
            words = "".join(c if c.isalnum() else " " for c in message).split()
            name = "".join(w.capitalize() for w in words)
            if name:
                return f"{name}Error"
        return f"RPCError{code}"

    # -------------------------------------------------------------------------
    # Naming helpers
    # -------------------------------------------------------------------------

    def _extract_namespace(self, method_name: str) -> Tuple[str, str]:
        """Split 'user.getById' into ('user', 'getById').

        Methods without a dot belong to the 'default' namespace.
        """
        if "." in method_name:
            parts = method_name.split(".", 1)
            return parts[0], parts[1]
        return "default", method_name

    def _namespace_to_service(self, namespace: str) -> str:
        """Convert a namespace to a Go service struct name.

        Examples:
            user    -> UserService
            default -> DefaultService
        """
        return namespace.capitalize() + "Service"

    def _suffix_to_go_method(self, suffix: str) -> str:
        """Convert a method suffix to an exported Go method name.

        Examples:
            getById -> GetById
            create  -> Create
            list    -> List
        """
        if not suffix:
            return "Handle"

        # Handle dot-separated sub-suffixes (e.g. "query.advanced")
        if "." in suffix:
            parts = suffix.split(".")
            return "".join(self._capitalize_first(p) for p in parts)

        return self._capitalize_first(suffix)

    def _capitalize_first(self, s: str) -> str:
        """Capitalize the first character of a string."""
        if not s:
            return s
        return s[0].upper() + s[1:]

    # -------------------------------------------------------------------------
    # Server helpers
    # -------------------------------------------------------------------------

    def _get_default_port(self, servers: List[Dict[str, Any]]) -> str:
        """Extract the port from the first server URL, defaulting to 8080."""
        if not servers:
            return "8080"

        url = servers[0].get("url", "")

        # Apply variable defaults
        variables = servers[0].get("variables", {})
        for var_name, var_def in variables.items():
            default_value = var_def.get("default", "")
            url = url.replace(f"{{{var_name}}}", default_value)

        # Try to parse port from URL
        import re
        match = re.search(r":(\d+)(?:/|$)", url)
        if match:
            return match.group(1)

        # Standard ports from scheme
        if url.startswith("https://"):
            return "443"
        if url.startswith("http://"):
            return "80"

        return "8080"
