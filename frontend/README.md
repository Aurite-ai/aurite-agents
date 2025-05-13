# Aurite AI Studio - Frontend

## 1. Overview

This directory contains the source code for the Aurite AI Studio frontend, a web-based user interface designed for developers to interact with the Aurite Agents Framework. It allows users to manage configurations, build and register agentic components, execute agents/workflows, and monitor system status.

The frontend is built as a Single Page Application (SPA).

## 2. Tech Stack

*   **Framework/Library:** React 19
*   **Build Tool / Dev Server:** Vite
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS v3
    *   Custom Dracula theme
*   **Package Manager:** Yarn
*   **State Management:** Zustand

## 3. Project Structure

*   `public/`: Static assets that are directly copied to the build output.
*   `src/`: Main source code for the application.
    *   `assets/`: Static assets like images, fonts, etc., that are imported into components.
    *   `components/`: Reusable UI components.
        *   `auth/`: Authentication related components (e.g., API Key Modal).
        *   `layout/`: Components defining the overall page structure (e.g., `Layout.tsx`, `Header.tsx`, `ComponentSidebar.tsx`).
    *   `features/`: Modules for specific application features (e.g., `configure`, `execute`, `evaluate`). Each feature typically contains its own views and components.
    *   `lib/`: Utility functions, API client logic, etc.
    *   `store/`: Zustand stores for global state management (e.g., `authStore.ts`, `uiStore.ts`).
    *   `types/`: TypeScript type definitions.
    *   `App.tsx`: The root React component.
    *   `main.tsx`: The entry point that renders the React application.
    *   `index.css`: Global styles and Tailwind CSS directives.
*   `index.html`: The main HTML entry point for the SPA.
*   `vite.config.ts`: Vite configuration (build, dev server, plugins).
*   `tailwind.config.js`: Tailwind CSS configuration (theme, content paths, plugins).
*   `postcss.config.js`: PostCSS configuration (intentionally kept minimal or blank as Vite handles Tailwind integration).
*   `package.json`: Project metadata, dependencies, and scripts.
*   `yarn.lock`: Yarn lockfile for deterministic dependency installation.
*   `tsconfig.json` (and variants): TypeScript compiler configuration.

## 4. Key Configuration Files

*   **`vite.config.ts`**:
    *   Configures the Vite development server, build process, and server proxy.
    *   Sets up PostCSS plugins, including `tailwindcss` (for v3) and `autoprefixer`.
*   **`tailwind.config.js`**:
    *   Defines the paths for Tailwind's Just-In-Time (JIT) engine to scan for class usage via the `content` array.
    *   Extends the default Tailwind theme, notably under `theme.extend.colors` to include the custom Dracula color palette.
*   **`postcss.config.js`**:
    *   This file is often minimal or blank in Vite projects when Tailwind is configured directly within `vite.config.ts`'s PostCSS options.
*   **`src/index.css`**:
    *   Includes the core Tailwind CSS directives: `@tailwind base;`, `@tailwind components;`, and `@tailwind utilities;`.
    *   Can also contain any custom global CSS or base style overrides.

## 5. Getting Started / Running Locally

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    yarn install
    ```
3.  Start the development server:
    ```bash
    yarn dev
    ```
    The application will typically be available at `http://localhost:5173`.

## 6. Styling Approach

*   Styling is primarily handled using **Tailwind CSS v3** utility classes directly in the JSX of the components.
*   A custom **Dracula theme** is implemented. Colors are defined in `tailwind.config.js` within the `theme.extend.colors` object (e.g., `dracula-background`, `dracula-foreground`, `dracula-pink`). These can then be used with Tailwind's color utility classes (e.g., `bg-dracula-background`, `text-dracula-pink`, `border-dracula-comment`).

## 7. Layout Components

The main application layout is structured by a few key components in `src/components/layout/`:

*   **`Layout.tsx`**: The top-level layout component that orchestrates the main sections of the UI. It renders the `Header` and `ComponentSidebar`, and manages the main content area.
*   **`Header.tsx`**: The combined top navigation bar. It includes:
    *   Application logo and title.
    *   Action tabs (Build, Configure, Execute, Evaluate).
    *   User profile icon.
    It uses Flexbox to arrange these elements.
*   **`ComponentSidebar.tsx`**: The sidebar used for selecting different component types (Clients, Agents, etc.) within a chosen action.

This README provides a basic guide to the frontend setup.
