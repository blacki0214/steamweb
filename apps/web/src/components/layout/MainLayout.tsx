import { Outlet } from "react-router-dom";
import { TopNavBar } from "./TopNavBar";
import { SideNavBar } from "./SideNavBar";
import { Footer } from "./Footer";
import { MobileNavBar } from "./MobileNavBar";

export function MainLayout() {
  return (
    <>
      <TopNavBar />
      <div className="flex pt-20">
        <SideNavBar />
        <main className="flex-1 md:ml-64 min-h-screen px-4 md:px-12 pb-24">
          <Outlet />
          <Footer />
        </main>
      </div>
      <MobileNavBar />
    </>
  );
}
