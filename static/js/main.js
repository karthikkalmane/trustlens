// TrustLens – Main JS
const STEPS = ["Validating URL…","Fetching product page…","Extracting data…","Running NLP analysis…","Detecting review bots…","Computing risk score…","Generating AI explanation…"];

const form    = document.getElementById('analyzeForm');
const overlay = document.getElementById('loadingOverlay');
const stepEl  = document.getElementById('loadingStep');

if (form && overlay) {
  form.addEventListener('submit', () => {
    overlay.classList.add('active');
    let i = 0;
    setInterval(() => { if(i < STEPS.length && stepEl) stepEl.textContent = STEPS[i++]; }, 1600);
  });
}

// URL platform hint
const urlInput = document.getElementById('urlInput');
const urlHint  = document.getElementById('urlHint');
if (urlInput && urlHint) {
  const MAP = {
    'flipkart.com':'✓ Flipkart detected','amazon.in':'✓ Amazon detected',
    'amazon.com':'✓ Amazon detected','meesho.com':'✓ Meesho detected',
    'myntra.com':'✓ Myntra detected','snapdeal.com':'✓ Snapdeal detected',
    'ajio.com':'✓ Ajio detected','nykaa.com':'✓ Nykaa detected',
    'tatacliq.com':'✓ Tata CLiQ detected','firstcry.com':'✓ FirstCry detected',
    'pepperfry.com':'✓ Pepperfry detected','jiomart.com':'✓ JioMart detected',
    'indiamart.com':'✓ IndiaMART detected','tradeindia.com':'✓ TradeIndia detected',
  };
  urlInput.addEventListener('input', () => {
    const v = urlInput.value.toLowerCase();
    let found = false;
    for (const [key, label] of Object.entries(MAP)) {
      if (v.includes(key)) {
        urlHint.textContent = label; urlHint.style.color = '#22c55e'; found = true; break;
      }
    }
    if (!found && v.length > 8) {
      urlHint.textContent = '🌐 Generic URL — will analyze as website'; urlHint.style.color = '#f59e0b';
    } else if (!found) {
      urlHint.textContent = 'Supports 13+ platforms including any product website'; urlHint.style.color = '';
    }
  });
}

// Animate bars on page load
document.addEventListener('DOMContentLoaded', () => {
  ['indicator-bar','mf-bar','risk-mini-bar'].forEach(cls => {
    document.querySelectorAll('.'+cls).forEach((el, i) => {
      const tw = el.style.width; el.style.width = '0';
      setTimeout(() => { el.style.transition = 'width 0.9s ease'; el.style.width = tw; }, 150 + i*90);
    });
  });
});
