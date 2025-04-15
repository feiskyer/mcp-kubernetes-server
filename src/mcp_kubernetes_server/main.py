# -*- coding: utf-8 -*-
import argparse
import subprocess
from typing import List, Union
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("mcp-kubernetes-server")

class KubectlProcess:
    """Wrapper for kubectl command."""

    def __init__(
        self,
        command: str = "kubectl",
        strip_newlines: bool = False,
        return_err_output: bool = True,
    ):
        """Initialize with stripping newlines."""
        self.strip_newlines = strip_newlines
        self.return_err_output = return_err_output
        self.command = command

    def run(self, args: Union[str, List[str]], input=None) -> str:
        """Run the command."""
        if isinstance(args, str):
            args = [args]
        commands = ";".join(args)
        if not commands.startswith(self.command):
            commands = f"{self.command} {commands}"

        return self.exec(commands, input=input)

    def exec(self, commands: Union[str, List[str]], input=None) -> str:
        """Run commands and return final output."""
        if isinstance(commands, str):
            commands = [commands]
        commands = ";".join(commands)
        try:
            output = subprocess.run(
                commands,
                shell=True,
                check=True,
                input=input,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ).stdout.decode()
        except subprocess.CalledProcessError as error:
            if self.return_err_output:
                return error.stdout.decode()
            return str(error)
        if self.strip_newlines:
            output = output.strip()
        return output


@mcp.tool()
async def kubectl(command: str) -> str:
    """Run a kubectl command and return the output."""
    process = KubectlProcess()
    output = process.run(command)
    return output


def server():
    # Create argument parser
    parser = argparse.ArgumentParser(description="MCP Kubernetes Server")
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

    # Parse arguments
    args = parser.parse_args()

    # Run with specified transport
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    server()
