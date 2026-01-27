from pathlib import Path
from typing import Any, Dict, List
from jinja2 import Environment, PackageLoader, select_autoescape
from .base import OpenRPCSpec
from .typescript_converter import TypeScriptConverter


class TypeScriptGenerator:
    """Generates TypeScript client from OpenRPC spec."""

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("py_openrpc_generator", "templates"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self, spec: OpenRPCSpec, output_path: str, class_name: str = "RPCClient"
    ) -> None:
        """Generate TypeScript client file."""
        template = self.env.get_template("typescript-client.ts.jinja2")

        # Initialize TypeScript converter
        converter = TypeScriptConverter(spec.components)

        # Process methods to generate types
        methods = self._process_methods(spec.get_method_list(), converter)

        # Process errors to generate error types
        error_types = self._process_errors(methods)

        # Get default server URL
        default_server_url = self._get_default_server_url(spec.servers)

        # Organize methods by tags
        methods_by_tag = self._organize_methods_by_tag(methods)

        # Prepare template context
        context = {
            "info": spec.info,
            "methods": methods,
            "class_name": class_name,
            "type_definitions": converter.get_all_type_definitions(),
            "error_types": error_types,
            "default_server_url": default_server_url,
            "methods_by_tag": methods_by_tag,
            "has_tags": len(methods_by_tag) > 0,
        }

        # Render template
        output = template.render(**context)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)

        print(f"Generated TypeScript client: {output_path}")

    def _process_methods(
        self, methods: List[Dict[str, Any]], converter: TypeScriptConverter
    ) -> List[Dict[str, Any]]:
        """Process methods to generate TypeScript types for params and results."""
        processed_methods = []

        for method in methods:
            method_name = method["name"]
            safe_name = method_name.replace(".", "_")
            param_structure = method.get("param_structure", "either")

            # Process parameters
            params_list = method.get("params", [])
            params_type = None
            params_interface_name = None
            is_positional = param_structure == "by-position"

            if params_list:
                if is_positional:
                    # Generate tuple type for positional params
                    param_types = []
                    for param in params_list:
                        param_type = converter.convert_schema(param["schema"])
                        if not param.get("required", False):
                            param_type += " | undefined"
                        param_types.append(param_type)
                    params_type = f"[{', '.join(param_types)}]"
                else:
                    # Generate object type for named params (by-name or either)
                    properties = {}
                    required = []

                    for param in params_list:
                        param_name = param["name"]
                        properties[param_name] = param["schema"]
                        if param.get("required", False):
                            required.append(param_name)

                    params_schema = {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }

                    # Generate type for params
                    params_interface_name = f"{self._capitalize(safe_name)}Params"
                    params_type = converter.convert_schema(params_schema, params_interface_name)

            # Process result
            result = method.get("result")
            is_notification = result is None
            result_type = "void" if is_notification else "any"

            if result:
                result_schema = result.get("schema", {})
                if result_schema:
                    result_interface_name = f"{self._capitalize(safe_name)}Result"
                    result_type = converter.convert_schema(result_schema, result_interface_name)

            processed_method = {
                **method,
                "safe_name": safe_name,
                "params_type": params_type,
                "params_interface_name": params_interface_name,
                "result_type": result_type,
                "has_params": bool(params_list),
                "is_positional": is_positional,
                "is_notification": is_notification,
            }

            processed_methods.append(processed_method)

        return processed_methods

    def _capitalize(self, name: str) -> str:
        """Capitalize first letter of name."""
        return name[0].upper() + name[1:] if name else name

    def _process_errors(self, methods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and deduplicate error definitions from all methods."""
        errors_map = {}

        for method in methods:
            for error in method.get("errors", []):
                code = error.get("code")
                if code is not None and code not in errors_map:
                    # Create a safe class name from the message
                    message = error.get("message", "")
                    class_name = self._error_code_to_class_name(code, message)
                    errors_map[code] = {
                        "code": code,
                        "message": message,
                        "class_name": class_name,
                        "data": error.get("data"),
                    }

        return list(errors_map.values())

    def _error_code_to_class_name(self, code: int, message: str) -> str:
        """Convert error code and message to a TypeScript class name."""
        # Try to derive from message
        if message:
            # Remove special characters and convert to PascalCase
            words = "".join(c if c.isalnum() else " " for c in message).split()
            class_name = "".join(word.capitalize() for word in words)
            if class_name:
                return f"{class_name}Error"

        # Fallback to code-based name
        return f"Error{code}"

    def _get_default_server_url(self, servers: List[Dict[str, Any]]) -> str:
        """Get the default server URL from the servers array."""
        if servers and len(servers) > 0:
            first_server = servers[0]
            url = first_server.get("url", "")

            # Handle server variables (simple replacement with defaults)
            variables = first_server.get("variables", {})
            for var_name, var_def in variables.items():
                default_value = var_def.get("default", "")
                url = url.replace(f"{{{var_name}}}", default_value)

            return url

        return ""

    def _organize_methods_by_tag(
        self, methods: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Organize methods by their tags."""
        methods_by_tag = {}

        for method in methods:
            tags = method.get("tags", [])
            if not tags:
                # Add to "Untagged" category
                if "Untagged" not in methods_by_tag:
                    methods_by_tag["Untagged"] = []
                methods_by_tag["Untagged"].append(method)
            else:
                for tag in tags:
                    # Handle both Tag Objects and string references
                    tag_name = tag if isinstance(tag, str) else tag.get("name", "Unknown")
                    if tag_name not in methods_by_tag:
                        methods_by_tag[tag_name] = []
                    methods_by_tag[tag_name].append(method)

        return methods_by_tag
