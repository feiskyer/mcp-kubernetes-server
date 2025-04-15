# mcp-kubernetes-server

MCP server to manage Kubernetes clusters via kubectl.

## How to install

Ensure kubectl is installed and added to your PATH and then config your MCP servers in [Claude Desktop](https://claude.ai/download), [Cursor](https://www.cursor.com/), [ChatGPT Copilot](https://marketplace.visualstudio.com/items?itemName=feiskyer.chatgpt-copilot), [Github Copilot](https://github.com/features/copilot) and other supported AI clients:

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
