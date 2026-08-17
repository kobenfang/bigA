/**
 * Self-test for the @kobenfang/dsh-biga dsh skill plugin.
 */
const mod = await import('./lib/index.js');
if (typeof mod.name !== 'string' || mod.name.length === 0) {
  console.error('FAIL: plugin name missing'); process.exit(1);
}
if (typeof mod.apply !== 'function') {
  console.error('FAIL: plugin apply() missing'); process.exit(1);
}

import fs from 'node:fs';
const raw = fs.readFileSync(new URL('./SKILL.md', import.meta.url), 'utf8');
const fm = mod.parseFrontmatter(raw);
const name = (fm.name || '').trim().replace(/^["']|["']$/g, '');
if (!name) { console.error('FAIL: SKILL.md frontmatter name missing'); process.exit(1); }
if (!(fm.description || '').trim()) { console.error('FAIL: SKILL.md frontmatter description missing'); process.exit(1); }
console.log(`PASS: skill "${name}" loads via plugin "${mod.name}"`);
