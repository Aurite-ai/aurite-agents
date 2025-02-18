/** @type {import('ts-jest').JestConfigWithTsJest} **/
module.exports = {
  moduleFileExtensions: ["js", "json", "ts"],
  rootDir: ".", // Make sure this points to your project root
  testRegex: ".*\\.test\\.ts$",
  transform: {
    "^.+\\.(t|j)s$": "ts-jest",
  },
  injectGlobals: true,
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1", // Match your path aliases
  },
  testEnvironment: "node",
  roots: ["<rootDir>/src/", "<rootDir>/tests/"], // Add your tests directory here
};
