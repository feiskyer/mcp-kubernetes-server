"""
The mcp-kubernetes-server is a Model Context Protocol (MCP) server that enables
AI assistants to interact with Kubernetes clusters. It serves as a bridge between
AI tools (like Claude, Cursor, and GitHub Copilot) and Kubernetes, translating
natural language requests into Kubernetes operations and returning the results
in a format the AI tools can understand.
"""

from .main import server


def main():
    """Main entry point for the mcp_kubernetes_server module."""
    server()


__all__ = [
    "main",
    "server",
]
