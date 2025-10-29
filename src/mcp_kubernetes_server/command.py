# -*- coding: utf-8 -*-
import subprocess
from typing import List, Union


class ShellProcess:
    """Wrapper for shell command."""

    def __init__(
        self,
        command: str,
        strip_newlines: bool = False,
        return_err_output: bool = True,
    ):
        """Initialize with explicit command and options."""
        self.strip_newlines = strip_newlines
        self.return_err_output = return_err_output
        self.command = command

    def run(self, args: List[str], input=None) -> str:
        """Run the command with arguments safely (no shell)."""
        if not isinstance(args, list):
            raise ValueError("args must be a list of arguments")
        cmd_list = [self.command] + args
        return self.exec(cmd_list, input=input)

    def exec(self, cmd_list: List[str], input=None) -> str:
        """Run the given command list and return output (no shell)."""
        if not isinstance(cmd_list, list):
            raise ValueError("cmd_list must be a list of arguments")
        try:
            output = subprocess.run(
                cmd_list,
                shell=False,
                check=True,
                input=input,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ).stdout.decode()
        except subprocess.CalledProcessError as error:
            if self.return_err_output and error.stdout:
                return error.stdout.decode()
            return str(error)
        if self.strip_newlines:
            output = output.strip()
        return output
