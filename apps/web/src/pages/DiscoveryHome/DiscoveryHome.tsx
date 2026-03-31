import { HeroSpotlight } from "./components/HeroSpotlight";
import { TailoredForYou } from "./components/TailoredForYou";
import { TopIndieHits } from "./components/TopIndieHits";
import { RecentGameplayGems } from "./components/RecentGameplayGems";

export function DiscoveryHome() {
  return (
    <>
      <HeroSpotlight />
      <TailoredForYou />
      <TopIndieHits />
      <RecentGameplayGems />
    </>
  );
}
