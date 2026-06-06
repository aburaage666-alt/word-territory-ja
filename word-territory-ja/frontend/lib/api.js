export const WT_API_THREAT_NORMALIZE_V1 = true;

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  "https://word-territory-ja.onrender.com";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const message = data?.detail || data?.error || `HTTP ${res.status}`;
    throw new Error(message);
  }

  return data;
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
    Array.isArray(value.affected_cells)
  ) {
    return [value];
  }

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
        item?.cells ??
        item?.path ??
        item?.threat_cells ??
        item?.affected_cells ??
        item?.captured_cells ??
        [];

      const cells = normalizeList(cellSource)
        .map(toCell)
        .filter(Boolean);

      const mainCell =
        toCell(item) ||
        toCell(item?.move) ||
        toCell(item?.target) ||
        cells[0] ||
        null;

      return {
        ...(item || {}),
        row: mainCell?.row,
        col: mainCell?.col,
        cells
      };
    })
    .filter((item) => {
      const hasMainCell =
        Number.isFinite(Number(item.row)) &&
        Number.isFinite(Number(item.col));

      const hasCells =
        Array.isArray(item.cells) &&
        item.cells.length > 0;

      return hasMainCell || hasCells;
    });
}

export async function createGame(payload = {}) {
  return request("/games", {
    method: "POST",
    body: JSON.stringify(payload)
  });
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
  return request("/daily/scores", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function submitMove(gameId, row, col, letter, path) {
  return request(`/games/${gameId}/move`, {
    method: "POST",
    body: JSON.stringify({ row, col, letter, path })
  });
}

export async function seedMove(gameId, row, col, letter) {
  return request(`/games/${gameId}/seed-move`, {
    method: "POST",
    body: JSON.stringify({ row, col, letter })
  });
}

export async function previewMove(gameId, row, col, letter, path) {
  return request(`/games/${gameId}/preview-move`, {
    method: "POST",
    body: JSON.stringify({ row, col, letter, path })
  });
}

export async function passTurn(gameId) {
  return request(`/games/${gameId}/pass`, { method: "POST" });
}

export async function botMove(gameId) {
  return request(`/games/${gameId}/bot-move`, { method: "POST" });
}

export async function autoMove(gameId, demo = false) {
  const q = demo ? "?demo=true" : "";
  return request(`/games/${gameId}/auto-move${q}`, { method: "POST" });
}

export async function getSuggestions(gameId) {
  return request(`/games/${gameId}/suggestions`);
}

export async function getAlmost(gameId) {
  return request(`/games/${gameId}/almost`);
}

export async function getSynergyOptions(gameId) {
  return request(`/games/${gameId}/synergy-options`);
}

export async function selectSynergy(gameId, card) {
  return request(`/games/${gameId}/select-synergy`, {
    method: "POST",
    body: JSON.stringify({ card })
  });
}

export async function getMarket(gameId) {
  return request(`/games/${gameId}/market`);
}

export async function getLetterPreview(gameId, letter) {
  return request(`/games/${gameId}/letter-preview/${encodeURIComponent(letter)}`);
}

export async function useFreeLetter(gameId, payload) {
  return request(`/games/${gameId}/free-letter`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getThreat(gameId) {
  const data = await request(`/games/${gameId}/threat`);
  return normalizeThreatPayload(data);
}

export async function createAsyncMatch(payload = {}) {
  return request("/async/games", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAsyncMatch(gameId, token) {
  return request(`/async/games/${gameId}?token=${encodeURIComponent(token)}`);
}

export async function submitAsyncMove(gameId, token, row, col, letter, path) {
  return request(`/async/games/${gameId}/move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify({ row, col, letter, path })
  });
}

export async function seedAsyncMove(gameId, token, row, col, letter) {
  return request(`/async/games/${gameId}/seed-move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify({ row, col, letter })
  });
}

export async function passAsyncTurn(gameId, token) {
  return request(`/async/games/${gameId}/pass?token=${encodeURIComponent(token)}`, {
    method: "POST"
  });
}

export async function joinWaitlist(email) {
  return request("/waitlist", {
    method: "POST",
    body: JSON.stringify({ email })
  });
}
