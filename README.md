# mcp-kubernetes-server

A Model Context Protocol (MCP) server to enable Claude, Cursor and other AI tools to interact with Kubernetes cluster via kubectl.

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

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/#installation-methods) and add it to your PATH, e.g. using curl:

```bash
# For Linux and MacOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install [kubectl](https://kubernetes.io/docs/tasks/tools/) and add it to your PATH, e.g.

```bash
# For Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# For MacOS
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/arm64/kubectl"
```

3. Config your MCP servers in [Claude Desktop](https://claude.ai/download), [Cursor](https://www.cursor.com/), [ChatGPT Copilot](https://marketplace.visualstudio.com/items?itemName=feiskyer.chatgpt-copilot), [Github Copilot](https://github.com/features/copilot) and other supported AI clients, e.g.

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
