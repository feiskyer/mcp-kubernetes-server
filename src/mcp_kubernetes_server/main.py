# -*- coding: utf-8 -*-
import argparse

from fastmcp import FastMCP

from .auth import k8s_auth_can_i, k8s_auth_whoami
from .command import ShellProcess
from .copy import k8s_cp
from .create import k8s_apply, k8s_create
from .describe import k8s_describe
from .events import k8s_events
from .get import k8s_apis, k8s_crds, k8s_get
from .kubeclient import (
    k8s_annotate,
    k8s_autoscale,
    k8s_cordon,
    k8s_delete,
    k8s_drain,
    k8s_exec_command,
    k8s_expose,
    k8s_label,
    k8s_patch,
    k8s_rollout_resume,
    k8s_run,
    k8s_scale,
    k8s_taint,
    k8s_uncordon,
    k8s_untaint,
    setup_client,
)
from .logs import k8s_logs
from .port_forward import k8s_port_forward
from .rollout import (
    k8s_rollout_history,
    k8s_rollout_pause,
    k8s_rollout_restart,
    k8s_rollout_status,
    k8s_rollout_undo,
)
from .set import (
    k8s_set_env,
    k8s_set_image,
    k8s_set_resources,
)
from .top import k8s_top_nodes, k8s_top_pods

# Initialize FastMCP server
mcp = FastMCP("mcp-kubernetes-server")


def register_read_tools():
    """Register MCP tools for reading Kubernetes resources."""
    mcp.tool()(k8s_apis)
    mcp.tool()(k8s_crds)
    mcp.tool()(k8s_get)
    mcp.tool()(k8s_rollout_status)
    mcp.tool()(k8s_rollout_history)
    mcp.tool()(k8s_top_nodes)
    mcp.tool()(k8s_top_pods)
    mcp.tool()(k8s_describe)
    mcp.tool()(k8s_logs)
    mcp.tool()(k8s_events)
    mcp.tool()(k8s_auth_can_i)
    mcp.tool()(k8s_auth_whoami)


def register_write_tools():
    """Register MCP tools for writing Kubernetes resources."""
    mcp.tool()(k8s_create)
    mcp.tool()(k8s_expose)
    mcp.tool()(k8s_run)
    mcp.tool()(k8s_set_resources)
    mcp.tool()(k8s_set_image)
    mcp.tool()(k8s_set_env)
    mcp.tool()(k8s_rollout_undo)
    mcp.tool()(k8s_rollout_restart)
    mcp.tool()(k8s_rollout_pause)
    mcp.tool()(k8s_rollout_resume)
    mcp.tool()(k8s_scale)
    mcp.tool()(k8s_autoscale)
    mcp.tool()(k8s_cordon)
    mcp.tool()(k8s_uncordon)
    mcp.tool()(k8s_drain)
    mcp.tool()(k8s_taint)
    mcp.tool()(k8s_untaint)
    mcp.tool()(k8s_exec_command)
    mcp.tool()(k8s_port_forward)
    mcp.tool()(k8s_cp)
    mcp.tool()(k8s_apply)
    mcp.tool()(k8s_patch)
    mcp.tool()(k8s_label)
    mcp.tool()(k8s_annotate)


def register_delete_tools():
    """Register MCP tools for deleting Kubernetes resources."""
    mcp.tool()(k8s_delete)


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
