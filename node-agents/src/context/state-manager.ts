import { CoreMessage } from "ai";
import {
  StateUpdate,
  InternalMessage,
  BaseState,
} from "@/types/state.interface";

export default class StateManager<T extends BaseState> {
  private state: T;

  constructor(initialState: T) {
    this.state = {
      ...initialState,
      messages: [],
      internalMessages: [],
      status: "idle",
    };
  }

  handleUpdate(update: StateUpdate) {
    switch (update.type) {
      case "UPDATE_STATUS":
        this.state = { ...this.state, status: update.payload };
        break;
      case "ADD_MESSAGE":
        this.state = {
          ...this.state,
          messages: [...this.state.messages, update.payload],
        };
        break;
      // Handle other update types
      case "ADD_INTERNAL_MESSAGE":
        this.state = {
          ...this.state,
          internalMessages: [
            ...this.state.internalMessages,
            update.payload as InternalMessage,
          ],
        };
        break;
    }
  }

  get(key: keyof T) {
    return this.state[key];
  }

  add(key: keyof T, value: any) {
    this.state = { ...this.state, [key]: value };
  }

  update(key: keyof T, value: any) {
    // first check if the key exists in the state
    if (key in this.state) {
      // if it exists, update it
      this.state = { ...this.state, [key]: value };
    } else {
      // throw an error if it doesn't exist
      throw new Error(`Key ${key.toString()} does not exist in the state`);
    }
  }

  getState(): T {
    return this.state;
  }

  addMessage(message: CoreMessage) {
    this.handleUpdate({ type: "ADD_MESSAGE", payload: message });
  }

  addInternalMessage(message: InternalMessage) {
    this.handleUpdate({ type: "ADD_INTERNAL_MESSAGE", payload: message });
  }

  getInternalMessages() {
    return this.state.internalMessages;
  }
}
