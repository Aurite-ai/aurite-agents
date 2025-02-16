import { AgentConfig } from '@/types/agent.interface';
import SupervisorAgent from '../../src/agents/coordination/supervisor.agent';
import StateManager from '@/state/state-manager';

const fs = require('fs');

describe('Supervisor', () => {
  it('should be able to run', async () => {
    const config: AgentConfig = {
      name: 'test-supervisor',
      description: 'test supervisor',
      defaultModel: 'gpt-4o',
    };

    const state = new StateManager({
      status: 'idle',
      messages: [],
      internalMessages: [],
    });

    const supervisor = new SupervisorAgent(config, state);

    const text = await supervisor.execute(
      'Who won the 2025 superbowl and how? Output your answer as markdown.'
    );

    // write to file for debugging
    fs.writeFileSync('tests/agent-outputs/supervisor-test.md', text);

    fs.writeFileSync(
      'tests/agent-outputs/supervisor-state.json',
      JSON.stringify(state.getState(), null, 2)
    );

    expect(text).toBeDefined();
  }, 100000);
});
