# ACP Setup

ReVibe can be used in text editors and IDEs that support [Agent Client Protocol](https://agentclientprotocol.com/overview/clients). ReVibe includes the `revibe-acp` tool.
Once you have set up `revibe` with the API keys, you are ready to use `revibe-acp` in your editor. Below are the setup instructions for some editors that support ACP.

## Zed

For usage in Zed, we recommend using the [ReVibe Zed extension](https://zed.dev/extensions/revibe). Alternatively, you can set up a local install as follows:

1. Go to `~/.config/zed/settings.json` and, under the `agent_servers` JSON object, add the following key-value pair:

```json
{
   "agent_servers": {
      "ReVibe": {
         "type": "custom",
         "command": "revibe-acp",
         "args": [],
         "env": {}
      }
   }
}
```

2. In the `New Thread` pane on the right, select the `ReVibe` agent and start the conversation.

## JetBrains IDEs

1. Add the following snippet to your JetBrains IDE acp.json ([documentation](https://www.jetbrains.com/help/ai-assistant/acp.html)):

```json
{
  "agent_servers": {
    "ReVibe": {
      "command": "revibe-acp"
    }
  }
}
```

2. In the AI Chat agent selector, select the ReVibe agent and start the conversation.

## Neovim (using avante.nvim)

Add ReVibe in the acp_providers section of your configuration:

```lua
{
  acp_providers = {
    ["revibe"] = {
      command = "revibe-acp",
      env = {
         -- Add API keys as needed
      },
    }
  }
}
```
