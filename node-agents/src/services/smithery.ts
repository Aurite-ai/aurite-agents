import { AISDKToolAdapter } from "@/lib/adapters/ai-sdk.mcp.adapter";
import { openai } from "@ai-sdk/openai";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory";
import { createSmitheryUrl, MultiClient } from "@smithery/sdk";
import { generateText, Tool } from "ai";

import { createMetaToolkit } from "@/mcp/servers/meta.server";
import { WebSocketClientTransport } from "@modelcontextprotocol/sdk/client/websocket";

const dotenv = require("dotenv");
dotenv.config({ path: ".env" });

export const runClient = async () => {
  console.log("Starting client");

  let tools: Record<string, Tool> = {};
  let conversationContext: string = "";

  // Initialize the client
  const client = new MultiClient({
    name: "Smithery SDK Test Client",
    version: "1.0.0",
  });

  // Create the transport pair
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  // Define the refreshTools function
  const refreshTools = async () => {
    const openaiAdapter = new AISDKToolAdapter(client);
    tools = await openaiAdapter.listTools();
    console.log("Tools refreshed:", Object.keys(tools));
  };

  // First create the meta server
  const metaServer = createMetaToolkit({
    addServer: async (name, transport) => {
      console.log(`Adding server ${name}`);
      console.log(transport);

      // connect the server to the client
      await client.connectAll({
        [name]: transport,
      });

      await refreshTools();
    },
  });

  console.log("Meta Server registered");

  // First connect the server transport
  metaServer.connect(serverTransport);
  console.log("Server transport connected");

  // Then connect the client transport
  await client.connectAll({
    meta: clientTransport,
  });
  console.log("Client transport connected");

  // Do initial tools refresh
  await refreshTools();

  // Set up the prompt
  const initialPrompt = `
    *You are an AI Agent that can call tools to perform actions.
    *You can use the 'meta' tool to search for your available MCP servers and call them to perform actions.
    *An MCP server is basically a library of tools related to a specific application.
    *Once you find a tool that you want to use, you can prepare it with the 'addServer' tool to expose it to your agent toolkit. Use the exact name of the server from inside the brackets [e.g. 'memory-server' or '@org/server-name'] (include @ if neccessary) to add it.
    *Then, use the new tools that were exposed to perform actions.
    
    Your Instructions are:
    Make a pull request on my github profile titled "Add a new feature".
  `;

  const maxSteps = 5;
  let allSteps = [];
  let finalText = "";

  // Custom implementation to run steps individually
  conversationContext = initialPrompt;

  for (let stepCount = 0; stepCount < maxSteps; stepCount++) {
    console.log(`\n--- Running Step ${stepCount + 1} ---`);

    // Refresh tools before each step
    await refreshTools();

    const newtools = tools;

    // Run a single step using the current tools
    const { text, toolCalls, toolResults, steps } = await generateText({
      model: openai("gpt-4o"),
      prompt: conversationContext,
      tools: newtools,
    });

    // Store the step
    allSteps.push(steps[0]);

    // Check if tool was called

    if (toolResults.length > 0) {
      // Update conversation context
      conversationContext += `\n\n--- Tool Calls & Results ---\n`;
      conversationContext += `\n${JSON.stringify(toolCalls)}\n`;
      conversationContext += `\n${JSON.stringify(toolResults)}\n`;
    } else {
      // Check if the conversation is complete
      // Update the conversation context
      conversationContext += text;

      finalText = text;
      // End the conversation
      break;
    }
  }

  console.log("\n=== Final Response ===");
  console.log(finalText);
  console.log("Total Steps Executed:", allSteps.length);

  // dump steps to file for debugging
  const fs = require("fs");
  fs.writeFileSync("steps.json", JSON.stringify(allSteps, null, 2));
};

runClient();
