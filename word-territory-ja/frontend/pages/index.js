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
