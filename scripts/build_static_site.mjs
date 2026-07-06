import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

await cp(resolve(root, "index.html"), resolve(dist, "index.html"));
await cp(resolve(root, "web"), resolve(dist, "web"), { recursive: true });
await cp(resolve(root, "public"), dist, { recursive: true });

console.log(`Static dashboard built at ${dist}`);
