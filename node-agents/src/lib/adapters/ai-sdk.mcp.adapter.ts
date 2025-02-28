import { jsonSchema, Tool, tool } from "ai";
import { z } from "zod";
import type { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";

interface OpenAIAdapterOptions {
  strict?: boolean;
  truncateDescriptionLength?: number;
}

export class AISDKToolAdapter {
  private client: Pick<Client, "callTool" | "listTools">;
  private options: OpenAIAdapterOptions;
  private tools: Record<string, ReturnType<typeof tool>> = {};

  constructor(
    client: Pick<Client, "callTool" | "listTools">,
    options: OpenAIAdapterOptions = {
      truncateDescriptionLength: 1024,
    }
  ) {
    this.client = client;
    this.options = options;
  }

  //   async executeTool(toolName: string, args: any) {
  //     const selectedTool = this.tools[toolName];
  //     if (!selectedTool) {
  //       throw new Error(`Tool ${toolName} not found`);
  //     }
  //     return await selectedTool.execute(args);
  //   }

  /**
   *
   * @returns A list of tools that can be used with the Vercel AI SDK
   */

  async listTools(): Promise<
    Record<
      string,
      Tool & {
        execute: (args: any) => Promise<any>;
      }
    >
  > {
    const toolResult = await this.client.listTools();
    toolResult.tools.forEach((toolDef) => {
      const cleanedName = toolDef.name.replace(/[^a-zA-Z0-9]/g, "_");
      // cut off the first chars to avoid names longer than 64 chars
      const slicedName = cleanedName.split("").slice(0, 64).join("");

      this.tools[slicedName] = {
        ...tool({
          description: toolDef.description?.slice(
            0,
            this.options.truncateDescriptionLength
          ),
          parameters: jsonSchema(toolDef.inputSchema),
        }),
        //@ts-ignore
        execute: async (args: any) => {
          try {
            const result = await this.client.callTool(
              {
                name: toolDef.name,
                arguments: args,
              },
              CallToolResultSchema
            );
            return result;
          } catch (error) {
            console.error("Error calling tool:", error);
            throw new Error(`Error calling tool ${toolDef.name}`);
          }
        },
      };
    });

    console.log("Tools:", this.tools);

    return this.tools;
  }
}
