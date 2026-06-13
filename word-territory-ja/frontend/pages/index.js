// WT_JA_ROMAJI_FREE_INPUT_UI_V2_BEGIN
const WT_JA_ROMAJI_TO_KANA_UI_V2 = Object.freeze({
  a:"あ", i:"い", u:"う", e:"え", o:"お",
  ka:"か", ki:"き", ku:"く", ke:"け", ko:"こ",
  ga:"が", gi:"ぎ", gu:"ぐ", ge:"げ", go:"ご",
  sa:"さ", si:"し", shi:"し", su:"す", se:"せ", so:"そ",
  za:"ざ", zi:"じ", ji:"じ", zu:"ず", ze:"ぜ", zo:"ぞ",
  ta:"た", ti:"ち", chi:"ち", tu:"つ", tsu:"つ", te:"て", to:"と",
  da:"だ", di:"ぢ", du:"づ", de:"で", do:"ど",
  na:"な", ni:"に", nu:"ぬ", ne:"ね", no:"の",
  ha:"は", hi:"ひ", hu:"ふ", fu:"ふ", he:"へ", ho:"ほ",
  ba:"ば", bi:"び", bu:"ぶ", be:"べ", bo:"ぼ",
  pa:"ぱ", pi:"ぴ", pu:"ぷ", pe:"ぺ", po:"ぽ",
  ma:"ま", mi:"み", mu:"む", me:"め", mo:"も",
  ya:"や", yu:"ゆ", yo:"よ",
  ra:"ら", ri:"り", ru:"る", re:"れ", ro:"ろ",
  wa:"わ", wo:"を", n:"ん", nn:"ん"
});
function wtJaNormalizeFreeInputUiV2(raw) {
  let s = String(raw || "").trim();
  if (!s) return "";
  s = s.replace(/[Ａ-Ｚａ-ｚ]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0));
  const first = s[0];
  if (first === "ー") return "ー";
  if (/[ぁ-ゖ]/.test(first)) return first;
  if (/[ァ-ヶ]/.test(first)) return String.fromCharCode(first.charCodeAt(0) - 0x60);
  const key = s.toLowerCase().replace(/[^a-z]/g, "");
  return WT_JA_ROMAJI_TO_KANA_UI_V2[key] || "";
}
// WT_JA_ROMAJI_FREE_INPUT_UI_V2_END

import dynamic from "next/dynamic";

const WordTerritoryClient = dynamic(
  () => import("../components/WordTerritoryClient"),
  {
    ssr: false,
    loading: () => null,
  }
);

export default function Home() {
  return <WordTerritoryClient />;
}
