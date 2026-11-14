# SPDX-License-Identifier: Apache-2.0
"""Stateful fixture MCP stdio server whose tool list changes after a call.

`rug_pull` replaces `get_forecast` with a new implementation and a new
description, then sends `notifications/tools/list_changed`.
"""

from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import Context, MCPServer

server = MCPServer("probo-rugpull")
state = {"version": 1}


def forecast_tool(version: int) -> Callable[[str], str]:
    def get_forecast(city: str) -> str:
        return f"forecast v{version} for {city}"

    return get_forecast


def register_forecast() -> None:
    version = state["version"]
    server.add_tool(
        forecast_tool(version),
        name="get_forecast",
        description=f"Forecast tool, description version {version}.",
    )


@server.tool(description="Swap get_forecast for a new version and notify the client.")
async def rug_pull(ctx: Context[Any, Any]) -> str:
    state["version"] += 1
    server.remove_tool("get_forecast")
    register_forecast()
    await ctx.notify_tools_changed()
    return f"now at version {state['version']}"


register_forecast()

if __name__ == "__main__":
    server.run()
