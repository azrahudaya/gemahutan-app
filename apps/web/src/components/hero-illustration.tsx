<svg width="600" height="400" viewBox="0 0 600 400" fill="none" xmlns="http://www.w3.org/2000/svg">
  {/* Background ambient glow */}
  <defs>
    <linearGradient id="waveGradient1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stopColor="#0033FF" stopOpacity="0.3" />
      <stop offset="50%" stopColor="#99FFE4" stopOpacity="0.2" />
      <stop offset="100%" stopColor="#0033FF" stopOpacity="0.3" />
    </linearGradient>
    <linearGradient id="waveGradient2" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stopColor="#99FFE4" stopOpacity="0.2" />
      <stop offset="50%" stopColor="#0033FF" stopOpacity="0.4" />
      <stop offset="100%" stopColor="#99FFE4" stopOpacity="0.2" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  {/* Left side - abstract forest silhouette */}
  <path d="M0 350 L50 300 L100 340 L150 280 L200 320 L250 260 L300 300 L350 250 L400 290 L450 240 L500 280 L550 230 L600 270 V400 H0 Z" 
    fill="#171717" opacity="0.5"/>
  
  {/* Right side - audio waveform visualization */}
  <path d="M350 200 C360 180, 370 220, 380 190 C390 160, 400 240, 410 170 C420 260, 430 150, 440 230 C450 140, 460 250, 470 160 C480 270, 490 130, 500 280" 
    stroke="url(#waveGradient1)" strokeWidth="3" fill="none" filter="url(#glow)" opacity="0.8"/>
  
  <path d="M360 200 C370 220, 380 180, 390 210 C400 190, 410 230, 420 180 C430 240, 440 170, 450 250 C460 160, 470 260, 480 190 C490 270, 500 180, 510 290" 
    stroke="url(#waveGradient2)" strokeWidth="2" fill="none" opacity="0.6"/>
  
  {/* Center - microphone/sound icon */}
  <circle cx="300" cy="200" r="60" stroke="#27272A" strokeWidth="2" fill="#101010"/>
  <circle cx="300" cy="200" r="40" stroke="#0033FF" strokeWidth="1.5" fill="none" opacity="0.7"/>
  <circle cx="300" cy="200" r="20" stroke="#99FFE4" strokeWidth="1" fill="none" opacity="0.5"/>
  
  {/* Decorative grid lines */}
  <line x1="50" y1="50" x2="550" y2="50" stroke="#171717" strokeWidth="1"/>
  <line x1="50" y1="100" x2="550" y2="100" stroke="#171717" strokeWidth="1"/>
  <line x1="50" y1="150" x2="550" y2="150" stroke="#171717" strokeWidth="1"/>
  <line x1="50" y1="200" x2="550" y2="200" stroke="#171717" strokeWidth="1"/>
  <line x1="50" y1="250" x2="550" y2="250" stroke="#171717" strokeWidth="1"/>
  <line x1="50" y1="300" x2="550" y2="300" stroke="#171717" strokeWidth="1"/>
  <line x1="50" y1="350" x2="550" y2="350" stroke="#171717" strokeWidth="1"/>
  
  {/* Left decorative lines */}
  <line x1="80" y1="80" x2="80" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="120" y1="80" x2="120" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="160" y1="80" x2="160" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="200" y1="80" x2="200" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="240" y1="80" x2="240" y2="320" stroke="#171717" strokeWidth="1"/>
  
  {/* Right decorative lines */}
  <line x1="320" y1="80" x2="320" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="360" y1="80" x2="360" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="400" y1="80" x2="400" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="440" y1="80" x2="440" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="480" y1="80" x2="480" y2="320" stroke="#171717" strokeWidth="1"/>
  <line x1="520" y1="80" x2="520" y2="320" stroke="#171717" strokeWidth="1"/>
</svg>