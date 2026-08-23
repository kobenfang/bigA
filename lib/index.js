/**
 * @kobenfang/dsh-biga — bundled Agent Skill for DeepSeek Harness (dsh).
 *
 * Cordis plugin entry: registers a skill provider on ctx.skills exposing the
 * SKILL.md at the package root, so `dsh plugin add` installs this skill.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SKILL_FILE = fileURLToPath(new URL('../SKILL.md', import.meta.url));
const SKILL_DIR = path.dirname(SKILL_FILE);
const PKG = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

export const name = 'biga';
export const inject = ['skills'];

export function parseFrontmatter(text) {
  const m = text.match(/^---[\r\n]([\s\S]*?)[\r\n]---[\r\n]?/);
  const fm = {};
  if (!m) return fm;
  const lines = m[1].split(/[\r\n]/);
  let key = null, buf = [], block = false;
  const flush = () => {
    if (key !== null) {
      let val = buf.join(block ? '\n' : ' ').trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) val = val.slice(1, -1);
      fm[key] = val;
    }
    key = null; buf = []; block = false;
  };
  for (const line of lines) {
    const km = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (km && !block) {
      flush();
      key = km[1];
      const v = km[2];
      if (v === '>' || v === '|' || v === '>-' || v === '|-' || v === '>+' || v === '|+') { block = true; buf = []; }
      else buf = [v];
    } else if (block) {
      if (/^\s+\S/.test(line)) buf.push(line.trim());
      else flush();
    }
  }
  flush();
  return fm;
}

const provider = {
  name: PKG.name,
  list() {
    if (!fs.existsSync(SKILL_FILE)) return Promise.resolve([]);
    const raw = fs.readFileSync(SKILL_FILE, 'utf8');
    const fm = parseFrontmatter(raw);
    const name = (fm.name || '').trim().replace(/^["']|["']$/g, '') || 'biga';
    const cand = {
      name,
      description: (fm.description || '').trim(),
      invocation: { modelInvocable: true, userInvocable: true },
      provider: PKG.name,
      source: 'bundled',
      resourceBase: { kind: 'directory', path: SKILL_DIR },
      rank: 0,
      locator: pathToFileURL(SKILL_FILE),
      metadata: fm,
    };
    return Promise.resolve([cand]);
  },
  async get(candidate) {
    const raw = fs.readFileSync(SKILL_FILE, 'utf8');
    return {
      name: candidate.name,
      description: candidate.description,
      body: raw,
      invocation: { modelInvocable: true, userInvocable: true },
      source: 'bundled',
      resourceBase: { kind: 'directory', path: SKILL_DIR },
      metadata: candidate.metadata,
    };
  },
};

export function apply(ctx) {
  return ctx.skills.registerProvider(() => provider);
}
