import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const PORT = parseInt(process.env.PORT || "3847", 10);
const DB_PATH = process.env.DB_PATH || join(__dirname, "..", "data", "brosif.db");

const db = new DatabaseSync(DB_PATH, { open: true, readOnly: true });
console.log(`opened ${DB_PATH}`);

const MIME = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function parseQuery(raw) {
  const terms = [];
  const filters = {};
  for (const token of raw.split(/\s+/)) {
    const m = token.match(/^(lang|source|pos):(.+)$/i);
    if (m) {
      filters[m[1].toLowerCase()] = m[2].toLowerCase();
    } else {
      terms.push(token);
    }
  }
  return { terms, filters };
}

function buildFtsMatch(terms) {
  return terms
    .map((t) => {
      const tokens = t.match(/[\w'-]+/gu) || [];
      return tokens.map((tok) => `"${tok}"*`).join(" OR ");
    })
    .filter(Boolean)
    .join(" AND ");
}

function handleSearch(params) {
  const q = params.get("q") || "";
  const limit = Math.min(parseInt(params.get("limit") || "50", 10), 200);
  if (!q.trim()) return { results: [] };

  const { terms } = parseQuery(q);
  const fts = buildFtsMatch(terms);
  if (!fts) return { results: [] };

  const stmt = db.prepare(`
    SELECT e.id, e.headword, e.part_of_speech, e.language, e.definition,
           s.name AS source_name
    FROM entries_fts
    JOIN entries e ON e.id = entries_fts.rowid
    JOIN sources s ON s.id = e.source_id
    WHERE entries_fts MATCH ?
    ORDER BY bm25(entries_fts, 8.0, 2.0, 4.0, 3.0)
    LIMIT ?
  `);
  return { results: stmt.all(fts, limit) };
}

function handleDetail(params) {
  const id = parseInt(params.get("id") || "0", 10);
  const lang = params.get("lang");
  const normalized = params.get("normalized");

  if (lang && normalized) {
    const stmt = db.prepare(`
      SELECT e.*, s.name AS source_name, s.version, s.homepage,
             s.license, s.attribution
      FROM entries e JOIN sources s ON s.id = e.source_id
      WHERE e.language = ? AND e.normalized = ?
      ORDER BY e.part_of_speech, s.name, e.id
    `);
    const senses = stmt.all(lang, normalized);
    return senses.length ? { senses } : { error: "not found" };
  }
  if (id) {
    const stmt = db.prepare(`
      SELECT e.*, s.name AS source_name, s.version, s.homepage,
             s.license, s.attribution
      FROM entries e JOIN sources s ON s.id = e.source_id
      WHERE e.id = ?
    `);
    const rows = stmt.all(id);
    return rows.length ? { entry: rows[0] } : { error: "not found" };
  }
  return { error: "provide id or lang+normalized" };
}

function handleStats() {
  return { sources: db.prepare("SELECT * FROM sources ORDER BY name").all() };
}

async function serveStatic(pathname, res) {
  const safePath = pathname.replace(/\.\./g, "").replace(/^\/+/, "");
  const filePath = join(__dirname, safePath || "index.html");
  try {
    await stat(filePath);
    const content = await readFile(filePath);
    const ext = extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(content);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("not found");
  }
}

const server = createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://localhost:${PORT}`);

  try {
    let data;
    if (url.pathname === "/health") {
      data = { ok: true };
    } else if (url.pathname === "/query") {
      data = handleSearch(url.searchParams);
    } else if (url.pathname === "/detail") {
      data = handleDetail(url.searchParams);
    } else if (url.pathname === "/stats") {
      data = handleStats();
    } else {
      await serveStatic(url.pathname, res);
      return;
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(data));
  } catch (err) {
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: err.message }));
  }
});

server.listen(PORT, () => {
  console.log(`brosif web listening on http://localhost:${PORT}`);
});
