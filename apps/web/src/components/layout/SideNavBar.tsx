export function SideNavBar() {
  return (
    <aside className="hidden md:flex flex-col h-[calc(100vh-80px)] w-64 border-r border-[#40485d]/15 bg-[#091328] font-['Manrope'] text-sm fixed left-0 overflow-y-auto pt-8 pb-8">
      <div className="px-6 mb-8">
        <h3 className="text-[#dee5ff] font-bold text-lg">Filters</h3>
        <p className="text-[#a3aac4] text-xs">Refine discovery</p>
      </div>
      <nav className="flex-1 space-y-1">
        <div className="px-6 py-3 flex items-center gap-3 bg-[#ba9eff]/10 text-[#ba9eff] font-bold border-r-4 border-[#ba9eff] cursor-pointer active:opacity-80 transition-transform hover:translate-x-1">
          <span className="material-symbols-outlined">sports_esports</span>
          <span>Action</span>
        </div>
        <div className="px-6 py-3 flex items-center gap-3 text-[#a3aac4] hover:bg-[#1f2b49] cursor-pointer active:opacity-80 transition-transform hover:translate-x-1">
          <span className="material-symbols-outlined">palette</span>
          <span>Indie</span>
        </div>
        <div className="px-6 py-3 flex items-center gap-3 text-[#a3aac4] hover:bg-[#1f2b49] cursor-pointer active:opacity-80 transition-transform hover:translate-x-1">
          <span className="material-symbols-outlined">auto_fix_high</span>
          <span>RPG</span>
        </div>
        <div className="px-6 py-3 flex items-center gap-3 text-[#a3aac4] hover:bg-[#1f2b49] cursor-pointer active:opacity-80 transition-transform hover:translate-x-1">
          <span className="material-symbols-outlined">grid_view</span>
          <span>Strategy</span>
        </div>
        <div className="px-6 py-3 flex items-center gap-3 text-[#a3aac4] hover:bg-[#1f2b49] cursor-pointer active:opacity-80 transition-transform hover:translate-x-1">
          <span className="material-symbols-outlined">explore</span>
          <span>Adventure</span>
        </div>
        <div className="px-6 py-3 flex items-center gap-3 text-[#a3aac4] hover:bg-[#1f2b49] cursor-pointer active:opacity-80 transition-transform hover:translate-x-1">
          <span className="material-symbols-outlined">dark_mode</span>
          <span>Horror</span>
        </div>
      </nav>
      <div className="mt-8 px-6 space-y-4">
        <div className="pt-4 border-t border-outline-variant/15">
          <div className="flex items-center gap-3 text-[#a3aac4] py-2">
            <span className="material-symbols-outlined">schedule</span>
            <span>Play Time</span>
          </div>
          <div className="flex items-center gap-3 text-[#a3aac4] py-2">
            <span className="material-symbols-outlined">star</span>
            <span>Steam Rating</span>
          </div>
        </div>
        <button className="w-full py-3 bg-gradient-to-r from-primary-dim to-primary text-on-primary-container font-bold rounded-xl active:scale-95 transition-all">
          Apply Filters
        </button>
      </div>
    </aside>
  );
}
