import { BaseClient } from '../client/BaseClient';

export class SystemClient extends BaseClient {
  async getStatus(): Promise<string> {
    return this.request('GET', '/health');
  }

  async getSystemInfo(): Promise<any> {
    return this.request('GET', '/system/info');
  }

  async getFrameworkVersion(): Promise<any> {
    return this.request('GET', '/system/version');
  }

  async getSystemCapabilities(): Promise<any> {
    return this.request('GET', '/system/capabilities');
  }

  async getEnvironmentVariables(): Promise<any> {
    return this.request('GET', '/system/environment');
  }

  async updateEnvironmentVariables(variables: any): Promise<any> {
    return this.request('PUT', '/system/environment', { variables });
  }

  async listDependencies(): Promise<any> {
    return this.request('GET', '/system/dependencies');
  }

  async checkDependencyHealth(): Promise<any> {
    return this.request('POST', '/system/dependencies/check');
  }

  async getSystemMetrics(): Promise<any> {
    return this.request('GET', '/system/monitoring/metrics');
  }

  async listActiveProcesses(): Promise<any> {
    return this.request('GET', '/system/monitoring/active');
  }

  async comprehensiveHealthCheck(): Promise<any> {
    return this.request('GET', '/system/health');
  }
}
