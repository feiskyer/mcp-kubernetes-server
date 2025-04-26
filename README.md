# mcp-kubernetes-server

The mcp-kubernetes-server is a Model Context Protocol (MCP) server that enables AI assistants to interact with Kubernetes clusters. It serves as a bridge between AI tools (like Claude, Cursor, and GitHub Copilot) and Kubernetes, translating natural language requests into Kubernetes operations and returning the results in a format the AI tools can understand.

It allows AI tools to:

- Query Kubernetes resources
- Execute kubectl commands
- Manage Kubernetes clusters through natural language interactions
- Diagnose and interpret the states of Kubernetes resources

## How it works

![](assets/mcp-kubernetes-server.png)

## How to install

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

### Options

Environment variables:

- `KUBECONFIG`: Path to your kubeconfig file, e.g. `/home/<username>/.kube/config`.

Command line arguments:

```sh
usage: mcp-kubernetes-server [-h] [--disable-kubectl] [--disable-helm] [--transport {stdio,sse}] [--port PORT]

MCP Kubernetes Server

options:
  -h, --help            show this help message and exit
  --disable-kubectl     Disable kubectl command execution
  --disable-helm        Disable helm command execution
  --transport {stdio,sse}
                        Transport mechanism to use (stdio or sse)
  --port PORT           Port to use for the server (only used with sse transport)
```

## Usage

Ask any questions about Kubernetes cluster in your AI client, e.g.

```txt
What is the status of my Kubernetes cluster?

What is wrong with my nginx pod?
```

## Development

How to run the project locally:

```sh
uv run -m src.mcp_kubernetes_server.main
```

How to inspect MCP server requests and responses:

```sh
npx @modelcontextprotocol/inspector uv run -m src.mcp_kubernetes_server.main
```

## Contribution

The project is opensource at github [feiskyer/mcp-kubernetes-server](https://github.com/feiskyer/mcp-kubernetes-server) with [Apache License](LICENSE).

If you would like to contribute to the project, please follow these guidelines:

1. Fork the repository and clone it to your local machine.
2. Create a new branch for your changes.
3. Make your changes and commit them with a descriptive commit message.
4. Push your changes to your forked repository.
5. Open a pull request to the main repository.

## LICENSE

The project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for more details.
