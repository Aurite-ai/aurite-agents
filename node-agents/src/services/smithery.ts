import { AISDKToolAdapter } from "@/lib/adapters/ai-sdk.mcp.adapter";
import { stripeServer } from "@/mcp/servers";
import { openai } from "@ai-sdk/openai";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory";
import { MultiClient } from "@smithery/sdk";
import { generateText } from "ai";
import { WebSocketClientTransport } from "@modelcontextprotocol/sdk/client/websocket.js";
import { createSmitheryUrl } from "@smithery/sdk";

import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

import { spawn } from "child_process";

// const npxProcess = spawn("npx", [], {
//   stdio: ["pipe", "pipe", "pipe"],
//   shell: process.platform === "win32", // Use shell on Windows
// });

// const transport = new StdioClientTransport({
//   command: "npx",
//   args: ["-y", "@mzxrai/mcp-webresearch"],
// });

const metaMcp = new StdioClientTransport({
  command: "npx",
  args: ["-y", "@metamcp/mcp-server-metamcp"],
  // env: {
  //   METAMCP_API_KEY: process.env.METAMCP_API_KEY,
  // },
});

const taskmanager = new StdioClientTransport({
  command: "npx",
  args: ["-y", "@kazuph/mcp-taskmanager"],
});

// const url = createSmitheryUrl(
//   "https://server.smithery.ai/@smithery-ai/brave-search/ws",
//   {
//     braveApiKey: "The API key for the BRAVE Search server.",
//   }
// );
// const transport = new WebSocketClientTransport(url);

const dotenv = require("dotenv");
dotenv.config({ path: ".env" });

export const runClient = async () => {
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  stripeServer.connect(serverTransport);

  const client = new MultiClient({
    name: "Smithery SDK Test Client",
    version: "1.0.0",
  });

  await client.connectAll({
    // stripe: clientTransport,
    // brave: transport,
    // metamcp: metaMcp,
    taskmanager: taskmanager,
    // webResearch: transport,
  });

  const openaiAdapter = new AISDKToolAdapter(client);

  const { text, toolResults } = await generateText({
    model: openai("gpt-4o"),
    prompt:
      // "Add add a new product to stripe with the name 'Bing treats', price of $10, and description 'This is a test product'.",
      "Help me create some tasks to clean my apartment. It's a two bedroom place.",
    tools: await openaiAdapter.listTools(),
    maxSteps: 2,
  });

  console.log("OpenAI Response:", text);
  console.log("OpenAI Tool Results:", toolResults);
};

runClient();
