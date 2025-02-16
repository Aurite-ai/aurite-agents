interface ToolOutput {
  toolName: string;
  output: any;
}

interface ToolDetails {
  name: string;
  description: string;
}

import { z } from 'zod';

const defaultToolSchema = z.object({
  waitForCompletion: z.boolean().default(true),
  maxTokens: z.number().default(1000),
});

export { ToolOutput, ToolDetails, defaultToolSchema };
