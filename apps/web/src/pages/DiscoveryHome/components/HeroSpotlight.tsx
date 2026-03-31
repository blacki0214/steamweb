export function HeroSpotlight() {
  return (
    <section className="mt-8 relative h-[600px] rounded-3xl overflow-hidden group">
      <div 
        className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 group-hover:scale-105" 
        style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDTco_h-uf5NYT2izqjvz33X2Rzm_ukIOCYOFYZjQmz5RqS6Pd13Q3rGeDAYt_16sMBisYaJsZ_EgJWWkxZUy4t5vPxYo4mO8jhisaUD_F3yn8uVSwIkzsC5XLYlwOPovPO9mOj_ikiE7RHT8GlGQCS2nMpkG24gOU1QvOjcS5YKuPo9kh36DvSwVjDuE_1xbmRAhTZJ_Fa32Mw3_1vFKtp3aIsZWGDRHGsyH2faXhvqobc_p_O1eOyRlMmE9mD99tP7mzytRxFk_gP')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/40 to-transparent"></div>
      <div className="absolute bottom-16 left-12 max-w-2xl">
        <span className="inline-block px-4 py-1 rounded-full bg-secondary-container text-secondary text-xs font-bold tracking-widest uppercase mb-4">Indie Spotlight</span>
        <h1 className="font-headline text-6xl md:text-7xl font-bold text-on-surface tracking-tighter leading-none mb-6">NEON REPRISAL</h1>
        <p className="text-on-surface-variant text-lg font-light leading-relaxed mb-8">Experience the critically acclaimed rogue-lite masterpiece where every cycle reshapes the narrative architecture of a dying digital god.</p>
        <div className="flex items-center gap-4">
          <button className="px-8 py-4 bg-gradient-to-br from-primary-dim to-primary text-on-primary-container font-bold rounded-xl flex items-center gap-2 hover:shadow-[0_0_30px_rgba(186,158,255,0.4)] transition-all active:scale-95">
            Discover More
          </button>
          <button className="px-8 py-4 bg-surface-variant/40 backdrop-blur-md border border-outline-variant/15 text-on-surface font-bold rounded-xl flex items-center gap-2 hover:bg-surface-variant/60 transition-all active:scale-95">
            <span className="material-symbols-outlined">play_circle</span>
            Watch Trailer
          </button>
        </div>
      </div>
      <div className="absolute bottom-16 right-12 hidden lg:flex flex-col gap-3">
        <div className="w-2 h-2 rounded-full bg-secondary"></div>
        <div className="w-2 h-2 rounded-full bg-white/20"></div>
        <div className="w-2 h-2 rounded-full bg-white/20"></div>
      </div>
    </section>
  );
}
