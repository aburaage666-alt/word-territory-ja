// How-to-Play page. The header "説明" link points to /about.
// Self-contained: no API, no shared state.
import React from "react";

const card = {
  border: "1px solid #e2e8f0",
  background: "linear-gradient(180deg,#ffffff,#f8fafc)",
  borderRadius: 16,
  padding: "14px 16px",
  margin: "10px 0",
};

const coreCard = {
  border: "1px solid #22d3ee",
  background: "#ecfeff",
  borderRadius: 16,
  padding: "14px 16px",
  margin: "14px 0",
};

const badge = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minWidth: 30,
  height: 30,
  borderRadius: 999,
  background: "#111827",
  color: "#fff",
  fontWeight: 900,
  fontSize: 14,
  marginRight: 10,
};

function Step({ n, title, body }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 4, margin: "4px 0" }}>
      <span style={badge}>{n}</span>
      <div>
        <div style={{ fontWeight: 900, fontSize: 15, color: "#0f172a" }}>{title}</div>
        <div style={{ fontSize: 13.5, color: "#475569", lineHeight: 1.6 }}>{body}</div>
      </div>
    </div>
  );
}

function Mech({ name, body }) {
  return (
    <div style={card}>
      <div style={{ fontWeight: 900, fontSize: 14.5, color: "#1f2937" }}>{name}</div>
      <div style={{ fontSize: 13.5, color: "#475569", lineHeight: 1.6, marginTop: 4 }}>{body}</div>
    </div>
  );
}

export default function About() {
  return (
    <div
      style={{
        maxWidth: 760,
        margin: "0 auto",
        padding: "20px 16px 48px",
        fontFamily: "system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI','Hiragino Kaku Gothic ProN','Yu Gothic',sans-serif",
        color: "#0f172a",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 24, fontWeight: 950, margin: 0 }}>遊び方</h1>
        <a href="/" style={{ textDecoration: "none", border: "1px solid #cbd5e1", borderRadius: 999, padding: "7px 14px", color: "#111827", fontWeight: 800, fontSize: 13, background: "#fff" }}>← ゲームに戻る</a>
      </div>

      <p style={{ fontSize: 14, color: "#475569", lineHeight: 1.6, marginTop: 8 }}>
        言葉で陣地を奪い合う、空間戦略ワードゲームです。まずは Quick 5×5 で短く遊び、
        緑のマスに1文字を置き、文字をつないで単語を作ります。導入 5×5 は OPEN と包囲を学ぶ練習盤です。
      </p>

      <div style={coreCard}>
        <div style={{ fontWeight: 950, fontSize: 16, marginBottom: 6 }}>コアルール</div>
        <div style={{ fontSize: 13.5, color: "#0f172a", lineHeight: 1.65 }}>
          領地 ＝ 単語の経路 ＋ 囲んだ敵マス。強い手は、長い経路を作るか、敵を囲んで反転させる手です。
          役名は追加得点のためではなく、盤面で起きたことを理解しやすくするための名前です。
        </div>
      </div>

      <div style={card}>
        <div style={{ fontWeight: 950, fontSize: 16, marginBottom: 6 }}>基本の3ステップ</div>
        <Step n="1" title="文字を置く" body="緑のマスに1文字を置き、隣り合う文字をつないで単語を作ります。日本語版では2文字語も使えますが、効果は小さめです。" />
        <Step n="2" title="領地を取る" body="単語の経路が自分の領地になります。3文字以上、4文字以上になるほど盤面が大きく動きます。" />
        <Step n="3" title="囲む" body="相手の領地グループの周囲を塞ぐと、捕獲・反転に近づきます。" />
      </div>

      <div style={{ fontWeight: 950, fontSize: 16, margin: "16px 0 2px" }}>特殊な手</div>

      <Mech name="LOCK" body="囲った領地はロックされ、相手に奪われにくくなります。守りの拠点です。" />
      <Mech name="奪字" body="敵文字を含む単語を作ると、敵マスを1つ中立化できます。守りを崩す突破口です。" />
      <Mech name="2×2回転" body="1試合1回、2×2の文字だけを回転できます。所有権は動かず、文字配置だけが変わります。" />
      <Mech name="CUT / BRIDGE" body="CUTは相手の連結を分断、BRIDGEは自分の離れた領地を接続します。" />
      <Mech name="ENCIRCLE / SWING" body="包囲や大きな領地変動で、一手で流れが変わります。" />
      <Mech name="OPEN / Open Sides" body="領地グループの周囲に残る、まだ塞がれていない接点です。OP1は包囲寸前、OP2は圧迫、OP3はまだ余裕。単語で相手のOPENを減らすと、次の捕獲・囲みに近づきます。" />
      <Mech name="導入 5×5" body="OPEN と包囲を早く理解するための練習盤です。競技用の Quick 5×5 とは別で、短い手数で OP2→OP1→捕獲の流れを確認できます。" />

      <div style={card}>
        <div style={{ fontWeight: 900, fontSize: 14.5 }}>勝敗</div>
        <div style={{ fontSize: 13.5, color: "#475569", lineHeight: 1.6, marginTop: 4 }}>
          最後に陣地（マス）が多い方の勝ちです。先に打つ側がやや有利なため、後手には少しだけコミが付きます。
        </div>
      </div>

      <div style={{ textAlign: "center", marginTop: 22 }}>
        <a href="/" style={{ textDecoration: "none", border: "1px solid #7c3aed", borderRadius: 999, padding: "10px 18px", color: "#fff", background: "#7c3aed", fontWeight: 900, fontSize: 14 }}>ゲームを始める</a>
      </div>
    </div>
  );
}
