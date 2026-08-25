// bunmake.ts
import { statSync, existsSync } from "node:fs";

export type RecipeContext = {
  inputs: string[];
  target: string;
};

export type RecipeFn = (ctx: RecipeContext) => Promise<void>;

export type InputsResolver =
  | string
  | string[]
  | Promise<string[]>
  | ((ctx: RecipeContext) => Promise<string[]> | string[]);

export interface RuleOptions {
  inputs?: InputsResolver;
  recipe?: RecipeFn;
  isPhony?: boolean;
}

export class TargetRule {
  target: string;
  inputsDef: RuleOptions["inputs"];
  recipeDef?: RecipeFn;
  isPhony: boolean;

  constructor(target: string, opts: RuleOptions) {
    this.target = target;
    this.inputsDef = opts.inputs;
    this.recipeDef = opts.recipe;
    this.isPhony = opts.isPhony ?? false;
  }

  async resolveInputs(): Promise<string[]> {
    const raw = typeof this.inputsDef === "function"
      ? await this.inputsDef({ target: this.target, inputs: [] })
      : await this.inputsDef;
    if (!raw) return [];
    return Array.isArray(raw) ? raw : [raw];
  }

  async *makeWithProgress(visited = new Set<string>()): AsyncGenerator<string, void, unknown> {
    if (visited.has(this.target)) return;
    visited.add(this.target);

    const inputs = await this.resolveInputs();

    // 1. Resolve DAG dependencies recursively
    for (const input of inputs) {
      const depRule = findOrCreateRule(input);
      if (depRule) {
        yield* depRule.makeWithProgress(visited);
      }
    }

    // 2. Check filesystem modification timestamps
    const needsBuild = await shouldRebuild(this.target, inputs, this.isPhony);

    if (!needsBuild) {
      yield `[bunmake] target '${this.target}' is up to date.`;
      return;
    }

    yield `[bunmake] building '${this.target}'...`;
    if (this.recipeDef) {
      try {
        await this.recipeDef({ inputs, target: this.target });
        yield `[bunmake] target '${this.target}' built successfully.`;
      } catch (err: any) {
        yield `[bunmake] error building '${this.target}': ${err.message}`;
        throw err;
      }
    }
  }
}

// Registries
const explicitRules = new Map<string, TargetRule>();
const patternRules: Array<{
  targetPattern: string;
  inputPattern: string | string[];
  recipe?: RecipeFn;
}> = [];

export function findOrCreateRule(target: string): TargetRule | undefined {
  if (explicitRules.has(target)) return explicitRules.get(target);

  // Match pattern rules (e.g. "mmd/%.mmd")
  for (const pr of patternRules) {
    const regex = new RegExp("^" + escapeRegExp(pr.targetPattern).replace("\\%", "(.+)") + "$");
    const match = target.match(regex);
    if (match) {
      const stem = match[1];
      const mapStem = (pat: string) => pat.replace("%", stem);
      
      const inputs = Array.isArray(pr.inputPattern)
        ? pr.inputPattern.map(mapStem)
        : mapStem(pr.inputPattern);

      const dynamicRule = new TargetRule(target, {
        inputs,
        recipe: pr.recipe,
      });
      explicitRules.set(target, dynamicRule);
      return dynamicRule;
    }
  }

  return undefined;
}

function escapeRegExp(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function shouldRebuild(target: string, inputs: string[], isPhony: boolean): Promise<boolean> {
  if (isPhony || !existsSync(target)) return true;
  const targetTime = statSync(target).mtimeMs;

  for (const input of inputs) {
    if (!existsSync(input)) return true;
    if (statSync(input).mtimeMs > targetTime) return true;
  }
  return false;
}

// Core API Exports
export function rule(target: string, opts: RuleOptions) {
  if (target.includes("%")) {
    patternRules.push({
      targetPattern: target,
      inputPattern: (opts.inputs as string | string[]) || [],
      recipe: opts.recipe,
    });
  } else {
    explicitRules.set(target, new TargetRule(target, opts));
  }
}

export function phy(name: string, opts: RuleOptions) {
  explicitRules.set(name, new TargetRule(name, { ...opts, isPhony: true }));
}

export async function glob(pattern: string): Promise<string[]> {
  const g = new Bun.Glob(pattern);
  const results: string[] = [];
  for await (const file of g.scan(".")) {
    results.push(file);
  }
  return results.sort();
}

export async function run() {
  const target = process.argv[2] || "all";
  const r = findOrCreateRule(target);
  if (!r) {
    console.error(`[bunmake] No rule found to build target '${target}'`);
    process.exit(1);
  }

  for await (const log of r.makeWithProgress()) {
    console.log(log);
  }
}

// Proxy enables dynamic lookups like bunmake.rules['dist/audiobook.mp3']
export const rules = new Proxy({} as Record<string, TargetRule>, {
  get(_, prop: string) {
    return findOrCreateRule(prop);
  },
  set(_, prop: string, val: TargetRule) {
    explicitRules.set(prop, val);
    return true;
  },
});

const bunmake = { rule, phy, glob, run, rules };
export default bunmake;

// CommonJS compatibility bridge
if (typeof module !== "undefined" && module.exports) {
  module.exports = bunmake;
  Object.assign(module.exports, bunmake);
}