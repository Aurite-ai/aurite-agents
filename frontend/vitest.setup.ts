// Vitest setup file
// This file is run before each test file

import { vi } from 'vitest';

// Make fetch available globally for tests
(globalThis as any).fetch = vi.fn();
