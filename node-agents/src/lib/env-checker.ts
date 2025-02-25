export const validateApiKeys = (
  API_KEYS: Record<string, string | undefined>
) => {
  // check if API_KEYS has any undefined values
  //   const hasUndefined = Object.values(API_KEYS).some(
  //     (value) => value === undefined
  //   );
  //   if (hasUndefined) {
  //     console.warn("API keys are not set. Please set them in the .env file.");
  //     process.exit(1);
  //   }
  Object.entries(API_KEYS).forEach(
    ([key, value]: [string, string | undefined], index: number) => {
      if (value === undefined) {
        console.warn(
          `API key ${key} is not set. Please set it in the .env file.`
        );
      }
      if (value === "") {
        console.warn(
          `API key ${key} is empty. Please set it in the .env file.`
        );
      }
    }
  );
};
