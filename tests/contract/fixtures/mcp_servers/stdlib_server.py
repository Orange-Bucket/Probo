# SPDX-License-Identifier: Apache-2.0
"""Dependency-free MCP stdio server, for images that have Python but no mcp SDK.

Speaks newline-delimited JSON-RPC 2.0 and implements only what an MCP client
needs to list and call one tool: initialize, ping, tools/list and tools/call.
"""

import json
import socket
import sys
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "sandbox_hostname",
        "description": "Report the hostname of the machine running this MCP server.",
        "inputSchema": {"type": "object", "properties": {}},
    }
]


def handle(method: str, params: dict[str, Any]) -> dict[str, Any]:
    if method == "initialize":
        return {
            "protocolVersion": params["protocolVersion"],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "probo-stdlib", "version": "0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call" and params.get("name") == "sandbox_hostname":
        return {"content": [{"type": "text", "text": socket.gethostname()}], "isError": False}
    raise LookupError(method)


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        message: dict[str, Any] = json.loads(line)
        if "id" not in message:
            continue
        reply: dict[str, Any] = {"jsonrpc": "2.0", "id": message["id"]}
        try:
            reply["result"] = handle(message["method"], message.get("params") or {})
        except LookupError:
            reply["error"] = {"code": -32601, "message": f"Method not found: {message['method']}"}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
