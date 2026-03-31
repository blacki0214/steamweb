export function RecentGameplayGems() {
  return (
    <section className="mt-24">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div className="order-2 lg:order-1">
          <span className="text-secondary font-bold tracking-[0.3em] uppercase text-xs mb-4 block">Recent Gameplay Gems</span>
          <h2 className="font-headline text-5xl font-bold text-on-surface leading-tight mb-8">Uncover the hidden masterpieces of the month.</h2>
          <div className="space-y-6">
            <div className="flex gap-6 p-4 rounded-2xl hover:bg-surface-bright transition-all cursor-pointer border border-transparent hover:border-outline-variant/15">
              <div className="w-24 h-24 rounded-xl overflow-hidden flex-none">
                <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAVTDI0EWgdjZWEVnWr-NdVOap_cDhlJRVYxEkJOcTU2wikri5D4GhjG3MUAOXpv4KxwBF6QqXvC61EV4lrPlxvfAQW7nCP1QLFdamsI_wspLdjYD2UnJvfPIsUIKc70EJzpW6HZkWKSpgAd7x1Fw5HfNeANl-Ws2LiREHwd7A7sKs4lh6r5AiiC_9VveAvjWjCA0pfAAsWRcTDrM1TVqZu20TDCZnDX4_aStdnNk5Iko5SO3iEngHY7hCeT1hTO-2BYBmzhUWb7ltJ" alt="Kernel Panix"/>
              </div>
              <div>
                <h4 className="text-lg font-bold text-on-surface">Kernel Panix</h4>
                <p className="text-sm text-on-surface-variant mt-1">A rhythm-based hacking simulator that defies gravity.</p>
                <div className="flex items-center gap-4 mt-2">
                  <span className="text-xs font-bold text-primary">Overwhelmingly Positive</span>
                  <span className="text-xs text-outline">12k Reviews</span>
                </div>
              </div>
            </div>
            <div className="flex gap-6 p-4 rounded-2xl hover:bg-surface-bright transition-all cursor-pointer border border-transparent hover:border-outline-variant/15">
              <div className="w-24 h-24 rounded-xl overflow-hidden flex-none">
                <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDXnY3XW2c-wm-xynyhPQMNGCGaitJEjGk9sL-KfjTJIsT9Rk5Wbstc2nC_jkkdYKehDa5qxpLwwd73XwxdHLqtTciB3P0k0TlBKdtBYAQ5dLjm9j327WTpIU_MCE8p0kFPfmEU33FfX9UDznqvhC49sXZ_sUxvgS8jE-EpvNxMMc_KNgAqJKcvhJy0i1U_0mrdQYw0bm8CrSkc4AjOZgruljnfVUDN2pBGw3LvavwTgeos9b7X5rDCkb42fLGb4ZN2HHPQRzoH_D2H" alt="Tower of Sunder"/>
              </div>
              <div>
                <h4 className="text-lg font-bold text-on-surface">Tower of Sunder</h4>
                <p className="text-sm text-on-surface-variant mt-1">Vertical climbing rogue-lite with procedural floors.</p>
                <div className="flex items-center gap-4 mt-2">
                  <span className="text-xs font-bold text-primary">Very Positive</span>
                  <span className="text-xs text-outline">8k Reviews</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="order-1 lg:order-2 relative">
          <div className="aspect-square bg-gradient-to-br from-primary/20 to-secondary/20 rounded-full blur-[120px] absolute -inset-10 opacity-30"></div>
          <div className="relative rounded-3xl overflow-hidden border border-outline-variant/15">
            <img className="w-full aspect-square object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAuHp2eDPedAX8xgUJUjHVOiyxiSRO5lRo2H9omL-JlGWl70p-ooJlX4J2pgJVd47pJOWf8VTa2soRpJzEgS4aWI3c-2TpF5J8AbYVRyOn_iQiWDogSYfU4kAlNUpEJkj6JoK3sakh5Lpjfvr3e7j9NhpPPUIN8EeZOh6gn9i6QYfOpKvV7UdSMVR-dIy4ZsnmKp6TENlOyqS4ka_YOg56yVhnUfOEWZnJk4AsEf-ixmAGCmZlcEpatPjtdwk6s1LCOt3-D1RQFwTO7" alt="Gallery Space"/>
            <div className="absolute inset-0 bg-surface/20 backdrop-blur-[2px]"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <button className="w-24 h-24 bg-surface-container-highest/60 backdrop-blur-xl rounded-full border border-white/10 flex items-center justify-center group hover:scale-110 transition-transform">
                <span className="material-symbols-outlined text-4xl text-on-surface">play_arrow</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
