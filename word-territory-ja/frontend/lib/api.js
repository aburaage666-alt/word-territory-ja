export const WT_JA_API_UNICODE_SAFE_V2 = true;


const WT_JA_FREE_API_FIX_20260606 = true;

function wtJaNormalizeFreeLetterForApi(value) {
  const raw = String(value || "").normalize("NFKC");
  const hira = raw.replace(/[\u30a1-\u30f6]/g, ch =>
    String.fromCharCode(ch.charCodeAt(0) - 0x60)
  );
  const chars = Array.from(hira).filter(ch => /^[\u3041-\u3096\u30fc]$/.test(ch));
  return chars.length ? chars[chars.length - 1] : "";
}


// WT_JA_API_LIST_FIX_20260606
function wtJaApiArray(value, key) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== "object") return [];
  if (key && Array.isArray(value[key])) return value[key];
  if (Array.isArray(value.suggestions)) return value.suggestions;
  if (Array.isArray(value.threats)) return value.threats;
  if (Array.isArray(value.almost)) return value.almost;
  if (Array.isArray(value.moves)) return value.moves;
  if (Array.isArray(value.items)) return value.items;
  if (Array.isArray(value.results)) return value.results;
  if (Array.isArray(value.data)) return value.data;
  return [];
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  "https://word-territory-ja.onrender.com";

const WT_JA_KANA_POOL = "\u3042\u3044\u3046\u3048\u304a\u304b\u304d\u304f\u3051\u3053\u3055\u3057\u3059\u305b\u305d\u305f\u3061\u3064\u3066\u3068\u306a\u306b\u306c\u306d\u306e\u306f\u3072\u3075\u3078\u307b\u307e\u307f\u3080\u3081\u3082\u3084\u3086\u3088\u3089\u308a\u308b\u308c\u308d\u308f\u3092\u3093\u304c\u304e\u3050\u3052\u3054\u3056\u3058\u305a\u305c\u305e\u3060\u3062\u3065\u3067\u3069\u3070\u3073\u3076\u3079\u307c\u3071\u3074\u3077\u307a\u307d";

function randomKana() {
  const chars = Array.from(WT_JA_KANA_POOL);
  return chars[Math.floor(Math.random() * chars.length)];
}

function isBadMarketToken(value) {
  return (
    typeof value === "string" &&
    (
      /^[A-Za-z]$/.test(value) ||
      value === "?" ||
      value === "?" ||
      value === "FREE" ||
      value === "Free"
    )
  );
}

function sanitizeApiData(value) {
  if (isBadMarketToken(value)) return randomKana();

  if (Array.isArray(value)) {
    return value.map(sanitizeApiData);
  }

  if (value && typeof value === "object") {
    const out = {};
    Object.entries(value).forEach(([k, v]) => {
      out[k] = sanitizeApiData(v);
    });
    return out;
  }

  return value;
}

function errorMessage(data, fallback) {
  if (!data) return fallback || "?????????????";
  if (typeof data === "string") return data;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((x) => {
      if (typeof x === "string") return x;
      if (x?.msg) return x.msg;
      return JSON.stringify(x);
    }).join(" / ");
  }
  if (data.error) return String(data.error);
  try { return JSON.stringify(data); } catch { return fallback || "???????????"; }
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
    throw new Error(errorMessage(data, `HTTP ${res.status}`));
  }

  return sanitizeApiData(data);
}

function payloadArgs(args) {
  if (args.length === 1 && args[0] && typeof args[0] === "object") {
    const p = args[0];
    return {
      gameId: p.gameId || p.game_id || p.id,
      body: {
        row: p.row,
        col: p.col,
        letter: p.letter,
        path: p.path || []
      }
    };
  }

  const [gameId, row, col, letter, path] = args;
  return {
    gameId,
    body: { row, col, letter, path: path || [] }
  };
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
  return [];
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
  const { gameId, body } = payloadArgs(args);
  if (!gameId) throw new Error("???ID???????New Game?????????");
  return request(`/games/${gameId}/move`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function seedMove(...args) {
  let gameId, body;
  if (args.length === 2 && args[1] && typeof args[1] === "object") {
    gameId = args[0];
    body = args[1];
  } else if (args.length === 1 && args[0] && typeof args[0] === "object") {
    gameId = args[0].gameId || args[0].game_id || args[0].id;
    body = { row: args[0].row, col: args[0].col, letter: args[0].letter };
  } else {
    gameId = args[0];
    body = { row: args[1], col: args[2], letter: args[3] };
  }
  if (!gameId) throw new Error("???ID???????New Game?????????");
  return request(`/games/${gameId}/seed-move`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function previewMove(...args) {
  const { gameId, body } = payloadArgs(args);
  if (!gameId) return { errorMessage: "???ID???????New Game?????????" };
  return request(`/games/${gameId}/preview-move`, {
    method: "POST",
    body: JSON.stringify(body)
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

export async function getSuggestions(gameId) { const data = await request(`/games/${gameId}/suggestions`); return wtJaApiArray(data, "suggestions"); }

export async function getAlmost(gameId) { const data = await request(`/games/${gameId}/almost`); return wtJaApiArray(data, "almost"); }

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

export async function useFreeLetter(gameId, payload, source = "free") {
  let body = {};

  if (typeof payload === "string") {
    body = { letter: payload, source };
  } else if (payload && typeof payload === "object") {
    body = { ...payload };
  }

  if (body.mode && !body.source) {
    body.source = body.mode;
  }

  body.letter = wtJaNormalizeFreeLetterForApi(body.letter);

  if (!body.letter) {
    throw new Error("????1????????????");
  }

  return request(`/games/${gameId}/free-letter`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getThreat(gameId) { const data = await request(`/games/${gameId}/threat`); return wtJaApiArray(data, "threats"); }

export async function createAsyncMatch(payload = {}) {
  return request("/async/games", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAsyncMatch(gameId, token) {
  return request(`/async/games/${gameId}?token=${encodeURIComponent(token)}`);
}

export async function submitAsyncMove(gameId, token, ...args) {
  const { body } = payloadArgs(args);
  return request(`/async/games/${gameId}/move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function seedAsyncMove(gameId, token, ...args) {
  let body;
  if (args.length === 1 && args[0] && typeof args[0] === "object") {
    body = args[0];
  } else {
    body = { row: args[0], col: args[1], letter: args[2] };
  }
  return request(`/async/games/${gameId}/seed-move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    body: JSON.stringify(body)
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
