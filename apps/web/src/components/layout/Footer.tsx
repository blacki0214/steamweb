export function Footer() {
  return (
    <footer className="flex flex-col md:flex-row justify-between items-center px-12 py-16 w-full mt-24 border-t border-[#40485d]/15 bg-[#060e20] font-['Manrope'] text-xs uppercase tracking-widest">
      <div className="mb-8 md:mb-0">
        <span className="text-lg font-['Space_Grotesk'] text-[#dee5ff] block mb-2">Bruh</span>
        <p className="text-[#a3aac4] normal-case tracking-normal">© 2026 Bruh. All rights reserved.</p>
      </div>
      <div className="flex flex-wrap justify-center gap-8">
        <a className="text-[#a3aac4] hover:text-[#ba9eff] transition-colors" href="#">About</a>
        <a className="text-[#a3aac4] hover:text-[#ba9eff] transition-colors" href="#">Twitter</a>
        <a className="text-[#a3aac4] hover:text-[#ba9eff] transition-colors" href="#">Discord</a>
        <a className="text-[#a3aac4] hover:text-[#ba9eff] transition-colors" href="#">Support</a>
        <a className="text-[#a3aac4] hover:text-[#ba9eff] transition-colors" href="#">Privacy</a>
      </div>
    </footer>
  );
}
