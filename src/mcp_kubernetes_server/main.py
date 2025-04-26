# -*- coding: utf-8 -*-
import argparse
from fastmcp import FastMCP
from .kubeclient import setup_client, apis,crds, get
from .command import kubectl, helm


# Initialize FastMCP server
mcp = FastMCP("mcp-kubernetes-server")


def server():
    """"Run the MCP server."""
    parser = argparse.ArgumentParser(description="MCP Kubernetes Server")
    parser.add_argument(
        "--disable-kubectl",
        action="store_true",
        help="Disable kubectl command execution",
    )
    parser.add_argument(
        "--disable-helm",
        action="store_true",
        help="Disable helm command execution",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mechanism to use (stdio or sse)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to use for the server (only used with sse transport)",
    )

    args = parser.parse_args()
    mcp.settings.port = args.port

    # Setup Kubernetes client
    setup_client()

    # Setup tools
    mcp.tool()(apis)
    mcp.tool()(crds)
    mcp.tool()(get)
    if not args.disable_kubectl:
        mcp.tool()(kubectl)
    if not args.disable_helm:
        mcp.tool()(helm)

    # Run the server
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    server()
