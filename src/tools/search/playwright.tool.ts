import { tool } from 'ai';
import { z } from 'zod';
import { Browser, chromium, Page } from 'playwright';

// Types for the scraping result
export interface ScrapingResult {
  title: string;
  content: string;
  metadata: {
    url: string;
    timestamp: string;
    status: 'success' | 'partial' | 'error';
    message?: string;
  };
  links?: Array<{ text: string; href: string }>;
}

// Configuration for the browser
export const browserConfig = {
  headless: true,
  timeout: 30000,
};

// Helper function to initialize the browser
export async function initBrowser(): Promise<Browser> {
  return await chromium.launch(browserConfig);
}

// Helper function to extract content based on objective
export async function extractContent(
  page: Page,
  objective: string
): Promise<Partial<ScrapingResult>> {
  const title = await page.title();
  let content = '';

  const textContent = await page.evaluate(() => document.body.innerText);

  content = textContent;

  // Apply objective-specific extraction if needed
  const links = await page.evaluate(() =>
    Array.from(document.querySelectorAll('a'))
      .map((a) => ({
        text: a.textContent?.trim() || '',
        href: a.href,
      }))
      .filter((link) => link.href.startsWith('http'))
  );

  return {
    title,
    content,
    links,
  };
}

export const createPlaywrightTool = () =>
  tool({
    description:
      'A tool that can perform web searches and return the results in a structured format.',
    parameters: z.object({
      url: z.string().describe('The url of the page to scrape.'),
      objective: z.string().describe('The objective of the search.'),
    }),
    execute: async ({ url, objective }) => {
      let browser: Browser | null = null;
      let result: ScrapingResult;

      try {
        // Initialize browser
        browser = await initBrowser();
        const context = await browser.newContext();
        const page = await context.newPage();

        // Configure timeouts
        await page.setDefaultTimeout(browserConfig.timeout);
        await page.setDefaultNavigationTimeout(browserConfig.timeout);

        // Navigate to URL
        await page.goto(url, { waitUntil: 'load' });

        // Extract content
        const extracted = await extractContent(page, objective);

        result = {
          title: extracted.title || '',
          content: extracted.content.slice(2000) || '',
          links: extracted.links,
          metadata: {
            url,
            timestamp: new Date().toISOString(),
            status: 'success',
          },
        };
      } catch (error) {
        console.error('Error in PlaywrightTool:', error);
        result = {
          title: '',
          content: '',
          metadata: {
            url,
            timestamp: new Date().toISOString(),
            status: 'error',
            message:
              error instanceof Error ? error.message : 'Unknown error occurred',
          },
        };
      } finally {
        // Ensure browser is closed
        if (browser) {
          await browser.close();
        }
      }

      return result;
    },
  });
