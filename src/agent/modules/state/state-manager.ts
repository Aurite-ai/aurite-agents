interface StateUpdate {
  type: string;
  payload: any;
}

export default class StateManager<T> {
  private state: T;

  constructor(initialState: T) {
    this.state = initialState;
  }

  handleUpdate(update: StateUpdate) {
    switch (update.type) {
      case "UPDATE_STATUS":
        this.state = { ...this.state, status: update.payload };
        break;
      // Handle other update types
    }
  }

  getState(): T {
    return this.state;
  }

  getStateValue<K extends keyof T>(key: K): T[K] {
    return this.state[key];
  }
}
