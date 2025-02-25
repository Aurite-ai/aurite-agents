import { AISDKToolAdapter } from "@/lib/adapters/ai-sdk.mcp.adapter";
import { stripeServer } from "@/mcp/servers";
import { openai } from "@ai-sdk/openai";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory";
import { MultiClient } from "@smithery/sdk";
import { generateText } from "ai";

import { getMcpTransorts } from "./directory/mcp-server.directory";

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

  const transportMap = getMcpTransorts();

  await client.connectAll(transportMap);

  const openaiAdapter = new AISDKToolAdapter(client);

  const { text, toolResults } = await generateText({
    model: openai("gpt-4o"),
    prompt:
      // "Add add a new product to stripe with the name 'Bing treats', price of $10, and description 'This is a test product'.",
      "Help me create some tasks to clean my apartment. It's a two bedroom place. Add some products to stripe that I can buy to help me clean.",
    tools: await openaiAdapter.listTools(),
    maxSteps: 2,
  });

  console.log("OpenAI Response:", text);
  console.log("OpenAI Tool Results:", toolResults);
};

runClient();
