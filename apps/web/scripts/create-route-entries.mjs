import { copyFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';

const output = process.argv[2];
if (!output) throw new Error('Usage: node scripts/create-route-entries.mjs <browser-output-directory>');
await mkdir(join(output, 'results'), { recursive: true });
await copyFile(join(output, 'index.html'), join(output, 'results', 'index.html'));
