export function TopIndieHits() {
  return (
    <section className="mt-24">
      <div className="flex items-center gap-4 mb-12">
        <h2 className="font-headline text-4xl font-bold text-on-surface tracking-tight">Top Indie Hits</h2>
        <div className="h-[1px] flex-1 bg-gradient-to-r from-outline-variant/30 to-transparent"></div>
      </div>
      <div className="flex overflow-x-auto gap-8 pb-8 hide-scrollbar">
        {/* Carousel Items */}
        <div className="flex-none w-72 group">
          <div className="relative aspect-[3/4] rounded-xl overflow-hidden mb-4 bg-surface-container">
            <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBR4crGfKwxtUtm-Dmm1IAYsyFDCqbHY2kZ52WKiqHCCX85Lo4GqDGJsRKZuyN1sV1zQROHFSHaGRPd5-yzSomZDmnyV2xQCyqNp-wdSOIi7AGdzWta6ETpZJv51n5sHlI_aKflsGUAMBHOz8U0AjCvxznFBiIfgQvla4MpwHbZFeJY61Ek-tK_vppRXfFGN-rjO_xNGnHPpuY8n0rDQcYa8jI1TMDIVg48PVTbJiYKeeA8TJEsHnj3MdADSwO5DtcUyDMHGB2g3y7k" alt="Vanguard Pulse"/>
            <div className="absolute top-4 right-4 bg-primary-fixed-dim text-on-primary-fixed px-2 py-1 text-[10px] font-bold rounded uppercase">Hot</div>
          </div>
          <h4 className="font-bold text-on-surface group-hover:text-primary transition-colors">Vanguard Pulse</h4>
          <p className="text-xs text-on-surface-variant">Neon-Slasher • 2024</p>
        </div>
        <div className="flex-none w-72 group">
          <div className="relative aspect-[3/4] rounded-xl overflow-hidden mb-4 bg-surface-container">
            <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCIrY5w4FWLImjn11mAZf9JF1FjpNz9-Hm5u4UPyHZORpW0fuhsOdeMxIa_9UMN_M673Y7bmXNB40_JlMsAthtW9SRpvZURoeegd9zvJypizNn185dRd0-ixpZj3a6VWXvKpiAaPeFCWVGJmjFbYDPy67V3gZ8X5qt4ci83-0CZf38WjGe250h_m94kCp2cs4ZOXSb64q9F7Ni_L0rWVagqzhQfEDho0Nn20R9ShqujIteBHofyM_QRE-juZkoZfE5bu2FFAFGJIMNe" alt="Desert Stranding"/>
          </div>
          <h4 className="font-bold text-on-surface group-hover:text-primary transition-colors">Desert Stranding</h4>
          <p className="text-xs text-on-surface-variant">Atmospheric • 2023</p>
        </div>
        <div className="flex-none w-72 group">
          <div className="relative aspect-[3/4] rounded-xl overflow-hidden mb-4 bg-surface-container">
            <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAz4pcw4lDV9dGt9w0bccdcRqSnSKUu1LL5Z9_Zt9hE17h4ondbAhRagTNwPEayT5ZvHGcCOIGjnfRueAerkbmyh69v5lje6_kep3nURAVTlp1L14EstoX-n0JSlus1snS-7TYAQ7IGsi98MD6wlYcmVwh_SKQRtiALXEhPL-TapJFpDfHR58N1YdsaX7qlG33j2HaglO3eoz_FRoNjMxWuNC6hf5L6jwgO_QLHJfBNiPL_q6Be_nADiP7b0YcWJRF64IIHh_uRYsUF" alt="Rain Protocol"/>
          </div>
          <h4 className="font-bold text-on-surface group-hover:text-primary transition-colors">Rain Protocol</h4>
          <p className="text-xs text-on-surface-variant">Noir RPG • 2024</p>
        </div>
        <div className="flex-none w-72 group">
          <div className="relative aspect-[3/4] rounded-xl overflow-hidden mb-4 bg-surface-container">
            <img className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDRsRwwNn8Fw9EPNvU4IWrhQCIxn-sn1tQRmMNxHPFiIDwGYIqcuuVISAn_3K-WGirIOedC_7FaHjR-1ASj7RHxnbwEzgp5d38d2yAvpckS5PeLEH1WLhx217yuCBLMwptcoAWOir9iz707D2ccYD4EcDJpKwP_4XI3GuTdqjJ15m-AgFNUkUv4bF92XWDxou_d6ClrTsOxsx_Vh4LFwYdtLsXfd1VYKHQsYr88lbSRk1DtVVZxn5qZeo-mYZgv-Iql1E3oqXjSSosb" alt="Clockwork Soul"/>
            <div className="absolute top-4 right-4 bg-secondary text-on-secondary px-2 py-1 text-[10px] font-bold rounded uppercase">New</div>
          </div>
          <h4 className="font-bold text-on-surface group-hover:text-primary transition-colors">Clockwork Soul</h4>
          <p className="text-xs text-on-surface-variant">Steampunk • 2024</p>
        </div>
      </div>
    </section>
  );
}
