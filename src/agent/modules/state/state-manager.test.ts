import StateManager from "./state-manager";

describe("StateManager", () => {
  interface TestState {
    count: number;
  }

  let initialState: TestState;
  let stateManager: StateManager<TestState>;

  beforeEach(() => {
    initialState = {
      count: 0,
    };
    stateManager = new StateManager<TestState>(initialState);
  });

  test("should initialize with given state", () => {
    expect(stateManager.getState()).toEqual({ status: "idle", count: 0 });
  });

  test("should update status on handleUpdate", () => {
    stateManager.handleUpdate({ type: "UPDATE_STATUS", payload: "running" });
    expect(stateManager.getState().status).toBe("running");
  });

  test("should not modify other state properties", () => {
    stateManager.handleUpdate({ type: "UPDATE_STATUS", payload: "running" });
    expect(stateManager.getState().count).toBe(0); // Ensure `count` is unchanged
  });

  test("should return correct value using getStateValue", () => {
    expect(stateManager.get("count")).toBe(0);
  });

  test("should handle multiple updates correctly", () => {
    stateManager.handleUpdate({ type: "UPDATE_STATUS", payload: "running" });
    stateManager.handleUpdate({ type: "UPDATE_STATUS", payload: "stopped" });
    expect(stateManager.getState().status).toBe("stopped");
  });

  test("should not update state for unknown update type", () => {
    stateManager.handleUpdate({ type: "UNKNOWN_TYPE", payload: "something" });
    expect(stateManager.getState()).toEqual(initialState);
  });
});
