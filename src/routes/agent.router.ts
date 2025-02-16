import * as agents from '../agents/index';

export default function pickAgent(name: string) {
  return (
    (agents as any)[name] ||
    (() => {
      throw new Error(`Agent ${name} not found`);
    })()
  );
}

export { pickAgent };
