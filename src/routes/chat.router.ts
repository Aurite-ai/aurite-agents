import { AgentConfig } from "@/types/agent.interface";
import StateManager from "@/context/state-manager";
import SupervisorAgent from "@/agents/coordination/supervisor.agent";
import { generateId } from "ai";
import express, { Router, Request, Response } from "express";
import dotenv from "dotenv";
import {
  ChatCompletionRequest,
  ChatCompletion,
  APIError,
  GenerationParams,
  Message,
} from "@/types/router.interface";
import { BaseState } from "@/types/state.interface";

// Load environment variables from .env file
dotenv.config();

const router: Router = Router();

// Mock database for conversation history
const conversations = new Map<string, Message[]>();

router.post("/test", async (req, res) => {
  res.json({ message: "Test endpoint is working!" });
});

// Chat completions endpoint
router.post(
  "/completions",
  async (
    req: Request<{}, {}, ChatCompletionRequest>,
    res: Response<ChatCompletion | APIError>
  ): Promise<any> => {
    console.log("Received request:", req.body);

    try {
      const {
        model,
        messages,
        temperature = 1,
        top_p = 1,
        stream = false,
        max_tokens,
        presence_penalty = 0,
        frequency_penalty = 0,
      } = req.body;

      // Validate required fields
      if (!model || !messages || messages.length === 0) {
        return res.status(400).json({
          error: {
            message: "Missing required fields: 'model' and 'messages' array",
            type: "invalid_request_error",
            code: "invalid_request",
          },
        });
      }

      // Validate message format
      for (const message of messages) {
        if (!message.role || !message.content) {
          return res.status(400).json({
            error: {
              message: "Each message must have 'role' and 'content' fields",
              type: "invalid_request_error",
              code: "invalid_request",
            },
          });
        }
      }

      console.log("Generating response...");

      // Handle streaming response
      if (stream) {
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");

        try {
          for await (const chunk of streamResponse(messages, {
            model,
            temperature,
            top_p,
            max_tokens,
            presence_penalty,
            frequency_penalty,
          })) {
            // Make sure to send each chunk in the correct SSE format
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          }

          // Send the [DONE] event
          res.write("data: [DONE]\n\n");
        } catch (error) {
          // Handle any errors during streaming
          console.error("Streaming error:", error);
          res.write(
            `data: ${JSON.stringify({
              error: {
                message: "Error during streaming",
                type: "server_error",
                code: "stream_error",
              },
            })}\n\n`
          );
        } finally {
          res.end();
        }
        return;
      }

      // Generate a response
      const response = await generateResponse(messages[0].content, {
        temperature,
        top_p,
        max_tokens,
        presence_penalty,
        frequency_penalty,
      });

      // Create completion response
      const completion: ChatCompletion = {
        id: `chatcmpl-${generateId()}`,
        object: "chat.completion",
        created: Math.floor(Date.now() / 1000),
        model,
        choices: [
          {
            index: 0,
            message: {
              role: "assistant",
              content: response,
            },
            finish_reason: "stop",
          },
        ],
        usage: {
          prompt_tokens: calculateTokens(messages),
          completion_tokens: calculateTokens(response),
          total_tokens: calculateTokens(messages) + calculateTokens(response),
        },
      };

      res.json(completion);
    } catch (error) {
      console.error("Error generating response:", error);
      res.status(500).json({
        error: {
          message: "Internal server error",
          type: "server_error",
          code: "internal_error",
        },
      });
    }
  }
);

function calculateTokens(text: string | Message[]): number {
  // Implement your token counting logic here
  // This is a simple approximation
  if (Array.isArray(text)) {
    return text.reduce(
      (acc, msg) => acc + Math.ceil(msg.content.length / 4),
      0
    );
  }
  return Math.ceil(text.length / 4);
}

async function generateResponse(
  prompt: string,
  params: GenerationParams
): Promise<string> {
  interface ChatState extends BaseState {
    status: string;
  }

  const stateManager = new StateManager({
    status: "idle",
    messages: [],
    internalMessages: [],
  });

  const config: AgentConfig = {
    name: "api-supervisor",
    description: "api supervisor",
    defaultModel: "gpt-4o",
  };

  const agent = new SupervisorAgent(config, stateManager);

  const response = await agent.execute(prompt);

  console.log(response);

  return response;
}

interface StreamChunk {
  id: string;
  object: "chat.completion.chunk";
  created: number;
  model: string;
  choices: {
    index: number;
    delta: Partial<Message>;
    finish_reason:
      | "stop"
      | "length"
      | "function_call"
      | "content_filter"
      | null;
  }[];
}

async function* streamResponse(
  messages: Message[],
  params: GenerationParams & { model: string }
): AsyncGenerator<StreamChunk> {
  try {
    const response = await generateResponse(
      `Respond to the last message of this thread ${JSON.stringify(messages)}`,
      params
    );

    // First chunk should include role
    yield {
      id: `chatcmpl-${generateId()}`,
      object: "chat.completion.chunk",
      created: Math.floor(Date.now() / 1000),
      model: params.model,
      choices: [
        {
          index: 0,
          delta: {
            role: "assistant",
          },
          finish_reason: null,
        },
      ],
    };

    // Split response into smaller chunks (you might want to adjust this logic)
    const chunks = response.match(/.{1,4}/g) || [];

    for (let i = 0; i < chunks.length; i++) {
      const isLast = i === chunks.length - 1;

      yield {
        id: `chatcmpl-${generateId()}`,
        object: "chat.completion.chunk",
        created: Math.floor(Date.now() / 1000),
        model: params.model,
        choices: [
          {
            index: 0,
            delta: {
              content: chunks[i],
            },
            finish_reason: isLast ? "stop" : null,
          },
        ],
      };
    }
  } catch (error) {
    console.error("Error in stream generation:", error);
    throw error;
  }
}

export default router;
