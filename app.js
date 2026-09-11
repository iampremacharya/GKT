const bio = document.getElementById("bio");
const counter = document.getElementById("counter");
const roastBtn = document.getElementById("roastBtn");
const result = document.getElementById("result");
const notice = document.getElementById("notice");

let selectedType = "Instagram";

document.querySelectorAll(".type").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".type").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    selectedType = btn.dataset.type;
  });
});

bio.addEventListener("input", () => {
  counter.textContent = `${bio.value.length} / 500`;
});

function fallbackResult(text, type) {
  const pools = {
    Instagram: {
      roast: "You somehow managed to say absolutely nothing in a very confident font.",
      translation: "I want people to think I'm interesting, but I would prefer not to provide evidence.",
      redemption: "Making things, learning things, occasionally overthinking both."
    },
    LinkedIn: {
      roast: "You have successfully turned a human being into a corporate loading screen.",
      translation: "I would like recruiters to know I am ambitious without sounding desperate.",
      redemption: "Computer Engineering student turning ideas into prototypes, experiments, and useful digital tools."
    },
    Dating: {
      roast: "You are asking someone to be intrigued by a trailer with no movie.",
      translation: "I am fun, allegedly. Please conduct your own investigation.",
      redemption: "Curious, slightly chaotic, and always ready for a good conversation."
    },
    Portfolio: {
      roast: "You have skills. You have ambitions. Apparently, you don't have nouns.",
      translation: "I want you to discover my work instead of me explaining why it matters.",
      redemption: "I build technical projects at the intersection of engineering, computing, and curiosity."
    },
    Other: {
      roast: "This bio has entered the chat, looked around, and refused to explain itself.",
      translation: "I would like to appear interesting while maintaining plausible deniability.",
      redemption: "Still figuring things out. Making things along the way."
    }
  };
  const vague = (text.match(/passion|dream|hustle|entrepreneur|love|living|journey|future|success/gi) || []).length;
  const emojis = (text.match(/[\u{1F300}-\u{1FAFF}]/gu) || []).length;
  const score = Math.min(9.9, Math.max(2.1, 4.2 + vague * .6 + emojis * .2 + (text.length < 30 ? 1 : 0)));
  return { ...pools[type], score: Math.round(score * 10) / 10 };
}

async function generateRoast() {
  const text = bio.value.trim();
  if (!text) {
    bio.focus();
    notice.textContent = "YOU FORGOT THE BIO. WE NEED SOMETHING TO JUDGE.";
    return;
  }

  roastBtn.disabled = true;
  notice.textContent = "";
  roastBtn.querySelector("span").textContent = "ANALYSING...";

  try {
    const response = await fetch("/api/roast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bio: text, type: selectedType })
    });

    if (!response.ok) throw new Error("AI endpoint unavailable");
    const data = await response.json();
    if (!data.roast || !data.translation || !data.redemption || typeof data.score !== "number") {
      throw new Error("Invalid AI response");
    }
    renderResult(data);
  } catch (error) {
    console.warn(error);
    renderResult(fallbackResult(text, selectedType));
    notice.textContent = "AI IS OFFLINE — LOCAL ROAST ENGINE ACTIVATED.";
  } finally {
    roastBtn.disabled = false;
    roastBtn.querySelector("span").textContent = "ROAST IT";
  }
}

function renderResult(data) {
  document.getElementById("score").textContent = Number(data.score).toFixed(1);
  document.getElementById("shareScore").textContent = Number(data.score).toFixed(1);
  document.getElementById("roast").textContent = data.roast;
  document.getElementById("translation").textContent = data.translation;
  document.getElementById("redemption").textContent = data.redemption;
  document.getElementById("shareRoast").textContent = data.roast;
  result.classList.remove("hidden");
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

roastBtn.addEventListener("click", generateRoast);

document.getElementById("againBtn").addEventListener("click", () => {
  result.classList.add("hidden");
  notice.textContent = "";
  bio.value = "";
  counter.textContent = "0 / 500";
  bio.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

document.getElementById("copyBtn").addEventListener("click", async () => {
  const text = `ROAST MY BIO — ${document.getElementById("score").textContent}/10 DAMAGE

${document.getElementById("roast").textContent}

WHAT IT ACTUALLY SAYS:
${document.getElementById("translation").textContent}

REDEMPTION:
${document.getElementById("redemption").textContent}`;
  try {
    await navigator.clipboard.writeText(text);
    const btn = document.getElementById("copyBtn");
    const old = btn.textContent;
    btn.textContent = "COPIED ✓";
    setTimeout(() => btn.textContent = old, 1400);
  } catch { alert(text); }
});

document.getElementById("downloadBtn").addEventListener("click", async () => {
  const card = document.getElementById("shareCard");
  if (!window.html2canvas) {
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
    document.head.appendChild(script);
    await new Promise(resolve => script.onload = resolve);
  }
  const canvas = await html2canvas(card, { scale: 2, backgroundColor: "#111111" });
  const link = document.createElement("a");
  link.download = "gkt-roast-my-bio.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
});
