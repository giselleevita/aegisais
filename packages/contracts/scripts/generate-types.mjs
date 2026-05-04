import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const schemasDir = path.join(rootDir, "schemas");
const outDir = path.join(rootDir, "src", "generated");
const outFile = path.join(outDir, "contracts.ts");

function toPascalCase(value) {
  return value
    .replace(/\.schema\.json$|\.json$/g, "")
    .replace(/[^a-zA-Z0-9]+(.)/g, (_, char) => char.toUpperCase())
    .replace(/^[^a-zA-Z]+/, "")
    .replace(/^common$/i, "Common")
    .replace(/^([a-z])/, (_, char) => char.toUpperCase());
}

const names = await readdir(schemasDir);
const schemaFiles = names.filter((name) => name.endsWith(".json")).sort();

const schemaEntries = await Promise.all(
  schemaFiles.map(async (fileName) => {
    const absolutePath = path.join(schemasDir, fileName);
    const source = await readFile(absolutePath, "utf8");
    const schema = JSON.parse(source);
    const baseName = toPascalCase(fileName) || "SchemaDocument";
    const constName = `${baseName}Schema`;
    const typeName = baseName;

    return {
      constName,
      fileName,
      schema,
      typeName,
    };
  }),
);

await mkdir(outDir, { recursive: true });

const chunks = [
  "/* eslint-disable */",
  "// Auto-generated from JSON Schema. Do not edit manually.",
  'import type { FromSchema } from "json-schema-to-ts";',
];

for (const entry of schemaEntries) {
  chunks.push(
    `export const ${entry.constName} = ${JSON.stringify(entry.schema, null, 2)} as const;`,
  );
}

chunks.push(
  `type SchemaReferences = [${schemaEntries
    .map((entry) => `typeof ${entry.constName}`)
    .join(", ")}];`,
);

for (const entry of schemaEntries.filter((item) =>
  item.fileName.endsWith(".schema.json"),
)) {
  chunks.push(
    `export type ${entry.typeName} = FromSchema<typeof ${entry.constName}, { references: SchemaReferences }>;`,
  );
}

await writeFile(outFile, `${chunks.join("\n\n")}\n`, "utf8");
console.log(`Generated ${outFile}`);
