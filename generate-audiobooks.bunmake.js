import bunmake, { rule, phy, glob, $ } from "./bunmake.ts";
import { basename } from "node:path";

phy("all", {
  inputs: "out.m4b",
});

rule("text", {
  inputs: "book.pdf",
  recipe: async ({ inputs }) => {
    await $`mkdir -p mmd text`;
    await $`uv run task nougat ${inputs[0]} -o mmd`;
    await $`uv run task math2text mmd/book.mmd -o text/book.txt --num-chunks 4`;
  },
});

rule("wavs/%.wav", {
  inputs: "text/%.txt",
  recipe: async ({ inputs, target }) => {
    await $`mkdir -p wavs`;
    await $`uv run task make_wavs --tts qwen3 --math True ${inputs[0]} -o ${target}`;
  },
});

const naturalCompare = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" }).compare;

async function getWavInputs(): Promise<string[]> {
  const textRule = bunmake.rules["text"];
  if (textRule) {
    for await (const _ of textRule.makeWithProgress()) {}
  }

  const txtFiles = await glob("text/*.txt");
  txtFiles.sort(naturalCompare);

  return txtFiles.map((f) => `audio/${basename(f, ".txt")}.wav`);
}

rule("out.m4b", {
  inputs: getWavInputs,
  recipe: async ({ inputs, target }) => {
    const {generateAudiobookMetadata} = require('./audiobook-binding-data');
    const controlFiles = generateAudiobookMetadata();
    await $`ffmpeg -y -f concat -safe 0 ${controlFiles.map(f => `-i ${f}`).join(' ')} -map_metadata 1 -c:a aac -b:a 64k ${target}`
    await $`rm ${controlFiles}`
  },
});

bunmake.run();