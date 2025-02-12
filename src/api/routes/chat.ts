import { AgentConfig } from "@/agent/config/agent-config.interface";
import StateManager from "@/agent/modules/state/state-manager";
import SupervisorAgent from "@/agent/sub-agents/supervisor/agent";
import { generateId } from "ai";
import express, { Router, Request, Response } from "express";

// Type definitions
interface Message {
  role: "system" | "user" | "assistant" | "function";
  content: string;
  name?: string;
  function_call?: {
    name: string;
    arguments: string;
  };
}

interface ChatCompletionRequest {
  model: string;
  messages: Message[];
  temperature?: number;
  top_p?: number;
  n?: number;
  stream?: boolean;
  max_tokens?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
  user?: string;
}

interface Choice {
  index: number;
  message: Message;
  finish_reason: "stop" | "length" | "function_call" | "content_filter";
}

interface ChatCompletion {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  choices: Choice[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

interface APIError {
  error: {
    message: string;
    type: string;
    code: string;
    param?: string;
  };
}

// Response generation parameters
interface GenerationParams {
  temperature: number;
  top_p: number;
  max_tokens?: number;
  presence_penalty: number;
  frequency_penalty: number;
}

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
    try {
      const {
        model,
        messages,
        temperature = 1,
        top_p = 1,
        n = 1,
        stream = false,
        max_tokens,
        presence_penalty = 0,
        frequency_penalty = 0,
        user,
      } = req.body;

      console.log(messages);

      // Validate required fields
      if (!model || !messages || !Array.isArray(messages)) {
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

      // Generate a response
      const response = await generateResponse(messages, {
        temperature,
        top_p,
        max_tokens,
        presence_penalty,
        frequency_penalty,
      });

      // Handle streaming response
      if (stream) {
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");

        for await (const chunk of streamResponse(messages, {
          model,
          temperature,
          top_p,
          max_tokens,
          presence_penalty,
          frequency_penalty,
        })) {
          res.write(`data: ${JSON.stringify(chunk)}\n\n`);
        }
        res.write("data: [DONE]\n\n");
        res.end();
        return;
      }

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
  messages: Message[],
  params: GenerationParams
): Promise<string> {
  const stateManager = new StateManager({
    messages,
  });

  const config: AgentConfig = {
    name: "api-supervisor",
    description: "api supervisor",
    defaultModel: "gpt-4o",
  };

  const agent = new SupervisorAgent(config, stateManager);

  const response = await agent.execute(messages[0].content);

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
  const response = await generateResponse(messages, params);
  const chunks = response.split(" ");

  for (const chunk of chunks) {
    yield {
      id: `chatcmpl-${generateId()}`,
      object: "chat.completion.chunk",
      created: Math.floor(Date.now() / 1000),
      model: params.model,
      choices: [
        {
          index: 0,
          delta: {
            content: chunk + " ",
          },
          finish_reason: null,
        },
      ],
    };
  }
}

export default router;
