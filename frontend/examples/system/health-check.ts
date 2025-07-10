/**
 * Example for using the SystemClient
 */

import { createAuriteClientFromEnv } from '../../src/client/AuriteApiClient';

async function main() {
  console.log('=== System Client Example ===');
  const client = await createAuriteClientFromEnv();

  try {
    const version = await client.system.getFrameworkVersion();
    console.log('Framework Version:', version);

    const health = await client.system.comprehensiveHealthCheck();
    console.log('System Health:', health.status);

    const processes = await client.system.listActiveProcesses();
    console.log('Active Processes:', processes);
  } catch (error) {
    console.error('Error using system client:', error);
  }
}

main().catch(console.error);
