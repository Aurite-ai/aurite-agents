import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { serverTransport } from "./server";

const transport = new StdioClientTransport({
  command: "node",
  args: ["dist/server.js"],
});

const client = new Client(
  {
    name: "example-client",
    version: "1.0.0",
  },
  {
    capabilities: {
      prompts: {},
      resources: {},
      tools: {},
    },
  }
);

const fn = async () => {
  await client.connect(transport);

  // List prompts
  // const prompts = await client.listPrompts();

  // // Get a prompt
  // // const prompt = await client.getPrompt("example-prompt", {
  // //   arg1: "value",
  // // });

  // // List resources
  const resources = await client.listResources();

  console.log(resources);

  // // Read a resource
  // const resource = await client.readResource("echo://{message}");

  // // Call a tool
  const result = await client.callTool({
    name: "echo",
    arguments: {
      message: "Hello, world!",
    },
  });

  console.log(result);
};

fn();
