import { OpenAIChatAdapter } from "@/lib/adapters/openai-tool-mcp";
import { stripeServer } from "@/mcp/servers";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory";
// import { OpenAIChatAdapter } from "@smithery/sdk";
// import { OpenAIChatAdapter } from "@smithery/sdk";
import { OpenAI } from "openai";

// Object.assign(global, { WebSocket: require("ws") });

const dotenv = require("dotenv");

console.log("Loading environment variables from .env file");

dotenv.config({ path: ".env" });

export const runClient = async () => {
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  stripeServer.connect(serverTransport);

  const client = new Client({
    name: "Smithery SDK Test Client",
    version: "1.0.0",
  });

  await client.connect(clientTransport);

  // Using OpenAI
  const openai = new OpenAI();
  const openaiAdapter = new OpenAIChatAdapter(client);
  const openaiResponse = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      {
        role: "user",
        content:
          "You have access to stripe tools. Using stripe, List all of the products, and return the product name, price, and description.",
      },
    ],
    tools: await openaiAdapter.listTools(),
  });

  const openaiToolMessages = await openaiAdapter.callTool(openaiResponse);

  console.log("OpenAI Response:", openaiResponse.choices[0].message.content);
  console.log("OpenAI Tool Messages:", ...openaiToolMessages);
};

runClient();
