// Word Territory JA frontend API hotfix
// Fixes: payload/positional argument mismatch, readable API errors, threat array normalization.

export const WT_JA_API_HOTFIX_20260606 = true;

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  "https://word-territory-ja.onrender.com";

function normalizeErrorMessage(data, status) {
  const detail = data?.detail ?? data?.error ?? data?.message;

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
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
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
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    throw new Error(normalizeErrorMessage(data, res.status));
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
    Array.isArray(value.affected_cells) ||
    Array.isArray(value.captured_cells)
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

      const hasCells = Array.isArray(item.cells) && item.cells.length > 0;
      return hasMainCell || hasCells;
    });
}

function movePayloadFromArgs(args) {
  if (args.length === 1 && args[0] && typeof args[0] === "object") {
    return args[0];
  }

  const [gameId, row, col, letter, path] = args;
  return {
    game_id: gameId,
    row,
    col,
    letter,
    path: Array.isArray(path) ? path : []
  };
}

function seedPayloadFromArgs(args) {
  if (args.length >= 2 && args[1] && typeof args[1] === "object") {
    return args[1];
  }

  const [, row, col, letter] = args;
  return { row, col, letter };
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

export async function submitMove(...args) {
  const payload = movePayloadFromArgs(args);
  const gameId = payload.game_id || args[0];

  if (!gameId) throw new Error("ゲームIDがありません。New Gameを押してからもう一度試してください。");

  return request(`/games/${encodeURIComponent(gameId)}/move`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function seedMove(gameId, ...args) {
  const payload = seedPayloadFromArgs([gameId, ...args]);

  if (!gameId) throw new Error("ゲームIDがありません。New Gameを押してからもう一度試してください。");

  return request(`/games/${encodeURIComponent(gameId)}/seed-move`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function previewMove(gameId, ...args) {
  const payload = args.length === 1 && args[0] && typeof args[0] === "object"
    ? args[0]
    : movePayloadFromArgs([gameId, ...args]);

  if (!gameId) return { errorMessage: "ゲームIDがありません。" };

  return request(`/games/${encodeURIComponent(gameId)}/preview-move`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function passTurn(gameId) {
  return request(`/games/${encodeURIComponent(gameId)}/pass`, { method: "POST" });
}

export async function botMove(gameId) {
  return request(`/games/${encodeURIComponent(gameId)}/bot-move`, { method: "POST" });
}

export async function autoMove(gameId, demo = false) {
  const q = demo ? "?demo=true" : "";
  return request(`/games/${encodeURIComponent(gameId)}/auto-move${q}`, { method: "POST" });
}

export async function getSuggestions(gameId) {
  const data = await request(`/games/${encodeURIComponent(gameId)}/suggestions`);
  return normalizeList(data?.suggestions ?? data);
}

export async function getAlmost(gameId) {
  const data = await request(`/games/${encodeURIComponent(gameId)}/almost`);
  return normalizeList(data?.almost ?? data);
}

export async function getSynergyOptions(gameId) {
  return request(`/games/${encodeURIComponent(gameId)}/synergy-options`);
}

export async function selectSynergy(gameId, card) {
  return request(`/games/${encodeURIComponent(gameId)}/select-synergy`, {
    method: "POST",
    body: JSON.stringify({ card })
  });
}

export async function getMarket(gameId) {
  return request(`/games/${encodeURIComponent(gameId)}/market`);
}

export async function getLetterPreview(gameId, letter) {
  if (!gameId || !letter) return { letter: letter || "", moves: [] };
  return request(`/games/${encodeURIComponent(gameId)}/letter-preview/${encodeURIComponent(letter)}`);
}

export async function useFreeLetter(gameId, payloadOrLetter, source = "free") {
  const payload =
    payloadOrLetter && typeof payloadOrLetter === "object"
      ? payloadOrLetter
      : { letter: payloadOrLetter, source };

  return request(`/games/${encodeURIComponent(gameId)}/free-letter`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getThreat(gameId) {
  if (!gameId) return [];
  const data = await request(`/games/${encodeURIComponent(gameId)}/threat`);
  return normalizeThreatPayload(data);
}

export async function createAsyncMatch(payload = {}) {
  return request("/async/games", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAsyncMatch(gameId, token) {
  return request(`/async/games/${encodeURIComponent(gameId)}?token=${encodeURIComponent(token)}`);
}

export async function submitAsyncMove(gameId, token, ...args) {
  const payload = movePayloadFromArgs(args);
  if (!payload.game_id) payload.game_id = gameId;

  return request(`/async/games/${encodeURIComponent(gameId)}/move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function seedAsyncMove(gameId, token, ...args) {
  const payload = seedPayloadFromArgs([gameId, ...args]);

  return request(`/async/games/${encodeURIComponent(gameId)}/seed-move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function passAsyncTurn(gameId, token) {
  return request(`/async/games/${encodeURIComponent(gameId)}/pass?token=${encodeURIComponent(token)}`, {
    method: "POST"
  });
}

export async function joinWaitlist(email) {
  return request("/waitlist", {
    method: "POST",
    body: JSON.stringify({ email })
  });
}
