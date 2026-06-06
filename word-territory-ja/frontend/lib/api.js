// Word Territory JA frontend API compatibility hotfix v2
// Fixes: game_id / gameId mismatch, payload-vs-positional calls, readable errors, threat response normalization.
export const WT_JA_API_GAMEID_HOTFIX_20260606_V2 = true;


const WT_JA_API_MARKET_SANITIZER_20260606 = true;
const WT_JA_KANA_POOL = "???????????????????????????????????????????????????????????????????????".split("");

function wtJaRandomKana() {
  return WT_JA_KANA_POOL[Math.floor(Math.random() * WT_JA_KANA_POOL.length)];
}

function wtJaIsBadMarketToken(value) {
  return (
    typeof value === "string" &&
    (
      /^[A-Za-z]$/.test(value) ||
      value === "FREE" ||
      value === "Free" ||
      value === "*"
    )
  );
}

function wtJaSanitizeApiData(value) {
  if (wtJaIsBadMarketToken(value)) {
    return wtJaRandomKana();
  }

  if (Array.isArray(value)) {
    return value.map(wtJaSanitizeApiData);
  }

  if (value && typeof value === "object") {
    const out = {};
    Object.entries(value).forEach(([k, v]) => {
      out[k] = wtJaSanitizeApiData(v);
    });
    return out;
  }

  return value;
}


const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  "https://word-territory-ja.onrender.com";

function normalizeErrorMessage(data, status) {
  const detail = data?.detail ?? data?.error ?? data?.message;

  if (status === 404 && String(detail || "").toLowerCase().includes("game not found")) {
    return "ゲームが切れました。New Gameを押して新しいゲームを開始してください。Render無料環境では再起動・再デプロイ時にゲームIDが消えます。";
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") return String(item);
        const loc = Array.isArray(item.loc) ? item.loc.join(".") : item.loc;
        const msg = item.msg || item.message || JSON.stringify(item);
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join(" / ");
  }

  if (detail && typeof detail === "object") {
    try { return JSON.stringify(detail); } catch { return String(detail); }
  }

  return detail ? String(detail) : `HTTP ${status}`;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;
  try { data = await res.json(); } catch { data = null; }

  if (!res.ok) {
    throw new Error(normalizeErrorMessage(data, res.status));
  }
  return wtJaSanitizeApiData(data);
}

function normalizeList(value) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== "object") return [];
  if (Array.isArray(value.threats)) return value.threats;
  if (Array.isArray(value.moves)) return value.moves;
  if (Array.isArray(value.items)) return value.items;
  if (Array.isArray(value.results)) return value.results;
  if (Array.isArray(value.data)) return value.data;
  if (Array.isArray(value.threat_moves)) return value.threat_moves;
  if (
    Array.isArray(value.cells) ||
    Array.isArray(value.path) ||
    Array.isArray(value.threat_cells) ||
    Array.isArray(value.affected_cells) ||
    Array.isArray(value.captured_cells)
  ) return [value];
  return [];
}

function toCell(value) {
  if (!value || typeof value !== "object") return null;
  const row = Number(value.row ?? value.r ?? value.y);
  const col = Number(value.col ?? value.c ?? value.x);
  if (!Number.isFinite(row) || !Number.isFinite(col)) return null;
  return { row, col };
}

function normalizeThreatPayload(value) {
  return normalizeList(value)
    .map((item) => {
      const cellSource =
        item?.cells ?? item?.path ?? item?.threat_cells ?? item?.affected_cells ?? item?.captured_cells ?? [];
      const cells = normalizeList(cellSource).map(toCell).filter(Boolean);
      const mainCell = toCell(item) || toCell(item?.move) || toCell(item?.target) || cells[0] || null;
      return { ...(item || {}), row: mainCell?.row, col: mainCell?.col, cells };
    })
    .filter((item) => {
      const hasMainCell = Number.isFinite(Number(item.row)) && Number.isFinite(Number(item.col));
      const hasCells = Array.isArray(item.cells) && item.cells.length > 0;
      return hasMainCell || hasCells;
    });
}

function extractGameId(...values) {
  for (const value of values) {
    if (!value) continue;
    if (typeof value === "string") return value;
    if (typeof value === "object") {
      const candidate =
        value.game_id ?? value.gameId ?? value.id ?? value.game?.game_id ?? value.game?.gameId;
      if (typeof candidate === "string" && candidate.trim()) return candidate;
    }
  }
  return "";
}

function normalizePath(path) {
  return Array.isArray(path)
    ? path.map((p) => ({ row: Number(p.row), col: Number(p.col) })).filter((p) => Number.isFinite(p.row) && Number.isFinite(p.col))
    : [];
}

function movePayloadFromArgs(args) {
  let payload;
  if (args.length === 1 && args[0] && typeof args[0] === "object") {
    payload = { ...args[0] };
  } else if (args.length >= 2 && args[1] && typeof args[1] === "object") {
    payload = { ...args[1] };
    if (!payload.game_id && !payload.gameId) payload.game_id = extractGameId(args[0]);
  } else {
    const [gameId, row, col, letter, path] = args;
    payload = { game_id: extractGameId(gameId), row, col, letter, path };
  }

  const gameId = extractGameId(payload, args[0]);
  return {
    game_id: gameId,
    row: Number(payload.row),
    col: Number(payload.col),
    letter: String(payload.letter || "").slice(0, 1),
    path: normalizePath(payload.path)
  };
}

function seedPayloadFromArgs(args) {
  let payload;
  if (args.length === 1 && args[0] && typeof args[0] === "object") {
    payload = { ...args[0] };
  } else if (args.length >= 2 && args[1] && typeof args[1] === "object") {
    payload = { ...args[1] };
    if (!payload.game_id && !payload.gameId) payload.game_id = extractGameId(args[0]);
  } else {
    const [gameId, row, col, letter] = args;
    payload = { game_id: extractGameId(gameId), row, col, letter };
  }
  return {
    game_id: extractGameId(payload, args[0]),
    row: Number(payload.row),
    col: Number(payload.col),
    letter: String(payload.letter || "").slice(0, 1)
  };
}

function assertGameId(gameId) {
  if (!gameId || typeof gameId !== "string") {
    throw new Error("ゲームIDがありません。New Gameを押して新しいゲームを開始してください。");
  }
}

export async function createGame(payload = {}) {
  return request("/games", { method: "POST", body: JSON.stringify(payload) });
}

export async function createDailyGame() {
  return request("/daily/games", { method: "POST" });
}

export async function getDailyInfo() {
  return request("/daily/today");
}

export async function getDailyLeaderboard() {
  return request("/daily/leaderboard");
}

export async function submitDailyScore(payload) {
  return request("/daily/scores", { method: "POST", body: JSON.stringify(payload) });
}

export async function submitMove(...args) {
  const payload = movePayloadFromArgs(args);
  const gameId = payload.game_id;
  assertGameId(gameId);
  return request(`/games/${encodeURIComponent(gameId)}/move`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function seedMove(...args) {
  const payload = seedPayloadFromArgs(args);
  const gameId = payload.game_id;
  assertGameId(gameId);
  const body = { row: payload.row, col: payload.col, letter: payload.letter };
  return request(`/games/${encodeURIComponent(gameId)}/seed-move`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function previewMove(...args) {
  const payload = movePayloadFromArgs(args);
  const gameId = payload.game_id || extractGameId(args[0]);
  if (!gameId) return { errorMessage: "ゲームIDがありません。New Gameを押してください。" };
  return request(`/games/${encodeURIComponent(gameId)}/preview-move`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function passTurn(gameId) {
  gameId = extractGameId(gameId);
  assertGameId(gameId);
  return request(`/games/${encodeURIComponent(gameId)}/pass`, { method: "POST" });
}

export async function botMove(gameId) {
  gameId = extractGameId(gameId);
  assertGameId(gameId);
  return request(`/games/${encodeURIComponent(gameId)}/bot-move`, { method: "POST" });
}

export async function autoMove(gameId, demo = false) {
  gameId = extractGameId(gameId);
  assertGameId(gameId);
  const q = demo ? "?demo=true" : "";
  return request(`/games/${encodeURIComponent(gameId)}/auto-move${q}`, { method: "POST" });
}

export async function getSuggestions(gameId) {
  gameId = extractGameId(gameId);
  if (!gameId) return [];
  const data = await request(`/games/${encodeURIComponent(gameId)}/suggestions`);
  return normalizeList(data?.suggestions ?? data);
}

export async function getAlmost(gameId) {
  gameId = extractGameId(gameId);
  if (!gameId) return [];
  const data = await request(`/games/${encodeURIComponent(gameId)}/almost`);
  return normalizeList(data?.almost ?? data);
}

export async function getSynergyOptions(gameId) {
  gameId = extractGameId(gameId);
  if (!gameId) return { options: [] };
  return request(`/games/${encodeURIComponent(gameId)}/synergy-options`);
}

export async function selectSynergy(gameId, card) {
  gameId = extractGameId(gameId);
  assertGameId(gameId);
  return request(`/games/${encodeURIComponent(gameId)}/select-synergy`, {
    method: "POST",
    body: JSON.stringify({ card })
  });
}

export async function getMarket(gameId) {
  gameId = extractGameId(gameId);
  if (!gameId) return { active: [], preview: [], stats: [], freeLetterUsed: false };
  return request(`/games/${encodeURIComponent(gameId)}/market`);
}

export async function getLetterPreview(gameId, letter) {
  gameId = extractGameId(gameId);
  if (!gameId || !letter) return { letter: letter || "", moves: [] };
  return request(`/games/${encodeURIComponent(gameId)}/letter-preview/${encodeURIComponent(letter)}`);
}

export async function useFreeLetter(gameId, payloadOrLetter, source = "free") {
  gameId = extractGameId(gameId);
  assertGameId(gameId);
  const payload = payloadOrLetter && typeof payloadOrLetter === "object"
    ? payloadOrLetter
    : { letter: payloadOrLetter, source };
  return request(`/games/${encodeURIComponent(gameId)}/free-letter`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getThreat(gameId) {
  gameId = extractGameId(gameId);
  if (!gameId) return [];
  const data = await request(`/games/${encodeURIComponent(gameId)}/threat`);
  return normalizeThreatPayload(data);
}

export async function createAsyncMatch(payload = {}) {
  return request("/async/games", { method: "POST", body: JSON.stringify(payload) });
}

export async function getAsyncMatch(gameId, token) {
  gameId = extractGameId(gameId);
  return request(`/async/games/${encodeURIComponent(gameId)}?token=${encodeURIComponent(token)}`);
}

export async function submitAsyncMove(gameId, token, ...args) {
  gameId = extractGameId(gameId);
  const payload = movePayloadFromArgs(args);
  payload.game_id = gameId;
  return request(`/async/games/${encodeURIComponent(gameId)}/move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function seedAsyncMove(gameId, token, ...args) {
  gameId = extractGameId(gameId);
  const payload = seedPayloadFromArgs(args);
  const body = { row: payload.row, col: payload.col, letter: payload.letter };
  return request(`/async/games/${encodeURIComponent(gameId)}/seed-move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function passAsyncTurn(gameId, token) {
  gameId = extractGameId(gameId);
  return request(`/async/games/${encodeURIComponent(gameId)}/pass?token=${encodeURIComponent(token)}`, {
    method: "POST"
  });
}

export async function joinWaitlist(email) {
  return request("/waitlist", { method: "POST", body: JSON.stringify({ email }) });
}
