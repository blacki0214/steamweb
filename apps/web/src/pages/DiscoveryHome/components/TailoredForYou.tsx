export function TailoredForYou() {
  return (
    <section className="mt-24">
      <div className="flex items-end justify-between mb-12">
        <div>
          <h2 className="font-headline text-4xl font-bold text-on-surface tracking-tight mb-2">Tailored For You</h2>
          <p className="text-on-surface-variant">Personalized curation based on your recent activity.</p>
        </div>
        <a className="text-primary hover:underline font-bold text-sm tracking-widest uppercase" href="#">View Full Library</a>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Large Card */}
        <div className="md:col-span-8 group relative rounded-2xl overflow-hidden bg-surface-container-low border border-outline-variant/15 p-1">
          <div className="relative h-96 overflow-hidden rounded-xl">
            <img className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAwyV-YME36IrO50xo-ENkuk7HjwckT9T6SpC0vJsWhwmAT-ySG92eBd9DOGQTDeLYtHEJeTZcB4OGLAAmTl6DsbHzG5Hz7c0oyxG-FWFeAlM1G9gOU4821_Uo9oUZUQxF6gk3m9iGK4sxJFXJEkWxHb3oDen3taF5Jhcy-yaHXzp4gieDiUzHJ4h5XoOauu_xq7HRtsdI3ap0dkfN_gdUWu1W4oXpOjPGpxcvovZmNvp1FXstk29zB7d3iIyrvv3fLCNV_wvizhPk6" alt="Echoes of the Void"/>
            <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest/90 via-transparent to-transparent"></div>
            {/* Video Trigger Portal */}
            <button className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-secondary-container/80 backdrop-blur-sm rounded-full flex items-center justify-center text-secondary shadow-[0_0_20px_rgba(83,221,252,0.4)] active:scale-90 transition-all">
              <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
            </button>
          </div>
          <div className="p-8">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-2xl font-bold font-headline mb-2 text-on-surface">Echoes of the Void</h3>
                <p className="text-on-surface-variant max-w-md">An atmospheric journey through space-time anomalies.</p>
              </div>
              <div className="bg-surface-bright px-3 py-1 rounded-lg border border-outline-variant/15">
                <span className="text-primary font-bold">9.8</span>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <span className="px-3 py-1 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold">Sci-Fi</span>
              <span className="px-3 py-1 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold">Exploration</span>
            </div>
          </div>
        </div>
        {/* Small Card 1 */}
        <div className="md:col-span-4 group bg-surface-container-low border border-outline-variant/15 rounded-2xl p-1 flex flex-col">
          <div className="relative h-48 overflow-hidden rounded-xl">
            <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDEi6ntDODM4J7Fpos_4VqVU0EvU8jiPzkf6VyQo2_m9Jk24yL5Pl5TF4YHn9lnGwAWAzWZ0chWiz1u1AdLoZljQSEC09jTqbi25i9_ECT2L0Ijq2xPe-OQoqn28yLH3H1R1LkBBU7wwXjEyWMVGJvNJkg964KatxR3pgGgg99ySoyJLDqjB2lRwzRBjr7BdZ1uMPQ1kISH4p5J6Y4DxrC0mpBO-mdXrL3cr7zNTeZR8cRTmMtgMfWf1cbh1bRQkWZ_d70RC51BNt-d" alt="Data Breach"/>
            <button className="absolute inset-0 flex items-center justify-center bg-surface/40 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="px-4 py-2 bg-secondary text-on-secondary-container text-xs font-bold rounded-full">YouTube Preview</span>
            </button>
          </div>
          <div className="p-6 flex-1 flex flex-col justify-between">
            <div>
              <h3 className="text-lg font-bold font-headline mb-1 text-on-surface">Data Breach</h3>
              <p className="text-sm text-on-surface-variant">Hyper-fast cyberpunk platformer.</p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-secondary font-bold">$19.99</span>
              <span className="material-symbols-outlined text-outline hover:text-primary cursor-pointer">favorite</span>
            </div>
          </div>
        </div>
        {/* Small Card 2 */}
        <div className="md:col-span-4 group bg-surface-container-low border border-outline-variant/15 rounded-2xl p-1 flex flex-col">
          <div className="relative h-48 overflow-hidden rounded-xl">
            <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCxEUiqtWJq2vZexIZj6EV89MTZirRo2Dp64qNWTV3zeSYfqk1qBUQQCt3YPMG5ta5BIF3Ae9JSOhY20jB8emnb8ldE9cSAi0_ig4jdpfumsHJwYdxPvmNAOVQNmq_8JiYcNNkIctZj7Myc04hne5GiZAlV03eVOQ9AY2qVZ51lIAUHJhZOzKL5-Gqju2Eb4LOMjsDm5zlKEh6wGFGl82mo6RD5U7HAPueAhIK588VsE_NuxCihh3HbkOXldurPR7a8QD_gNlEFRdre" alt="Shadow Keep"/>
            <button className="absolute inset-0 flex items-center justify-center bg-surface/40 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="px-4 py-2 bg-secondary text-on-secondary-container text-xs font-bold rounded-full">YouTube Preview</span>
            </button>
          </div>
          <div className="p-6 flex-1 flex flex-col justify-between">
            <div>
              <h3 className="text-lg font-bold font-headline mb-1 text-on-surface">Shadow Keep</h3>
              <p className="text-sm text-on-surface-variant">Tactical turn-based horror.</p>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-secondary font-bold">$24.99</span>
              <span className="material-symbols-outlined text-outline hover:text-primary cursor-pointer">favorite</span>
            </div>
          </div>
        </div>
        {/* Asymmetric Spacer/Quote */}
        <div className="md:col-span-8 flex items-center justify-center bg-gradient-to-br from-[#192540] to-surface border border-outline-variant/15 rounded-2xl p-12 overflow-hidden relative">
          <div className="absolute -top-12 -right-12 w-64 h-64 bg-primary/10 blur-[100px] rounded-full"></div>
          <div className="relative z-10 text-center">
            <h4 className="font-headline text-2xl italic font-light text-primary/80 leading-relaxed">"The future of interactive storytelling isn't just in the graphics, but in the spaces between the frames."</h4>
            <p className="mt-4 text-xs tracking-widest uppercase text-on-surface-variant">— Editorial Note</p>
          </div>
        </div>
      </div>
    </section>
  );
}
