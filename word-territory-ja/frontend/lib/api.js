export const WT_JA_API_DEFINITIVE_20260606 = true;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "https://word-territory-ja.onrender.com";


// WT_FETCH_TIMEOUT_FALLBACK_V1
async function fetchWithTimeout(url, options = {}) {
  return fetch(url, options);
}

// WT_API_READJSON_RUNTIME_FIX_V1
async function readJson(res) {
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message || data.error)) || (typeof data === "string" && data) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

const WT_JA_KANA_POOL = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ";
function kanaChars(){return Array.from(WT_JA_KANA_POOL);}
function isKanaTile(v){return typeof v==="string" && /^[\u3041-\u3096\u30fc]$/.test(v);}
function cleanMarketSeq(seq, existing=new Set(), offset=0){const pool=kanaChars(); const out=[]; (seq||[]).forEach(x=>{if(isKanaTile(x)&&!out.includes(x))out.push(x);}); let i=offset; while(out.length<3){const c=pool[i%pool.length]; i++; if(!out.includes(c)&&!existing.has(c))out.push(c);} return out.slice(0,3);}
function sanitizeMarketData(v){if(Array.isArray(v))return v.map(sanitizeMarketData); if(v&&typeof v==="object"){const out={}; Object.entries(v).forEach(([k,x])=>{out[k]=sanitizeMarketData(x);}); if(Array.isArray(out.marketLetters))out.marketLetters=cleanMarketSeq(out.marketLetters,new Set(),0); if(Array.isArray(out.previewLetters))out.previewLetters=cleanMarketSeq(out.previewLetters,new Set(out.marketLetters||[]),7); if(Array.isArray(out.active))out.active=cleanMarketSeq(out.active,new Set(),0); if(Array.isArray(out.preview))out.preview=cleanMarketSeq(out.preview,new Set(out.active||[]),7); return out;} return v;}
function normalizeKanaInput(value){const raw=String(value||"").normalize("NFKC"); const hira=raw.replace(/[\u30a1-\u30f6]/g,ch=>String.fromCharCode(ch.charCodeAt(0)-0x60)); const chars=Array.from(hira).filter(ch=>/^[\u3041-\u3096\u30fc]$/.test(ch)); return chars.length?chars[chars.length-1]:"";}
function errorMessage(data,fallback){if(!data)return fallback||"通信エラーが発生しました。"; if(typeof data==="string")return data; if(typeof data.detail==="string")return data.detail; if(Array.isArray(data.detail))return data.detail.map(x=>typeof x==="string"?x:(x?.msg||JSON.stringify(x))).join(" / "); if(data.error)return String(data.error); try{return JSON.stringify(data);}catch{return fallback||"エラーが発生しました。";}}
async function request(path,options={}){const res=await fetch(`${API_BASE}${path}`,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}}); let data=null; try{data=await res.json();}catch{} if(!res.ok)throw new Error(errorMessage(data,`HTTP ${res.status}`)); return sanitizeMarketData(data);}
function payloadArgs(args){if(args.length===1&&args[0]&&typeof args[0]==="object"){const p=args[0]; return {gameId:p.gameId||p.game_id||p.id,body:{row:p.row,col:p.col,letter:p.letter,path:p.path||[]}};} const [gameId,row,col,letter,path]=args; return {gameId,body:{row,col,letter,path:path||[]}};}
function listFrom(value,key){if(Array.isArray(value))return value; if(!value||typeof value!=="object")return []; if(key&&Array.isArray(value[key]))return value[key]; for(const k of ["suggestions","threats","almost","moves","items","results","data"]){if(Array.isArray(value[k]))return value[k];} return [];}
export async function createGame(payload={}, boardMode = "standard"){
  const selectedBoardMode =
    (payload && payload.boardMode) ||
    (typeof window !== "undefined" && (window.__wtPendingBoardMode || window.localStorage?.getItem("wtBoardMode"))) ||
    boardMode ||
    "standard";
  const body = {
    ...(payload && typeof payload === "object" ? payload : {}),
    boardMode: selectedBoardMode,
  };
  return request("/games",{method:"POST",body:JSON.stringify(body)});
}
export async function createDailyGame(){return request("/daily/games",{method:"POST"});}
export async function getDailyInfo(){return request("/daily/today");}
export async function getDailyLeaderboard(){return request("/daily/leaderboard");}
export async function submitDailyScore(payload){return request("/daily/scores",{method:"POST",body:JSON.stringify(payload)});}
export async function submitMove(...args){const {gameId,body}=payloadArgs(args); if(!gameId)throw new Error("ゲームIDがありません。新規ゲームを押してください。"); return request(`/games/${gameId}/move`,{method:"POST",body:JSON.stringify(body)});}
export async function seedMove(...args){let gameId,body; if(args.length===2&&args[1]&&typeof args[1]==="object"){gameId=args[0];body=args[1];}else if(args.length===1&&args[0]&&typeof args[0]==="object"){gameId=args[0].gameId||args[0].game_id||args[0].id; body={row:args[0].row,col:args[0].col,letter:args[0].letter};}else{gameId=args[0]; body={row:args[1],col:args[2],letter:args[3]};} if(!gameId)throw new Error("ゲームIDがありません。新規ゲームを押してください。"); return request(`/games/${gameId}/seed-move`,{method:"POST",body:JSON.stringify(body)});}


export async function rotateBlock(gameId, payload) {
  const res = await fetchWithTimeout(`${API_BASE}/games/${gameId}/rotate-block`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson(res);
}

export async function daziMove(gameId, payload) {
  const res = await fetchWithTimeout(`${API_BASE}/games/${gameId}/dazi-move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson(res);
}

export async function daziAsyncMove(gameId, token, payload) {
  const res = await fetchWithTimeout(`${API_BASE}/async/games/${gameId}/dazi-move?token=${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson(res);
}

export async function previewMove(...args){const {gameId,body}=payloadArgs(args); if(!gameId)return {errorMessage:"ゲームIDがありません。新規ゲームを押してください。"}; return request(`/games/${gameId}/preview-move`,{method:"POST",body:JSON.stringify(body)});}
export async function passTurn(gameId){return request(`/games/${gameId}/pass`,{method:"POST"});}
export async function botMove(gameId){return request(`/games/${gameId}/bot-move`,{method:"POST"});}
export async function autoMove(gameId,demo=false){const q=demo?"?demo=true":""; return request(`/games/${gameId}/auto-move${q}`,{method:"POST"});}
export async function getSuggestions(gameId){return listFrom(await request(`/games/${gameId}/suggestions`),"suggestions");}
export async function getAlmost(gameId){return listFrom(await request(`/games/${gameId}/almost`),"almost");}
export async function getSynergyOptions(gameId){return request(`/games/${gameId}/synergy-options`);}
export async function selectSynergy(gameId,card){return request(`/games/${gameId}/select-synergy`,{method:"POST",body:JSON.stringify({card})});}
export async function getMarket(gameId){return request(`/games/${gameId}/market`);}
export async function getLetterPreview(gameId,letter){return request(`/games/${gameId}/letter-preview/${encodeURIComponent(letter)}`);}
export async function useFreeLetter(gameId,payload,source="free"){let body={}; if(typeof payload==="string")body={letter:payload,source}; else if(payload&&typeof payload==="object")body={...payload}; if(body.mode&&!body.source)body.source=body.mode; body.letter=normalizeKanaInput(body.letter); if(!body.letter)throw new Error("ひらがな1文字を入力してください。"); return request(`/games/${gameId}/free-letter`,{method:"POST",body:JSON.stringify(body)});}
export async function swapLetter(gameId, letter=""){return request(`/games/${gameId}/swap-letter`,{method:"POST",body:JSON.stringify({letter})});} export async function getThreat(gameId){return listFrom(await request(`/games/${gameId}/threat`),"threats");}
export async function getIntents(gameId){return listFrom(await request(`/games/${gameId}/intents`),"intents");}
export async function createAsyncMatch(payload={}){return request("/async/games",{method:"POST",body:JSON.stringify(payload)});}
export async function getAsyncMatch(gameId,token){return request(`/async/games/${gameId}?token=${encodeURIComponent(token)}`);}
export async function submitAsyncMove(gameId,token,...args){const {body}=payloadArgs(args); return request(`/async/games/${gameId}/move?token=${encodeURIComponent(token)}`,{method:"POST",body:JSON.stringify(body)});}


export async function rotateAsyncBlock(gameId, token, payload) {
  const res = await fetchWithTimeout(`${API_BASE}/async/games/${gameId}/rotate-block?token=${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson(res);
}

export async function seedAsyncMove(gameId,token,...args){let body; if(args.length===1&&args[0]&&typeof args[0]==="object")body=args[0]; else body={row:args[0],col:args[1],letter:args[2]}; return request(`/async/games/${gameId}/seed-move?token=${encodeURIComponent(token)}`,{method:"POST",body:JSON.stringify(body)});}
export async function passAsyncTurn(gameId,token){return request(`/async/games/${gameId}/pass?token=${encodeURIComponent(token)}`,{method:"POST"});}
export async function joinWaitlist(email){return request("/waitlist",{method:"POST",body:JSON.stringify({email})});}
