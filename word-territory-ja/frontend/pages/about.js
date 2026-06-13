import React from "react";

const steps = [
  ["1", "文字を置く", "緑のマスに1文字を置き、隣り合う文字をつないで単語を作ります。日本語版では2文字語も使えますが、効果は小さめです。"],
  ["2", "領地を取る", "単語の経路が自分の領地になります。3文字以上、4文字以上になるほど盤面が大きく動きます。"],
  ["3", "LOCK", "囲った領地はロックされ、相手に奪われにくくなります。守りの拠点です。"],
  ["4", "奪字", "敵文字を含む単語を作ると、敵マスを1つ中立化できます。守りを崩す突破口です。"],
  ["5", "2x2回転", "1試合1回、2x2の文字だけを回転できます。所有権は動かず、文字配置だけが変わります。"],
  ["6", "CUT / BRIDGE", "CUTは相手の連結を分断、BRIDGEは自分の離れた領地を接続します。"],
  ["7", "ENCIRCLE / SWING", "包囲や大きな領地変動で、一手で流れが変わります。"],
];

function DemoBoard() {
  const cells = [
    ["", "", "か", "", ""],
    ["", "み", "い", "ず", ""],
    ["そ", "ら", "奪", "ほ", "し"],
    ["", "は", "な", "し", ""],
    ["", "", "く", "", ""],
  ];

  const kinds = [
    ["", "", "blue", "", ""],
    ["", "red", "red", "blue", ""],
    ["red", "red", "purple", "blue", "blue"],
    ["", "red", "green", "blue", ""],
    ["", "", "orange", "", ""],
  ];

  const styleFor = (kind) => {
    const base = {
      width: 48,
      height: 48,
      borderRadius: 13,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontWeight: 950,
      fontSize: 23,
      border: "2px solid #e5e7eb",
      background: "#fff",
      color: "#0f172a",
      boxShadow: "inset 0 -2px 0 rgba(0,0,0,.06)",
    };
    if (kind === "red") return { ...base, background: "#fee2e2", borderColor: "#ef4444", color: "#7f1d1d" };
    if (kind === "blue") return { ...base, background: "#dbeafe", borderColor: "#3b82f6", color: "#1e3a8a" };
    if (kind === "green") return { ...base, background: "#dcfce7", borderColor: "#22c55e", color: "#14532d", boxShadow: "0 0 0 4px rgba(34,197,94,.25)" };
    if (kind === "purple") return { ...base, background: "#f3e8ff", borderColor: "#a855f7", color: "#581c87", boxShadow: "0 0 0 4px rgba(168,85,247,.25)" };
    if (kind === "orange") return { ...base, background: "#ffedd5", borderColor: "#fb923c", color: "#7c2d12", boxShadow: "0 0 0 4px rgba(251,146,60,.25)" };
    return base;
  };

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(5, 48px)",
      gap: 7,
      justifyContent: "center",
      margin: "18px auto",
    }}>
      {cells.flatMap((row, r) =>
        row.map((ch, c) => (
          <div key={`${r}-${c}`} style={styleFor(kinds[r][c])}>{ch}</div>
        ))
      )}
    </div>
  );
}

export default function About() {
  const card = {
    border: "1px solid #e2e8f0",
    background: "linear-gradient(180deg,#ffffff,#f8fafc)",
    borderRadius: 18,
    padding: "14px 16px",
    margin: "12px 0",
    boxShadow: "0 8px 24px rgba(15,23,42,.06)",
  };

  return (
    <main style={{
      maxWidth: 760,
      margin: "0 auto",
      padding: "22px 16px 56px",
      fontFamily: "system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI','Hiragino Kaku Gothic ProN','Yu Gothic',sans-serif",
      color: "#0f172a",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 1000, margin: 0 }}>遊び方</h1>
          <div style={{ fontSize: 13, color: "#64748b", fontWeight: 800, marginTop: 4 }}>
            役・効果・狙いが分かる How to Play
          </div>
        </div>
        <a href="/" style={{
          textDecoration: "none",
          border: "1px solid #cbd5e1",
          borderRadius: 999,
          padding: "8px 15px",
          fontWeight: 900,
          color: "#0f172a",
          background: "#fff",
        }}>ゲームへ戻る</a>
      </div>

      <section style={{
        marginTop: 18,
        padding: 18,
        borderRadius: 24,
        background: "linear-gradient(135deg,#0f172a,#312e81,#7c3aed)",
        color: "#fff",
        boxShadow: "0 20px 60px rgba(15,23,42,.25)",
      }}>
        <div style={{ fontSize: 13, fontWeight: 900, opacity: .85 }}>WORD TERRITORY</div>
        <div style={{ fontSize: 24, fontWeight: 1000, marginTop: 4 }}>
          単語で陣地を取るゲームです
        </div>
        <p style={{ fontSize: 15, lineHeight: 1.75, marginBottom: 0 }}>
          1文字を置き、単語を作り、領地を広げます。短い語は安全、長い語は強力。
          LOCK・奪字・回転・CUT・BRIDGEで盤面を動かします。
        </p>
      </section>

      <DemoBoard />

      <section style={{
        marginTop: 14,
        padding: 16,
        borderRadius: 20,
        background: "#ecfeff",
        border: "1px solid #06b6d4",
      }}>
        <div style={{ fontWeight: 1000, fontSize: 16, color: "#164e63" }}>
          コアルール
        </div>
        <div style={{ fontSize: 14.5, color: "#155e75", lineHeight: 1.75, marginTop: 4 }}>
          領地 ＝ 単語の経路 ＋ 囲んだ敵マス。強い手は、長い経路を作るか、敵を囲んで反転させる手です。
          役名は追加得点のためではなく、盤面で起きたことを理解しやすくするための名前です。
        </div>
      </section>


      <section>
        {steps.map(([n, title, body]) => (
          <div key={n} style={card}>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div style={{
                minWidth: 34,
                height: 34,
                borderRadius: 999,
                background: "#111827",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 1000,
              }}>{n}</div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 1000 }}>{title}</div>
                <div style={{ fontSize: 14.5, color: "#475569", lineHeight: 1.75, marginTop: 3 }}>{body}</div>
              </div>
            </div>
          </div>
        ))}
      </section>

      <section style={{ ...card, background: "#fef3c7", borderColor: "#f59e0b" }}>
        <div style={{ fontWeight: 1000, fontSize: 16 }}>コツ</div>
        <div style={{ fontSize: 14.5, color: "#78350f", lineHeight: 1.75, marginTop: 4 }}>
          2文字語だけで逃げ続けると盤面は大きく動きません。
          3文字以上の語、敵文字を含む語、離れた自陣をつなぐ語を探すと、役が出やすくなります。
        </div>
      </section>
    </main>
  );
}
