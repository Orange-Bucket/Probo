# SPDX-License-Identifier: Apache-2.0
"""Benign fixture MCP stdio server on the mcp 2.x SDK, exposing one tool."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

server = MCPServer("probo-benign")


@server.tool(
    description=(
        "Return the weather forecast for a city.\n\n"
        "<note>Multi-line text and markup in this description must reach the model "
        "unchanged.</note>"
    )
)
def get_forecast(city: Annotated[str, Field(description="Name of the city to look up.")]) -> str:
    return f"Forecast for {city}: sunny, 21C"


if __name__ == "__main__":
    server.run()
