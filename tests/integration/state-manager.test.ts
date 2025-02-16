import { BaseState } from '@/types/state.interface';
import StateManager from '../../src/state/state-manager';

describe('StateManager', () => {
  let initialState: BaseState;
  let stateManager: StateManager<BaseState>;

  beforeEach(() => {
    initialState = {
      status: 'idle',
      messages: [],
      internalMessages: [],
    };
    stateManager = new StateManager<BaseState>(initialState);
  });

  test('should initialize with given state', () => {
    expect(stateManager.getState()).toEqual({ status: 'idle', count: 0 });
  });

  test('should update status on handleUpdate', () => {
    stateManager.handleUpdate({ type: 'UPDATE_STATUS', payload: 'running' });
    expect(stateManager.getState().status).toBe('running');
  });

  test('should not modify other state properties', () => {
    stateManager.handleUpdate({ type: 'UPDATE_STATUS', payload: 'running' });
    expect(stateManager.getState().status).toBe('running'); // Ensure `count` is unchanged
  });

  test('should return correct value using getStateValue', () => {
    expect(stateManager.get('status')).toBe('idle');
  });

  test('should handle multiple updates correctly', () => {
    stateManager.handleUpdate({ type: 'UPDATE_STATUS', payload: 'running' });
    stateManager.handleUpdate({ type: 'UPDATE_STATUS', payload: 'stopped' });
    expect(stateManager.getState().status).toBe('stopped');
  });

  test('should not update state for unknown update type', () => {
    stateManager.handleUpdate({ type: 'UNKNOWN_TYPE', payload: 'something' });
    expect(stateManager.getState()).toEqual(initialState);
  });
});
