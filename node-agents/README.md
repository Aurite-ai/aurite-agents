# Aurite Agent

## Overview

This is the Aurite Agent Code Repository. It contains the source code for agents and sub-agents, an API to access them, and a frontend web
application to interact with the agent.

## Features

- **Express**: Fast, unopinionated, minimalist web framework for Node.js.
- **Axios**: Promise-based HTTP client for the browser and Node.js.
- **Playwright**: Node.js library to automate Chromium, Firefox, and WebKit with a single API.
- **Jest**: Delightful JavaScript Testing Framework with a focus on simplicity.
- **Zod**: TypeScript-first schema declaration and validation library.

## Installation

To install the dependencies, run:

```bash
pnpm install
```

## Scripts

- `dev`: Starts the server in watch mode using `tsx`.
- `start`: Starts the server.
- `test`: Runs the tests using `jest`.

You can run these scripts using:

```bash
pnpm run dev
pnpm run start
pnpm run test
```

## Environment Variables

This project uses `dotenv` to manage environment variables. Create a `.env` file in the root directory and add your variables there.

## License

This project is licensed under the ISC License.

## Dependencies

- `@ai-sdk/openai`: ^1.1.9
- `ai`: ^4.1.17
- `axios`: ^1.7.9
- `dotenv`: ^16.4.7
- `express`: ^4.21.2
- `jest`: ^29.7.0
- `playwright`: ^1.50.1
- `tsx`: ^4.19.2
- `zod`: ^3.24.1

## Dev Dependencies

- `@playwright/test`: ^1.50.1
- `@types/express`: ^5.0.0
- `@types/jest`: ^29.5.14
- `@types/node`: ^22.13.1
- `ts-jest`: ^29.2.5

## Author

Aurite

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

cat node_modules/@modelcontextprotocol/sdk/dist/esm/types.d.ts
