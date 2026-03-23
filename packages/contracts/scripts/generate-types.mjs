import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "json-schema-to-typescript";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const schemasDir = path.join(rootDir, "schemas");
const outDir = path.join(rootDir, "src", "generated");
const outFile = path.join(outDir, "contracts.ts");

const names = await readdir(schemasDir);
const schemaFiles = names
  .filter((name) => name.endsWith(".schema.json"))
  .sort();

await mkdir(outDir, { recursive: true });

const chunks = [
  "/* eslint-disable */",
  "// Auto-generated from JSON Schema. Do not edit manually."
];

for (const fileName of schemaFiles) {
  const absolutePath = path.join(schemasDir, fileName);
  const source = await readFile(absolutePath, "utf8");
  const schema = JSON.parse(source);
  const title = schema.title ?? fileName.replace(".schema.json", "");
  const output = await compile(schema, title, {
    cwd: schemasDir,
    unreachableDefinitions: true,
    bannerComment: ""
  });
  chunks.push(output.trim());
}

await writeFile(outFile, `${chunks.join("\n\n")}\n`, "utf8");
console.log(`Generated ${outFile}`);
