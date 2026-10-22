import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { loadLocalSupabaseEnv } from './load-local-env.mjs';

// The machine-level environment can carry a stale SUPABASE_* key (for another
// project) and Next does not let .env files override variables that are already
// set. loadLocalSupabaseEnv() drops the inherited values first so .env.local
// wins, exactly like the dev launcher does.
loadLocalSupabaseEnv();

const require = createRequire(import.meta.url);
const nextCli = require.resolve('next/dist/bin/next');
const args = process.argv.slice(2);
process.argv.splice(1, 1, nextCli, 'start', ...args);
await import(pathToFileURL(nextCli).href);
