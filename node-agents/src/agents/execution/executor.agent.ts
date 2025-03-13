export {};

import { AISDKToolAdapter } from "@/lib/adapters/ai-sdk.mcp.adapter.js";
import { getMcpTransorts } from "@/services/directory/mcp-server.directory.js";
import { Agent } from "@/types/index.js";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import type { MultiClient } from "@smithery/sdk";

export default class ExecutorAgent extends Agent {
  private client: MultiClient;
  protected config: any;
  protected addInternalMessage: (text: string, toolResults?: any) => void;

  async setupTools() {
    const { MultiClient } = await import("@smithery/sdk");
    this.client = new MultiClient({
      name: "Executor Agent Client",
      version: "0.2.0",
    });

    const transportMap = getMcpTransorts();

    await this.client.connectAll(transportMap);

    // const aiSdkAdapter = new AISDKToolAdapter(this.client);
  }

  async execute(instructions: string) {
    if (!this.client) {
      await this.setupTools();
    }

    const aiSdkAdapter = new AISDKToolAdapter(this.client);

    const tools = await aiSdkAdapter.listTools();

    const { text } = await generateText({
      prompt: `You are an executor agent. Your job is to call tools to perform actions defined by the supervisor agent's instructions.

      To accomplish this, first you should view your available tools and call the best one to accomplish the task.
      Next, evaluate the results of the tool and determine if you need to call another tool or if the task is complete.
      When you are finished, return the results of your actions as a summary of what you did and the results of your actions.

      Your Instructions are:
      ${instructions}.

      `,
      onStepFinish: ({ text, toolResults }) =>
        this.addInternalMessage(text, toolResults),
      model: openai(this.config.defaultModel),
      tools,
      temperature: 0.2,
      maxSteps: 5,
    });

    return text;
  }

  getTool(
    opts: any = {
      reThrowErrors: true,
    }
  ) {
    return tool({
      description: "A tool that runs the executor agent",
      parameters: z.object({
        prompt: z.string(),
      }),
      execute: async ({ prompt }) => {
        try {
          return this.execute(prompt);
        } catch (error) {
          console.error("Error executing Executor agent:", error);

          if (opts.reThrowErrors) {
            throw error;
          }

          return `Error executing tool: ${error}`;
        }
      },
    });
  }
}
