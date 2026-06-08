import dynamic from "next/dynamic";

const WordTerritoryPage = dynamic(
  () => import("../components/WordTerritoryPageSource"),
  { ssr: false }
);

export default function Home() {
  return <WordTerritoryPage />;
}
