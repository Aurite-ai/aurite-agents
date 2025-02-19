import { tool } from "ai";
import { z } from "zod";

const userConfirmTool = tool({
  description: "A tool that pings the user for confirmation.",
  parameters: z.object({
    message: z.string(),
  }),
});

export { userConfirmTool };
