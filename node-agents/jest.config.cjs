/** @type {import('ts-jest').JestConfigWithTsJest} **/
module.exports = {
  moduleFileExtensions: ["js", "json", "ts"],
  rootDir: ".", // Make sure this points to your project root
  testRegex: ".*\\.test\\.ts$",
  setupFiles: ["<rootDir>/tests/setup/jest.setup.ts"],
  transform: {
    "^.+\\.[tj]s$": [
      "ts-jest",
      {
        tsconfig: {
          allowJs: true,
        },
      },
    ],
  },
  injectGlobals: true,
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1", // Match your path aliases
  },
  testEnvironment: "node",
  roots: ["<rootDir>/src/", "<rootDir>/tests/"], // Add your tests directory here
  transformIgnorePatterns: ["<rootDir>/node_modules/(?!@smithery)"],
  extensionsToTreatAsEsm: [".ts"],
  preset: "ts-jest",
};
