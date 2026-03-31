export function TopNavBar() {
  return (
    <nav className="fixed top-0 w-full z-50 bg-[#060e20]/80 backdrop-blur-xl flex justify-between items-center px-8 h-20 bg-gradient-to-b from-[#091328] to-transparent shadow-[0_4px_30px_rgba(186,158,255,0.06)] font-['Space_Grotesk'] tracking-tight">
      <div className="flex items-center gap-12">
        <span className="text-2xl font-bold tracking-tighter text-[#dee5ff]">Bruh</span>
        {/* Desktop Nav Links */}
        <div className="hidden md:flex items-center gap-8">
          <a className="text-[#53ddfc] border-b-2 border-[#53ddfc] pb-1 active:scale-95 duration-200" href="#">Discovery</a>
          <a className="text-[#a3aac4] hover:text-[#dee5ff] transition-colors active:scale-95 duration-200" href="#">My Profile</a>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {/* Search Bar */}
        <div className="relative hidden lg:block group">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none">search</span>
          <input className="bg-surface-container-lowest border-none rounded-xl pl-10 pr-4 py-2 w-64 focus:ring-2 focus:ring-secondary transition-all outline-none text-sm" placeholder="Search titles..." type="text"/>
        </div>
        <button className="p-2 hover:bg-[#ba9eff]/10 rounded-lg transition-all active:scale-95 duration-200">
          <span className="material-symbols-outlined text-[#ba9eff]">notifications</span>
        </button>
        <button className="p-2 hover:bg-[#ba9eff]/10 rounded-lg transition-all active:scale-95 duration-200">
          <span className="material-symbols-outlined text-[#ba9eff]">settings</span>
        </button>
        <div className="w-10 h-10 rounded-full overflow-hidden border border-outline-variant/30">
          <img alt="User profile avatar" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAkN6B26Cg9AHdC67Uwwy8wb7UTBOVIYSvCXRbSqx489auysNdFXOFmQUNgw8zxaTdbHK0yeZTkrdX1zUa6rL2NgPIwL_jQFqRRM7esyA4c6TWRXPQU6hN_dq3_KTcLMMs6EWC4-mwQ5DIl9CAEW5ZmrS1crlW8tBfgmdR1wmZMnHK-CZ58Mbj1oKKnvMWcBZ-Yma6wf6gNad7PqdJbGp6kcZVwzdolULf3npjQL2bGcgl1jN_bq6pSHYspcHxmbEoyGpwOfAYh0gu0"/>
        </div>
      </div>
    </nav>
  );
}
