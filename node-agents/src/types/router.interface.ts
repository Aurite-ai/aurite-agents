// Type definitions
interface Message {
  role: 'system' | 'user' | 'assistant' | 'function';
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
  finish_reason: 'stop' | 'length' | 'function_call' | 'content_filter';
}

interface ChatCompletion {
  id: string;
  object: 'chat.completion';
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

export {
  Message,
  ChatCompletionRequest,
  ChatCompletion,
  APIError,
  GenerationParams,
};
