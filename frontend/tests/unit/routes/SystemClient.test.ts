import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SystemClient } from '../../../src/routes/SystemClient';
import type { ApiConfig } from '../../../src/types';

describe('SystemClient', () => {
  let client: SystemClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: 'http://localhost:8000',
    apiKey: 'test-api-key',
  };

  beforeEach(() => {
    client = new SystemClient(config);
    mockFetch.mockClear();
    (globalThis as any).fetch = mockFetch;
  });

  it('should call getSystemInfo', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response);
    const result = await client.getSystemInfo();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/info',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ status: 'ok' });
  });

  it('should call getFrameworkVersion', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ version: '1.0.0' }),
    } as Response);
    const result = await client.getFrameworkVersion();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/version',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ version: '1.0.0' });
  });

  it('should call getSystemCapabilities', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ capabilities: [] }),
    } as Response);
    const result = await client.getSystemCapabilities();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/capabilities',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ capabilities: [] });
  });

  it('should call getEnvironmentVariables', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ variables: [] }),
    } as Response);
    const result = await client.getEnvironmentVariables();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/environment',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ variables: [] });
  });

  it('should call updateEnvironmentVariables', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response);
    const result = await client.updateEnvironmentVariables({ TEST: 'test' });
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/environment',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ variables: { TEST: 'test' } }),
      })
    );
    expect(result).toEqual({ status: 'ok' });
  });

  it('should call listDependencies', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ dependencies: [] }),
    } as Response);
    const result = await client.listDependencies();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/dependencies',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ dependencies: [] });
  });

  it('should call checkDependencyHealth', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response);
    const result = await client.checkDependencyHealth();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/dependencies/check',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result).toEqual({ status: 'ok' });
  });

  it('should call getSystemMetrics', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ metrics: {} }),
    } as Response);
    const result = await client.getSystemMetrics();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/monitoring/metrics',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ metrics: {} });
  });

  it('should call listActiveProcesses', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ processes: [] }),
    } as Response);
    const result = await client.listActiveProcesses();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/monitoring/active',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ processes: [] });
  });

  it('should call comprehensiveHealthCheck', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response);
    const result = await client.comprehensiveHealthCheck();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/system/health',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ status: 'ok' });
  });
});
