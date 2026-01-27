import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class OpenRPCSpec:
    """Represents a parsed OpenRPC specification."""

    def __init__(self, spec_data: Dict[str, Any]):
        self.raw = spec_data
        self.openrpc = spec_data.get("openrpc", "")
        self.info = spec_data.get("info", {})
        self.methods = spec_data.get("methods", [])
        self.components = spec_data.get("components", {})
        self.servers = spec_data.get("servers", [])
        self.external_docs = spec_data.get("externalDocs")

    @classmethod
    def from_file(cls, file_path: str) -> "OpenRPCSpec":
        """Load OpenRPC spec from a JSON file."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"OpenRPC spec file not found: {file_path}")

        if not path.suffix == ".json":
            raise ValueError("OpenRPC spec must be a JSON file")

        with open(path, "r", encoding="utf-8") as f:
            spec_data = json.load(f)

        # Basic validation
        if "openrpc" not in spec_data:
            raise ValueError("Invalid OpenRPC spec: missing 'openrpc' field")

        if "info" not in spec_data:
            raise ValueError("Invalid OpenRPC spec: missing 'info' field")

        if "methods" not in spec_data:
            raise ValueError("Invalid OpenRPC spec: missing 'methods' field")

        return cls(spec_data)

    def get_method_list(self) -> List[Dict[str, Any]]:
        """Get a list of all methods with their details."""
        methods = []
        for method in self.methods:
            method_info = {
                "name": method.get("name", ""),
                "summary": method.get("summary", ""),
                "description": method.get("description", ""),
                "params": self._parse_params(method.get("params", [])),
                "result": self._parse_result(method.get("result")),
                "errors": self._parse_errors(method.get("errors", [])),
                "deprecated": method.get("deprecated", False),
                "tags": method.get("tags", []),
                "param_structure": method.get("paramStructure", "either"),
                "examples": method.get("examples", []),
                "links": method.get("links", []),
                "external_docs": method.get("externalDocs"),
            }
            methods.append(method_info)
        return methods

    def _parse_params(self, params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse method parameters, resolving Content Descriptor $refs."""
        parsed_params = []
        for param in params:
            # Resolve $ref if present
            if "$ref" in param:
                param = self._resolve_content_descriptor_ref(param["$ref"])

            param_info = {
                "name": param.get("name", ""),
                "summary": param.get("summary", ""),
                "description": param.get("description", ""),
                "required": param.get("required", False),
                "schema": param.get("schema", {}),
                "deprecated": param.get("deprecated", False),
            }
            parsed_params.append(param_info)
        return parsed_params

    def _parse_result(self, result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse method result, resolving Content Descriptor $refs."""
        if not result:
            # No result means this is a notification method
            return None

        # Resolve $ref if present
        if "$ref" in result:
            result = self._resolve_content_descriptor_ref(result["$ref"])

        return {
            "name": result.get("name", "result"),
            "summary": result.get("summary", ""),
            "description": result.get("description", ""),
            "schema": result.get("schema", {}),
            "deprecated": result.get("deprecated", False),
        }

    def _parse_errors(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse method error definitions."""
        parsed_errors = []
        for error in errors:
            # Resolve $ref if present
            if "$ref" in error:
                error = self._resolve_error_ref(error["$ref"])

            error_info = {
                "code": error.get("code"),
                "message": error.get("message", ""),
                "data": error.get("data"),
            }
            parsed_errors.append(error_info)
        return parsed_errors

    def _resolve_content_descriptor_ref(self, ref: str) -> Dict[str, Any]:
        """Resolve a Content Descriptor $ref."""
        if ref.startswith("#/components/contentDescriptors/"):
            name = ref.split("/")[-1]
            content_descriptors = self.components.get("contentDescriptors", {})
            if name in content_descriptors:
                return content_descriptors[name]
        return {}

    def _resolve_error_ref(self, ref: str) -> Dict[str, Any]:
        """Resolve an Error $ref."""
        if ref.startswith("#/components/errors/"):
            name = ref.split("/")[-1]
            errors = self.components.get("errors", {})
            if name in errors:
                return errors[name]
        return {}
