import type { Client } from "@modelcontextprotocol/sdk/client/index.js";
import type { RequestOptions } from "@modelcontextprotocol/sdk/shared/protocol.js";
import { CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";
import type { OpenAI } from "openai";
import type {
  ChatCompletionTool,
  ChatCompletionToolMessageParam,
} from "openai/resources/index.js";

interface OpenAIAdapterOptions {
  strict?: boolean;
  truncateDescriptionLength?: number;
}

/**
 * Adapt an MCP client so it works seamlessly with OpenAI chat completions
 */
export class OpenAIChatAdapter {
  private client: Pick<Client, "callTool" | "listTools">;
  private options: OpenAIAdapterOptions;

  constructor(
    client: Pick<Client, "callTool" | "listTools">,
    options: OpenAIAdapterOptions = {
      // Restriction enforced by OpenAI
      truncateDescriptionLength: 1024,
    }
  ) {
    this.client = client;
    this.options = options;
  }

  async listTools(): Promise<ChatCompletionTool[]> {
    const toolResult = await this.client.listTools();
    return toolResult.tools.map((tool) => ({
      type: "function",
      function: {
        name: tool.name,
        description: tool.description?.slice(
          0,
          this.options?.truncateDescriptionLength
        ),
        parameters: tool.inputSchema,
        strict: this.options?.strict ?? false,
      },
    }));
  }

  // TODO: Support streaming
  async callTool(
    response: OpenAI.Chat.Completions.ChatCompletion,
    options?: RequestOptions
  ): Promise<ChatCompletionToolMessageParam[]> {
    if (response.choices.length !== 1) {
      // TODO: Support `n`
      throw new Error("Multiple choices not supported");
    }

    const choice = response.choices[0];
    if (!choice?.message?.tool_calls) {
      return [];
    }

    const toolCalls = choice.message.tool_calls;
    const results = await Promise.all(
      toolCalls.map(async (toolCall) => {
        return await this.client.callTool(
          {
            name: toolCall.function.name,
            arguments: JSON.parse(toolCall.function.arguments),
          },
          CallToolResultSchema,
          options
        );
      })
    );

    return results.map((result, index) => ({
      role: "tool",
      content: result.content as
        | string
        | {
            type: "text";
            text: string;
          }[],
      tool_call_id: toolCalls[index].id,
    }));
  }
}
