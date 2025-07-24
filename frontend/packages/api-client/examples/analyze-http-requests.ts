#!/usr/bin/env tsx
/**
 * Enhanced HTTP Request Analysis Script
 * 
 * This script intercepts all HTTP requests made by the examples,
 * captures detailed request/response information, and generates
 * a comprehensive analysis report.
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { writeFileSync } from 'fs';
import { join } from 'path';

const execAsync = promisify(exec);

interface HttpRequest {
  id: string;
  timestamp: string;
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: any;
}

interface HttpResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  body?: any;
  error?: string;
  duration: number;
}

interface HttpTransaction {
  request: HttpRequest;
  response?: HttpResponse;
  error?: string;
}

interface ExampleResult {
  name: string;
  path: string;
  success: boolean;
  output: string;
  error?: string;
  duration: number;
  httpTransactions: HttpTransaction[];
}

// Create a wrapper script that intercepts fetch
const createWrapperScript = (examplePath: string) => `
import { config } from 'dotenv';
config();

// Store all HTTP transactions
const httpTransactions = [];
let requestId = 0;

// Save the original fetch
const originalFetch = global.fetch;

// Override global fetch
global.fetch = async function(input, init) {
  const id = String(++requestId);
  const timestamp = new Date().toISOString();
  
  // Extract request details
  const url = typeof input === 'string' ? input : input.url;
  const method = init?.method || 'GET';
  const headers = {};
  
  // Extract headers
  if (init?.headers) {
    if (init.headers instanceof Headers) {
      init.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(init.headers)) {
      init.headers.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, init.headers);
    }
  }
  
  // Extract body
  let body;
  if (init?.body) {
    if (typeof init.body === 'string') {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    } else {
      body = init.body;
    }
  }
  
  const request = {
    id,
    timestamp,
    method,
    url,
    headers,
    body
  };
  
  console.log('\\n🔵 HTTP Request #' + id);
  console.log('   Method:', method);
  console.log('   URL:', url);
  console.log('   Headers:', JSON.stringify(headers, null, 2));
  if (body) {
    console.log('   Body:', JSON.stringify(body, null, 2));
  }
  
  const startTime = Date.now();
  
  try {
    // Make the actual request
    const response = await originalFetch(input, init);
    const duration = Date.now() - startTime;
    
    // Clone response to read body
    const responseClone = response.clone();
    
    // Extract response headers
    const responseHeaders = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });
    
    // Try to read response body
    let responseBody;
    try {
      const text = await responseClone.text();
      try {
        responseBody = JSON.parse(text);
      } catch {
        responseBody = text;
      }
    } catch (e) {
      responseBody = '[Unable to read response body]';
    }
    
    const responseData = {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
      body: responseBody,
      duration
    };
    
    console.log('\\n🟢 HTTP Response #' + id);
    console.log('   Status:', response.status, response.statusText);
    console.log('   Duration:', duration + 'ms');
    console.log('   Headers:', JSON.stringify(responseHeaders, null, 2));
    if (responseBody) {
      console.log('   Body:', JSON.stringify(responseBody, null, 2).substring(0, 500) + '...');
    }
    
    httpTransactions.push({
      request,
      response: responseData
    });
    
    return response;
  } catch (error) {
    const duration = Date.now() - startTime;
    
    console.log('\\n🔴 HTTP Error #' + id);
    console.log('   Duration:', duration + 'ms');
    console.log('   Error:', error.message);
    
    httpTransactions.push({
      request,
      error: error.message
    });
    
    throw error;
  }
};

// At the end, output the transactions
process.on('beforeExit', () => {
  console.log('\\n📊 HTTP_TRANSACTIONS_START');
  console.log(JSON.stringify(httpTransactions));
  console.log('HTTP_TRANSACTIONS_END');
});

// Import and run the actual example
import('./${examplePath.split('/').pop()}').catch(error => {
  console.error('Example failed:', error);
  process.exit(1);
});
`;

async function runExampleWithInterception(example: { name: string; path: string }): Promise<ExampleResult> {
  console.log(`\n🚀 Running: ${example.name}`);
  console.log(`   Path: ${example.path}`);
  
  const startTime = Date.now();
  
  // Create a temporary wrapper file in the same directory as the example
  const wrapperPath = example.path.replace('.ts', '-wrapper.ts');
  const wrapperContent = createWrapperScript(example.path);
  writeFileSync(wrapperPath, wrapperContent);
  
  try {
    const { stdout, stderr } = await execAsync(`npx tsx ${wrapperPath}`, {
      cwd: process.cwd(),
      env: { ...process.env, NODE_ENV: 'development' },
      timeout: 30000,
    });
    
    const duration = Date.now() - startTime;
    console.log(`   ✅ Success (${duration}ms)`);
    
    // Extract HTTP transactions from output
    const httpTransactions = extractHttpTransactions(stdout);
    
    return {
      name: example.name,
      path: example.path,
      success: true,
      output: cleanOutput(stdout) + (stderr ? `\n\nSTDERR:\n${stderr}` : ''),
      duration,
      httpTransactions,
    };
  } catch (error: any) {
    const duration = Date.now() - startTime;
    console.log(`   ❌ Failed (${duration}ms)`);
    
    // Extract HTTP transactions even from failed output
    const httpTransactions = extractHttpTransactions(error.stdout || '');
    
    return {
      name: example.name,
      path: example.path,
      success: false,
      output: cleanOutput(error.stdout || ''),
      error: error.message + (error.stderr ? `\n\nSTDERR:\n${error.stderr}` : ''),
      duration,
      httpTransactions,
    };
  } finally {
    // Clean up wrapper file
    try {
      const fs = await import('fs');
      fs.unlinkSync(wrapperPath);
    } catch {}
  }
}

function extractHttpTransactions(output: string): HttpTransaction[] {
  try {
    const match = output.match(/HTTP_TRANSACTIONS_START\n(.*?)\nHTTP_TRANSACTIONS_END/s);
    if (match) {
      return JSON.parse(match[1]);
    }
  } catch (e) {
    console.error('Failed to extract HTTP transactions:', e);
  }
  return [];
}

function cleanOutput(output: string): string {
  // Remove the HTTP transactions JSON from output
  return output.replace(/HTTP_TRANSACTIONS_START\n.*?\nHTTP_TRANSACTIONS_END/s, '').trim();
}

const examples = [
  // Environment
  { name: 'Environment Configuration Demo', path: 'examples/environment-demo.ts' },
  
  // Configuration
  { name: 'Configuration Listing', path: 'examples/config/config-listing.ts' },
  { name: 'Reload Configurations', path: 'examples/config/reload-configs.ts' },
  
  // Execution
  { name: 'Basic Agent Execution', path: 'examples/execution/agent-basic.ts' },
  { name: 'Agent Streaming', path: 'examples/execution/agent-streaming.ts' },
  { name: 'Debug Planning Agent', path: 'examples/execution/debug-planning-agent.ts' },
  { name: 'Simple Workflow', path: 'examples/execution/workflow-simple.ts' },
  
  // MCP Host
  { name: 'Server Management', path: 'examples/mcp-host/server-management.ts' },
  { name: 'Tool Execution', path: 'examples/mcp-host/tool-execution.ts' },
  
  // System
  { name: 'Health Check', path: 'examples/system/health-check.ts' },
];

async function main() {
  console.log('🎯 Aurite API Client - HTTP Request Analysis');
  console.log('=' .repeat(60));
  console.log(`📅 Date: ${new Date().toISOString()}`);
  console.log(`📁 Working Directory: ${process.cwd()}`);
  console.log(`🔧 Node Version: ${process.version}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 API URL: ${process.env.AURITE_API_URL || 'http://localhost:8000'}`);
  console.log(`🔑 API Key: ${process.env.API_KEY ? '[SET]' : '[NOT SET]'}`);
  
  const results: ExampleResult[] = [];
  const startTime = Date.now();
  
  // Run all examples with HTTP interception
  for (const example of examples) {
    const result = await runExampleWithInterception(example);
    results.push(result);
  }
  
  const totalDuration = Date.now() - startTime;
  
  // Analyze HTTP transactions
  const allTransactions: HttpTransaction[] = [];
  results.forEach(r => allTransactions.push(...r.httpTransactions));
  
  const totalRequests = allTransactions.length;
  const successfulRequests = allTransactions.filter(t => t.response && t.response.status < 400).length;
  const failedRequests = allTransactions.filter(t => t.error || (t.response && t.response.status >= 400)).length;
  
  // Group by endpoint
  const endpointStats = new Map<string, { count: number; successes: number; failures: number }>();
  allTransactions.forEach(t => {
    const url = new URL(t.request.url);
    const endpoint = `${t.request.method} ${url.pathname}`;
    const stats = endpointStats.get(endpoint) || { count: 0, successes: 0, failures: 0 };
    stats.count++;
    if (t.response && t.response.status < 400) {
      stats.successes++;
    } else {
      stats.failures++;
    }
    endpointStats.set(endpoint, stats);
  });
  
  // Generate markdown report
  let markdown = `# Aurite API Client - HTTP Request Analysis Report

## Summary

- **Date**: ${new Date().toISOString()}
- **Total Examples**: ${results.length}
- **Successful Examples**: ${results.filter(r => r.success).length}
- **Failed Examples**: ${results.filter(r => !r.success).length}
- **Total Duration**: ${totalDuration}ms

## HTTP Request Statistics

- **Total Requests**: ${totalRequests}
- **Successful Requests**: ${successfulRequests}
- **Failed Requests**: ${failedRequests}

## Endpoint Usage

| Endpoint | Total | Success | Failed |
|----------|-------|---------|--------|
${Array.from(endpointStats.entries())
  .sort((a, b) => b[1].count - a[1].count)
  .map(([endpoint, stats]) => `| ${endpoint} | ${stats.count} | ${stats.successes} | ${stats.failures} |`)
  .join('\n')}

## Environment

- **Node Version**: ${process.version}
- **Working Directory**: ${process.cwd()}
- **API URL**: ${process.env.AURITE_API_URL || 'http://localhost:8000'}
- **API Key**: ${process.env.API_KEY ? '[SET]' : '[NOT SET]'}

## Example Results

| Example | Status | Duration | HTTP Requests |
|---------|--------|----------|---------------|
${results.map(r => `| ${r.name} | ${r.success ? '✅ Success' : '❌ Failed'} | ${r.duration}ms | ${r.httpTransactions.length} |`).join('\n')}

## Detailed HTTP Transactions

`;

  // Add detailed HTTP transaction logs
  for (const result of results) {
    if (result.httpTransactions.length === 0) continue;
    
    markdown += `\n### ${result.name}\n\n`;
    
    for (const transaction of result.httpTransactions) {
      markdown += `#### Request #${transaction.request.id}\n\n`;
      markdown += `- **Method**: ${transaction.request.method}\n`;
      markdown += `- **URL**: ${transaction.request.url}\n`;
      markdown += `- **Timestamp**: ${transaction.request.timestamp}\n`;
      markdown += `- **Headers**:\n\`\`\`json\n${JSON.stringify(transaction.request.headers, null, 2)}\n\`\`\`\n`;
      
      if (transaction.request.body) {
        markdown += `- **Body**:\n\`\`\`json\n${JSON.stringify(transaction.request.body, null, 2)}\n\`\`\`\n`;
      }
      
      if (transaction.response) {
        markdown += `\n**Response**:\n`;
        markdown += `- **Status**: ${transaction.response.status} ${transaction.response.statusText}\n`;
        markdown += `- **Duration**: ${transaction.response.duration}ms\n`;
        markdown += `- **Headers**:\n\`\`\`json\n${JSON.stringify(transaction.response.headers, null, 2)}\n\`\`\`\n`;
        
        if (transaction.response.body) {
          const bodyStr = JSON.stringify(transaction.response.body, null, 2);
          const truncated = bodyStr.length > 1000 ? bodyStr.substring(0, 1000) + '\n... [truncated]' : bodyStr;
          markdown += `- **Body**:\n\`\`\`json\n${truncated}\n\`\`\`\n`;
        }
      } else if (transaction.error) {
        markdown += `\n**Error**: ${transaction.error}\n`;
      }
      
      markdown += '\n---\n';
    }
  }
  
  // Add example outputs
  markdown += `\n## Example Outputs\n\n`;
  
  for (const result of results) {
    markdown += `\n### ${result.name}\n\n`;
    markdown += `- **Path**: \`${result.path}\`\n`;
    markdown += `- **Status**: ${result.success ? '✅ Success' : '❌ Failed'}\n`;
    markdown += `- **Duration**: ${result.duration}ms\n`;
    markdown += `- **HTTP Requests**: ${result.httpTransactions.length}\n\n`;
    
    if (result.output || result.error) {
      markdown += '#### Output\n\n```\n';
      if (result.output) {
        markdown += result.output;
      }
      if (result.error) {
        markdown += '\n\n❌ ERROR:\n' + result.error;
      }
      markdown += '\n```\n';
    }
  }
  
  // Write report to file
  const reportPath = join(process.cwd(), 'http-request-analysis-report.md');
  writeFileSync(reportPath, markdown);
  
  console.log(`\n\n📄 Report written to: ${reportPath}`);
  console.log('\n📊 Summary:');
  console.log(`   Total Examples: ${results.length}`);
  console.log(`   ✅ Success: ${results.filter(r => r.success).length}`);
  console.log(`   ❌ Failed: ${results.filter(r => !r.success).length}`);
  console.log(`   🌐 Total HTTP Requests: ${totalRequests}`);
  console.log(`   ⏱️  Total time: ${totalDuration}ms`);
}

// Run the script
main().catch(console.error);
