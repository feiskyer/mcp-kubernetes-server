# mcp-kubernetes-server

[![PyPI version](https://img.shields.io/pypi/v/mcp-kubernetes-server.svg)](https://pypi.org/project/mcp-kubernetes-server) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE) [![Build Status](https://github.com/feiskyer/mcp-kubernetes-server/actions/workflows/build.yml/badge.svg)](https://github.com/feiskyer/mcp-kubernetes-server/actions/workflows/build.yml)

The `mcp-kubernetes-server` is a server implementing the Model Context Protocol (MCP) to enable AI assistants (such as Claude, Cursor, and GitHub Copilot) to interact with Kubernetes clusters. It acts as a bridge, translating natural language requests from these assistants into Kubernetes operations and returning the results.

It allows AI assistants to:

- Query Kubernetes resources
- Execute kubectl commands
- Manage Kubernetes clusters through natural language interactions
- Diagnose and interpret the states of Kubernetes resources

## How It Works

The `mcp-kubernetes-server` acts as an intermediary between AI assistants (that support the Model Context Protocol) and your Kubernetes cluster. It receives natural language requests from these assistants, translates them into `kubectl` commands or direct Kubernetes API calls, and executes them against the target cluster. The server then processes the results and returns a structured response, enabling seamless interaction with your Kubernetes environment via the AI assistant.

![](https://github.com/feiskyer/mcp-kubernetes-server/blob/main/assets/mcp-kubernetes-server.png?raw=true)

## How To Install

### Prerequisites

Before installing `mcp-kubernetes-server`, ensure you have the following:

*   A working Kubernetes cluster.
*   A `kubeconfig` file correctly configured to access your Kubernetes cluster (the server requires this file for interaction).
*   The `kubectl` command-line tool installed and in your system's PATH (used by the server to execute many Kubernetes commands).
*   The `helm` command-line tool installed and in your system's PATH (used by the server for Helm chart operations).
*   Python >= 3.11, if you plan to install and run the server directly using `uvx` (without Docker).

### Docker

Get your kubeconfig file for your Kubernetes cluster and setup in the mcpServers (replace src path with your kubeconfig path):

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount", "type=bind,src=/home/username/.kube/config,dst=/home/mcp/.kube/config",
        "ghcr.io/feiskyer/mcp-kubernetes-server"
      ]
    }
  }
}
```

### UVX

To run the server using `uvx` (a tool included with `uv`, the Python packager), first ensure `uv` is installed:

<details>

<summary>Install uv</summary>

Install [uv](https://docs.astral.sh/uv/getting-started/installation/#installation-methods) if it's not installed yet and add it to your PATH, e.g. using curl:

```bash
# For Linux and MacOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

</details>

<details>

<summary>Install kubectl</summary>

Install [kubectl](https://kubernetes.io/docs/tasks/tools/) if it's not installed yet and add it to your PATH, e.g.

```bash
# For Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# For MacOS
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/arm64/kubectl"
```

</details>

<details>
<summary>Install helm</summary>

Install [helm](https://helm.sh/docs/intro/install/) if it's not installed yet and add it to your PATH, e.g.

```bash
curl -sSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

</details>

<br/>

Config your MCP servers in [Claude Desktop](https://claude.ai/download), [Cursor](https://www.cursor.com/), [ChatGPT Copilot](https://marketplace.visualstudio.com/items?itemName=feiskyer.chatgpt-copilot), [Github Copilot](https://github.com/features/copilot) and other supported AI clients, e.g.

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "uvx",
      "args": [
        "mcp-kubernetes-server"
      ],
      "env": {
        "KUBECONFIG": "<your-kubeconfig-path>"
      }
    }
  }
}
```

### MCP Server Options

<details>

<summary>Environment Variables</summary>

**Environment variables:**

- `KUBECONFIG`: Path to your kubeconfig file, e.g. `/home/<username>/.kube/config`.

</details>

<details>

<summary>Command line arguments</summary>

**Command-line Arguments:**

```sh
usage: main.py [-h] [--disable-kubectl] [--disable-helm] [--disable-write]
               [--disable-delete] [--transport {stdio,sse,streamable-http}]
               [--host HOST] [--port PORT]

MCP Kubernetes Server

options:
  -h, --help            show this help message and exit
  --disable-kubectl     Disable kubectl command execution
  --disable-helm        Disable helm command execution
  --disable-write       Disable write operations
  --disable-delete      Disable delete operations
  --transport {stdio,sse,streamable-http}
                        Transport mechanism to use (stdio or sse or streamable-http)
  --host HOST           Host to use for sse or streamable-http server
  --port PORT           Port to use for sse or streamable-http server
```

</details>

## Usage

Once the `mcp-kubernetes-server` is installed and configured in your AI client (using the JSON snippets provided in the 'How to install' section for Docker or UVX), you can start interacting with your Kubernetes cluster through natural language. For example, you can ask:

```txt
What is the status of my Kubernetes cluster?

What is wrong with my nginx pod?
```

**Verifying the server:** If you're running the server with `stdio` transport (common for `uvx` direct execution), the AI client will typically start and manage the server process. For `sse` or `streamable-http` transports, the server runs independently. You would have started it manually (e.g., `uvx mcp-kubernetes-server --transport sse`) and should see output in your terminal indicating it's running (e.g., `INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`). You can also check for any error messages in the server terminal if the AI client fails to connect.

## Available Tools

The mcp-kubernetes-server provides a comprehensive set of tools for interacting with Kubernetes clusters, categorized by operation type:

<details>

<summary>Command Tools</summary>

### Command Tools

These tools provide general command execution capabilities:

| Tool | Description | Parameters |
|------|-------------|------------|
| **kubectl** | Run any kubectl command and return the output | `command` (string) |
| **helm** | Run any helm command and return the output | `command` (string) |

</details>

<details>

<summary>Read Tools</summary>

### Read Tools

These tools provide read-only access to Kubernetes resources:

| Tool | Description | Parameters |
|------|-------------|------------|
| **k8s_get** | Fetch any Kubernetes object (or list) as JSON string | `resource` (string), `name` (string), `namespace` (string) |
| **k8s_describe** | Show detailed information about a specific resource or group of resources | `resource_type` (string), `name` (string, optional), `namespace` (string, optional), `selector` (string, optional), `all_namespaces` (boolean, optional) |
| **k8s_logs** | Print the logs for a container in a pod | `pod_name` (string), `container` (string, optional), `namespace` (string, optional), `tail` (integer, optional), `previous` (boolean, optional), `since` (string, optional), `timestamps` (boolean, optional), `follow` (boolean, optional) |
| **k8s_events** | List events in the cluster | `namespace` (string, optional), `all_namespaces` (boolean, optional), `field_selector` (string, optional), `resource_type` (string, optional), `resource_name` (string, optional), `sort_by` (string, optional), `watch` (boolean, optional) |
| **k8s_apis** | List all available APIs in the Kubernetes cluster | none |
| **k8s_crds** | List all Custom Resource Definitions (CRDs) in the Kubernetes cluster | none |
| **k8s_top_nodes** | Display resource usage (CPU/memory) of nodes | `sort_by` (string, optional) |
| **k8s_top_pods** | Display resource usage (CPU/memory) of pods | `namespace` (string, optional), `all_namespaces` (boolean, optional), `sort_by` (string, optional), `selector` (string, optional) |
| **k8s_rollout_status** | Get the status of a rollout for a deployment, daemonset, or statefulset | `resource_type` (string), `name` (string), `namespace` (string, optional) |
| **k8s_rollout_history** | Get the rollout history for a deployment, daemonset, or statefulset | `resource_type` (string), `name` (string), `namespace` (string, optional), `revision` (string, optional) |
| **k8s_auth_can_i** | Check whether an action is allowed | `verb` (string), `resource` (string), `subresource` (string, optional), `namespace` (string, optional), `name` (string, optional) |
| **k8s_auth_whoami** | Show the subject that you are currently authenticated as | none |

</details>

<details>

<summary>Write Tools</summary>

### Write Tools

These tools provide create, update or patch operations to Kubernetes resources:

| Tool | Description | Parameters |
|------|-------------|------------|
| **k8s_create** | Create a Kubernetes resource from YAML/JSON content | `yaml_content` (string), `namespace` (string, optional) |
| **k8s_apply** | Apply a configuration to a resource by filename or stdin | `yaml_content` (string), `namespace` (string, optional) |
| **k8s_expose** | Expose a resource as a new Kubernetes service | `resource_type` (string), `name` (string), `port` (integer), `target_port` (integer, optional), `namespace` (string, optional), `protocol` (string, optional), `service_name` (string, optional), `labels` (object, optional), `selector` (string, optional), `type` (string, optional) |
| **k8s_run** | Create and run a particular image in a pod | `name` (string), `image` (string), `namespace` (string, optional), `command` (array, optional), `env` (object, optional), `labels` (object, optional), `restart` (string, optional) |
| **k8s_set_resources** | Set resource limits and requests for containers | `resource_type` (string), `resource_name` (string), `namespace` (string, optional), `containers` (array, optional), `limits` (object, optional), `requests` (object, optional) |
| **k8s_set_image** | Set the image for a container | `resource_type` (string), `resource_name` (string), `container` (string), `image` (string), `namespace` (string, optional) |
| **k8s_set_env** | Set environment variables for a container | `resource_type` (string), `resource_name` (string), `container` (string), `env_dict` (object), `namespace` (string, optional) |
| **k8s_rollout_undo** | Undo a rollout for a deployment, daemonset, or statefulset | `resource_type` (string), `name` (string), `namespace` (string, optional), `to_revision` (string, optional) |
| **k8s_rollout_restart** | Restart a rollout for a deployment, daemonset, or statefulset | `resource_type` (string), `name` (string), `namespace` (string, optional) |
| **k8s_rollout_pause** | Pause a rollout for a deployment, daemonset, or statefulset | `resource_type` (string), `name` (string), `namespace` (string, optional) |
| **k8s_rollout_resume** | Resume a rollout for a deployment, daemonset, or statefulset | `resource_type` (string), `name` (string), `namespace` (string, optional) |
| **k8s_scale** | Scale a resource | `resource_type` (string), `name` (string), `replicas` (integer), `namespace` (string, optional) |
| **k8s_autoscale** | Autoscale a deployment, replica set, stateful set, or replication controller | `resource_type` (string), `name` (string), `min` (integer), `max` (integer), `namespace` (string, optional), `cpu_percent` (integer, optional) |
| **k8s_cordon** | Mark a node as unschedulable | `node_name` (string) |
| **k8s_uncordon** | Mark a node as schedulable | `node_name` (string) |
| **k8s_drain** | Drain a node in preparation for maintenance | `node_name` (string), `force` (boolean, optional), `ignore_daemonsets` (boolean, optional), `delete_local_data` (boolean, optional), `timeout` (integer, optional) |
| **k8s_taint** | Update the taints on one or more nodes | `node_name` (string), `key` (string), `value` (string, optional), `effect` (string) |
| **k8s_untaint** | Remove the taints from a node | `node_name` (string), `key` (string), `effect` (string, optional) |
| **k8s_exec_command** | Execute a command in a container | `pod_name` (string), `command` (string), `container` (string, optional), `namespace` (string, optional), `stdin` (boolean, optional), `tty` (boolean, optional), `timeout` (integer, optional) |
| **k8s_port_forward** | Forward one or more local ports to a pod | `resource_type` (string), `name` (string), `ports` (array), `namespace` (string, optional), `address` (string, optional) |
| **k8s_cp** | Copy files and directories to and from containers | `src_path` (string), `dst_path` (string), `container` (string, optional), `namespace` (string, optional) |
| **k8s_patch** | Update fields of a resource | `resource_type` (string), `name` (string), `patch` (object), `namespace` (string, optional) |
| **k8s_label** | Update the labels on a resource | `resource_type` (string), `name` (string), `labels` (object), `namespace` (string, optional), `overwrite` (boolean, optional) |
| **k8s_annotate** | Update the annotations on a resource | `resource_type` (string), `name` (string), `annotations` (object), `namespace` (string, optional), `overwrite` (boolean, optional) |

</details>

<details>

<summary>Delete Tools</summary>

### Delete Tools

These tools provide delete operations to Kubernetes resources:

| Tool | Description | Parameters |
|------|-------------|------------|
| **k8s_delete** | Delete resources by name, label selector, or all resources in a namespace | `resource_type` (string), `name` (string, optional), `namespace` (string, optional), `label_selector` (string, optional), `all_namespaces` (boolean, optional), `force` (boolean, optional), `grace_period` (integer, optional) |

</details>

## Development

How to run the project locally:

```sh
uv run -m src.mcp_kubernetes_server.main
```

How to inspect MCP server requests and responses:

```sh
npx @modelcontextprotocol/inspector uv run -m src.mcp_kubernetes_server.main
```

## Troubleshooting

Here are some common issues and their solutions when working with `mcp-kubernetes-server`:

**Issue:** `mcp-kubernetes-server` cannot connect to the Kubernetes cluster or reports authentication errors.
**Solution:**
*   Ensure your `kubeconfig` file is correctly configured and points to the intended cluster.
*   Verify that the path to your `kubeconfig` file is correctly specified in the `mcpServers` configuration (for Docker, ensure the mount path is correct; for `uvx`, ensure the `KUBECONFIG` environment variable is set correctly).
*   Check that the credentials in your `kubeconfig` have the necessary permissions to perform operations on the cluster. You can test this with `kubectl` directly (e.g., `kubectl get pods`).

**Issue:** `kubectl` or `helm` commands return an error like "command not found" or are disabled.
**Solution:**
*   If running via `uvx`, ensure `kubectl` and/or `helm` are installed on your system and available in your PATH. Refer to the "Prerequisites" section for installation guidance.
*   If you see a message like "Write operations are not allowed" or "Delete operations are not allowed", the server might have been started with flags like `--disable-kubectl`, `--disable-helm`, `--disable-write`, or `--disable-delete`. Check the server's startup command and the "MCP Server Options" section in the README for details on these flags.

**Issue:** How can I see the raw requests and responses between my AI client and the `mcp-kubernetes-server`?
**Solution:**
*   You can use the `@modelcontextprotocol/inspector` tool as mentioned in the "Development" section: `npx @modelcontextprotocol/inspector uv run -m src.mcp_kubernetes_server.main`. This will show you the MCP messages being exchanged.

**Issue:** The server starts but the AI client cannot connect.
**Solution:**
*   If using `stdio` transport (default for `uvx` direct execution), ensure your AI client is configured to launch the `mcp-kubernetes-server` command correctly.
*   If using `sse` or `streamable-http` transport, ensure the host and port configured in the `mcp-kubernetes-server` (e.g., `--host 0.0.0.0 --port 8000`) are reachable from where your AI client is running. Check for firewall rules or network configuration issues. Also, verify the AI client is configured with the correct URL for the server.

## Contribution

This project is open source, available on GitHub at [feiskyer/mcp-kubernetes-server](https://github.com/feiskyer/mcp-kubernetes-server) and licensed under the [Apache License](LICENSE).

If you would like to contribute to the project, please follow these guidelines:

1. Fork the repository and clone it to your local machine.
2. Create a new branch for your changes.
3. Make your changes and commit them with a descriptive commit message.
4. Push your changes to your forked repository.
5. Open a pull request to the main repository.

## LICENSE

The project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for more details.
