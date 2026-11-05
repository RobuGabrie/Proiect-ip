/** Fundalul comun: lumină refractată, peste care stau suprafețele de sticlă. */
export function Ambient() {
  return (
    <div className="ambient" aria-hidden="true">
      <svg className="ambient-lines" viewBox="0 0 1440 1024" preserveAspectRatio="xMidYMid slice">
        <path d="M-40 720C240 560 420 860 760 700s480-420 760-300" />
        <path d="M-40 780C260 620 440 920 780 760s470-400 740-280" />
        <path d="M-40 850C280 700 470 980 810 830s450-380 710-250" />
        <path d="M980-40c-60 260 120 400 60 640s-260 300-220 460" />
      </svg>
      <svg width="0" height="0" style={{ position: "absolute" }} focusable="false">
        <filter id="liquid-glass" x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.008 0.012" numOctaves="2" seed="7" result="noise" />
          <feGaussianBlur in="noise" stdDeviation="2" result="soft" />
          <feDisplacementMap in="SourceGraphic" in2="soft" scale="46" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>
    </div>
  );
}
