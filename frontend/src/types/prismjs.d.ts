declare module 'prismjs/components/prism-core' {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const languages: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const highlight: any;
  export { languages, highlight };
}

// If you use other prismjs submodules directly, you might need to declare them too.
// For example:
// declare module 'prismjs/components/prism-json';
// declare module 'prismjs/themes/prism-okaidia.css'; // CSS modules usually don't need this if configured correctly
