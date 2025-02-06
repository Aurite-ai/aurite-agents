import ResearcherAgent from "./researcher/agent";

export default function pickAgent(name: string) {
  if (name === "researcher") {
    return ResearcherAgent;
  } else {
    throw new Error(`Agent ${name} not found`);
  }
}
