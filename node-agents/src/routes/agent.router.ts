import ExecutorAgent from "@/agents/execution/executor.agent";
import StateManager from "@/context/state-manager";
import { AgentConfig } from "@/types";
import { Request, Response, Router } from "express";

const router: Router = Router();

router.post("/execute", async (req: Request, res: Response): Promise<any> => {
  const { instructions } = req.body;

  if (!instructions) {
    return res.status(400).json({ error: "Instructions are required" });
  }

  try {
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

    const agent = new ExecutorAgent(config, stateManager);

    const output = await agent.execute(instructions);

    const internal = stateManager.getInternalMessages();

    res.json({ output, internal });
  } catch (error) {
    console.error("Error executing agent:", error);
    res.status(500).json({ error: "Internal server error" });
  }
});

export { router as agentRouter };
