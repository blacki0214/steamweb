export function MobileNavBar() {
  return (
    <nav className="md:hidden fixed bottom-0 w-full h-16 bg-[#060e20]/90 backdrop-blur-lg border-t border-outline-variant/15 flex justify-around items-center z-50">
      <button className="flex flex-col items-center text-[#53ddfc]">
        <span className="material-symbols-outlined">explore</span>
        <span className="text-[10px] uppercase font-bold mt-1">Discovery</span>
      </button>
      <button className="flex flex-col items-center text-[#a3aac4]">
        <span className="material-symbols-outlined">person</span>
        <span className="text-[10px] uppercase font-bold mt-1">Profile</span>
      </button>
      <button className="flex flex-col items-center text-[#a3aac4]">
        <span className="material-symbols-outlined">settings</span>
        <span className="text-[10px] uppercase font-bold mt-1">Settings</span>
      </button>
    </nav>
  );
}
