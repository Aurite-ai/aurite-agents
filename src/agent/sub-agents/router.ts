import PlannerAgent from "./planner/agent";
import ResearcherAgent from "./researcher/agent";

export default function pickAgent(name: string) {
  if (name === "researcher") {
    return ResearcherAgent;
  } else if (name === "planner") {
    return PlannerAgent;
  } else {
    throw new Error(`Agent ${name} not found`);
  }
}
