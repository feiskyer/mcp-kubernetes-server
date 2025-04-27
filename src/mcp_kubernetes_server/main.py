# -*- coding: utf-8 -*-
import argparse

from fastmcp import FastMCP

from .auth import auth_can_i, auth_whoami
from .command import ShellProcess
from .copy import cp
from .create import apply, create
from .describe import describe
from .events import events
from .get import apis, crds, get
from .kubeclient import (
    annotate,
    autoscale,
    cordon,
    delete,
    drain,
    exec_command,
    expose,
    label,
    patch,
    port_forward,
    rollout_resume,
    run,
    scale,
    setup_client,
    taint,
    uncordon,
    untaint,
)
from .logs import logs
from .rollout import (
    rollout_history,
    rollout_pause,
    rollout_restart,
    rollout_status,
    rollout_undo,
)
from .set import (
    set_env,
    set_image,
    set_resources,
)
from .top import top_nodes, top_pods

# Initialize FastMCP server
mcp = FastMCP("mcp-kubernetes-server")


def register_read_tools():
    """Register MCP tools for reading Kubernetes resources."""
    mcp.tool()(apis)
    mcp.tool()(crds)
    mcp.tool()(get)
    mcp.tool()(rollout_status)
    mcp.tool()(rollout_history)
    mcp.tool()(top_nodes)
    mcp.tool()(top_pods)
    mcp.tool()(describe)
    mcp.tool()(logs)
    mcp.tool()(events)
    mcp.tool()(auth_can_i)
    mcp.tool()(auth_whoami)


def register_write_tools():
    """Register MCP tools for writing Kubernetes resources."""
    mcp.tool()(create)
    mcp.tool()(expose)
    mcp.tool()(run)
    mcp.tool()(set_resources)
    mcp.tool()(set_image)
    mcp.tool()(set_env)
    mcp.tool()(rollout_undo)
    mcp.tool()(rollout_restart)
    mcp.tool()(rollout_pause)
    mcp.tool()(rollout_resume)
    mcp.tool()(scale)
    mcp.tool()(autoscale)
    mcp.tool()(cordon)
    mcp.tool()(uncordon)
    mcp.tool()(drain)
    mcp.tool()(taint)
    mcp.tool()(untaint)
    mcp.tool()(exec_command)
    mcp.tool()(port_forward)
    mcp.tool()(cp)
    mcp.tool()(apply)
    mcp.tool()(patch)
    mcp.tool()(label)
    mcp.tool()(annotate)


def register_delete_tools():
    """Register MCP tools for deleting Kubernetes resources."""
    mcp.tool()(delete)


def register_kubectl_tool(disable_write, disable_delete):
    """Register MCP tool for executing kubectl commands."""

    async def kubectl(command: str) -> str:
        """Run a kubectl command and return the output."""
        process = ShellProcess(command="kubectl")
        write_operations = [
            "create",
            "apply",
            "edit",
            "patch",
            "replace",
            "scale",
            "autoscale",
            "label",
            "annotate",
            "set",
            "rollout",
            "expose",
            "run",
            "cordon",
            "delete",
            "uncordon",
            "drain",
            "taint",
            "untaint",
            "cp",
            "exec",
            "port-forward",
        ]
        delete_operations = ["delete"]
        unallowed_operations = []
        if disable_delete:
            unallowed_operations.extend(delete_operations)
        if disable_write:
            unallowed_operations.extend(write_operations)
        if len(unallowed_operations) > 0:
            # Extract the first word from the command (the kubectl subcommand)
            cmd_parts = command.strip().split()
            if len(cmd_parts) > 0:
                if cmd_parts[0] == "kubectl":
                    cmd_parts = cmd_parts[1:]
                subcommand = cmd_parts[0]

                # Check if the subcommand is unallwoed operation
                if subcommand in unallowed_operations:
                    return (
                        f"Error: Write operations are not allowed. "
                        f"Cannot execute kubectl {subcommand} command."
                    )

        output = process.run(command)
        return output

    mcp.tool()(kubectl)


def register_helm_tool(disable_write):
    """Register MCP tool for executing helm commands."""

    async def helm(command: str) -> str:
        """Run a helm command and return the output."""
        process = ShellProcess(command="helm")
        if disable_write:
            # Check if the command is a write operation
            write_operations = [
                "install",
                "upgrade",
                "uninstall",
                "rollback",
                "repo add",
                "repo update",
                "repo remove",
                "push",
                "create",
                "dependency update",
                "package",
                "plugin install",
                "plugin uninstall",
            ]

            # Extract the first word or two from the command (the helm subcommand)
            cmd_parts = command.strip().split()
            if len(cmd_parts) > 0:
                if cmd_parts[0] == "helm":
                    cmd_parts = cmd_parts[1:]
                subcommand = cmd_parts[0]

                # Check for two-word commands like "repo add"
                if (
                    len(cmd_parts) > 1
                    and f"{subcommand} {cmd_parts[1]}" in write_operations
                ):
                    return (
                        f"Error: Write operations are not allowed. "
                        f"Cannot execute helm {subcommand} {cmd_parts[1]} command."
                    )

                # Check if the subcommand is a write operation
                if subcommand in write_operations:
                    return (
                        f"Error: Write operations are not allowed. "
                        f"Cannot execute helm {subcommand} command."
                    )

        return process.run(command)

    mcp.tool()(helm)


def server():
    """ "Run the MCP server."""
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
        "--disable-write",
        action="store_true",
        help="Disable write operations",
    )
    parser.add_argument(
        "--disable-delete",
        action="store_true",
        help="Disable delete operations",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],  # TODO: add streamable HTTP
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
    register_read_tools()

    if not args.disable_write:
        register_write_tools()

    if not args.disable_delete:
        register_delete_tools()

    if not args.disable_kubectl:
        register_kubectl_tool(args.disable_write, args.disable_delete)

    if not args.disable_helm:
        register_helm_tool(args.disable_write)

    # Run the server
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    server()
