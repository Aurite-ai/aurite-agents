// Need to define standard agent - agent call interface

import { z } from "zod";

export const defaultToolSchema = z.object({
  waitForCompletion: z.boolean().default(true),
  maxTokens: z.number().default(1000),
});
