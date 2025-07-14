/**
 * Reload Configurations Example
 */

import { createExampleClient, runExample, handleExampleError } from '../shared/client-setup';

async function reloadConfigs() {
  const client = await createExampleClient();

  console.log('\n📋 Reloading configurations...');

  try {
    await client.config.reloadConfigs();
    console.log('✅ Configurations reloaded successfully.');
  } catch (error) {
    handleExampleError(error, 'Reload Configs');
  }
}

async function main() {
  await runExample('Reload Configurations', reloadConfigs);
}

main().catch(console.error);
