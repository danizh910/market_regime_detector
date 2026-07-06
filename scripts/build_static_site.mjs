import { cp, mkdir, readFile, rm, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

await cp(resolve(root, "index.html"), resolve(dist, "index.html"));
await cp(resolve(root, "web"), resolve(dist, "web"), { recursive: true });
await cp(resolve(root, "public"), dist, { recursive: true });

const assertFile = async (path) => {
  try {
    const info = await stat(path);
    if (!info.isFile()) throw new Error(`${path} is not a file`);
  } catch {
    throw new Error(`Missing required dashboard asset: ${path}`);
  }
};

const manifestPath = resolve(dist, "manifest.json");
await assertFile(manifestPath);
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
for (const run of manifest.runs ?? []) {
  for (const assetPath of Object.values(run.paths ?? {})) {
    await assertFile(resolve(dist, assetPath.replace(/^\/+/, "")));
  }
}

console.log(`Static dashboard built at ${dist}`);
