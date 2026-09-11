const bio = document.getElementById("bio");
const counter = document.getElementById("counter");
const roastBtn = document.getElementById("roastBtn");
const result = document.getElementById("result");
const notice = document.getElementById("notice");

let selectedType = "Instagram";


/* -----------------------------
   TYPE SELECTOR
----------------------------- */

document.querySelectorAll(".type").forEach((button) => {

  button.addEventListener("click", () => {

    document.querySelectorAll(".type").forEach((b) => {
      b.classList.remove("active");
    });

    button.classList.add("active");

    selectedType = button.dataset.type;
  });

});


/* -----------------------------
   CHARACTER COUNTER
----------------------------- */

bio.addEventListener("input", () => {

  counter.textContent =
    `${bio.value.length} / 500`;

});


/* -----------------------------
   UTILITIES
----------------------------- */

function hash(text) {

  let h = 2166136261;

  for (let i = 0; i < text.length; i++) {

    h ^= text.charCodeAt(i);

    h +=
      (h << 1) +
      (h << 4) +
      (h << 7) +
      (h << 8) +
      (h << 24);

  }

  return Math.abs(h >>> 0);
}


function choose(array, seed) {

  return array[
    seed % array.length
  ];

}


function clamp(value, min, max) {

  return Math.max(
    min,
    Math.min(max, value)
  );

}


function capitalize(text) {

  return text.charAt(0).toUpperCase() +
    text.slice(1);

}


/* -----------------------------
   LOCAL ROAST ENGINE
----------------------------- */

function analyzeBio(text, type) {

  const lower = text.toLowerCase();

  const seed =
    hash(`${type}|${text}`);


  let score =
    2.5 +
    (seed % 61) / 10;


  let roast;


  const observations = [];


  /* ---- detect common bio crimes ---- */

  if (
    lower.includes("coffee") ||
    lower.includes("chai")
  ) {

    observations.push(
      choose([
        "You have officially outsourced your personality to caffeine.",
        "Coffee is doing a suspicious amount of work in this bio.",
        "Congratulations. You have joined the international union of people who drink coffee."
      ], seed)
    );

    score += .5;
  }


  if (
    lower.includes("dream") ||
    lower.includes("hustle") ||
    lower.includes("grind") ||
    lower.includes("success")
  ) {

    observations.push(
      choose([
        "There is enough hustle in here to qualify as a LinkedIn post.",
        "The motivational-poster department called. They want their vocabulary back.",
        "This bio has been through at least three motivational podcasts."
      ], seed + 3)
    );

    score += .7;
  }


  if (
    lower.includes("entrepreneur") ||
    lower.includes("founder") ||
    lower.includes("ceo")
  ) {

    observations.push(
      choose([
        "Calling yourself a founder before founding anything is certainly a strategy.",
        "The CEO title arrived significantly earlier than the company.",
        "Your bio has more executive energy than actual evidence."
      ], seed + 5)
    );

    score += .8;
  }


  if (
    lower.includes("love") &&
    (
      lower.includes("travel") ||
      lower.includes("adventure")
    )
  ) {

    observations.push(
      choose([
        "You have successfully assembled the default human starter pack.",
        "Travel, love and adventure. Somewhere a Pinterest board is smiling.",
        "This reads like the demo version of a personality."
      ], seed + 7)
    );

    score += .5;
  }


  if (
    lower.includes("student") ||
    lower.includes("engineer") ||
    lower.includes("developer") ||
    lower.includes("designer")
  ) {

    observations.push(
      choose([
        "Your profession is carrying approximately 74% of this bio.",
        "A job title entered the chat and never left.",
        "Technically a bio. Spiritually a résumé fragment."
      ], seed + 11)
    );

    score += .4;
  }


  if (
    text.includes("🔥") ||
    text.includes("✨") ||
    text.includes("💯") ||
    text.includes("🚀")
  ) {

    observations.push(
      choose([
        "The emojis are currently doing unpaid emotional labour.",
        "The emoji budget clearly exceeded the writing budget.",
        "At least the emojis are confident."
      ], seed + 13)
    );

    score += .5;
  }


  if (
    lower.includes("not here to") ||
    lower.includes("don't take") ||
    lower.includes("dont take")
  ) {

    observations.push(
      choose([
        "Nothing says confidence like beginning with a defensive disclaimer.",
        "Your bio is already arguing with an imaginary comment section.",
        "The disclaimer somehow became the personality."
      ], seed + 17)
    );

    score += .6;
  }


  if (text.length < 25) {

    observations.push(
      choose([
        "You gave us fewer words than a Wi-Fi password.",
        "Bold choice. Minimalism or simply nothing to say?",
        "This bio has the information density of an empty folder."
      ], seed + 19)
    );

    score += .8;

  } else if (text.length > 350) {

    observations.push(
      choose([
        "This stopped being a bio somewhere around paragraph three.",
        "Your bio has entered its extended director's cut.",
        "Nobody asked for the autobiography, but here we are."
      ], seed + 23)
    );

    score += .8;
  }


  if (
    (text.match(/[!]/g) || []).length >= 4
  ) {

    observations.push(
      choose([
        "The exclamation marks are fighting for their lives.",
        "Apparently every sentence needed its own emergency siren.",
        "Your punctuation has more enthusiasm than your actual bio."
      ], seed + 29)
    );

    score += .4;
  }


  /* ---- platform-specific observations ---- */

  if (type === "LinkedIn") {

    observations.push(
      choose([
        "This is one 'passionate visionary' away from becoming a LinkedIn carousel.",
        "Somewhere a recruiter just whispered: 'strong communication skills.'",
        "The corporate energy is measurable from orbit."
      ], seed + 31)
    );

    score += .4;
  }


  if (type === "Dating") {

    observations.push(
      choose([
        "You are trying very hard to seem effortless. The effort is showing.",
        "This sounds like someone who rehearsed being spontaneous.",
        "The bio says 'I'm chill' with the intensity of a hostage negotiator."
      ], seed + 37)
    );

    score += .5;
  }


  if (type === "Instagram") {

    observations.push(
      choose([
        "This bio is one carefully placed emoji away from becoming a brand strategy.",
        "Instagram has seen this exact sentence approximately four million times.",
        "The algorithm has probably met this personality already."
      ], seed + 41)
    );

  }


  if (type === "Portfolio") {

    observations.push(
      choose([
        "Your portfolio bio is trying to be a résumé wearing sunglasses.",
        "There is talent here. The bio just buried it under professional vocabulary.",
        "You probably have better work than this introduction suggests."
      ], seed + 43)
    );

  }


  /* ---- generic fallback ---- */

  if (observations.length === 0) {

    observations.push(
      choose([
        "This bio is surprisingly normal. Which is almost suspicious.",
        "Nothing catastrophic here. Just enough personality to avoid an investigation.",
        "You escaped the obvious clichés. Unfortunately, I still have standards.",
        "There is potential here. The bio just hasn't unlocked it yet."
      ], seed + 47)
    );

  }


  roast =
    observations
      .slice(0, 3)
      .join(" ");


  score =
    clamp(
      score,
      1.8,
      9.7
    );


  /* -----------------------------
     TRANSLATION
  ----------------------------- */

  let translation;

  if (text.length < 35) {

    translation =
      "You are communicating the bare minimum and trusting everyone else to fill in the blanks.";

  } else if (
    lower.includes("hustle") ||
    lower.includes("grind") ||
    lower.includes("success")
  ) {

    translation =
      "You want people to see ambition first, personality second.";

  } else if (
    lower.includes("travel") ||
    lower.includes("adventure")
  ) {

    translation =
      "You want to come across as spontaneous, interesting and slightly difficult to pin down.";

  } else if (
    lower.includes("engineer") ||
    lower.includes("developer") ||
    lower.includes("designer")
  ) {

    translation =
      "You are leading with what you do instead of giving people a reason to remember who you are.";

  } else {

    translation =
      "You are trying to compress an entire personality into a few lines, and the compression algorithm is struggling.";
  }


  /* -----------------------------
     REDEMPTION
  ----------------------------- */

  let redemption;


  if (type === "LinkedIn") {

    redemption =
      "Build around what you actually make, solve or care about. Replace generic ambition with one concrete thing that makes you memorable.";

  } else if (type === "Dating") {

    redemption =
      "Drop the résumé language. Keep one real detail, one weird detail and one thing someone could actually start a conversation about.";

  } else if (type === "Portfolio") {

    redemption =
      "Show the person behind the work. One specific interest or obsession will usually make a stronger introduction than five professional adjectives.";

  } else {

    redemption =
      "Keep the strongest idea, delete the clichés, and replace one generic claim with something oddly specific to you.";
  }


  return {
    score,
    roast,
    translation,
    redemption
  };

}


/* -----------------------------
   RENDER
----------------------------- */

function renderResult(data) {

  document.getElementById("score").textContent =
    data.score.toFixed(1);

  document.getElementById("shareScore").textContent =
    data.score.toFixed(1);

  document.getElementById("roast").textContent =
    data.roast;

  document.getElementById("translation").textContent =
    data.translation;

  document.getElementById("redemption").textContent =
    data.redemption;

  document.getElementById("shareRoast").textContent =
    data.roast;


  result.classList.remove("hidden");

  result.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });

}


/* -----------------------------
   ROAST BUTTON
----------------------------- */

roastBtn.addEventListener("click", () => {

  const text =
    bio.value.trim();


  if (!text) {

    notice.textContent =
      "YOU FORGOT THE BIO. WE NEED SOMETHING TO JUDGE.";

    bio.focus();

    return;
  }


  notice.textContent = "";

  roastBtn.disabled = true;

  roastBtn.querySelector("span").textContent =
    "ANALYSING...";


  setTimeout(() => {

    const resultData =
      analyzeBio(
        text,
        selectedType
      );

    renderResult(resultData);

    roastBtn.disabled = false;

    roastBtn.querySelector("span").textContent =
      "ROAST IT";

  }, 650);

});


/* -----------------------------
   ROAST ANOTHER
----------------------------- */

document.getElementById("againBtn")
  .addEventListener("click", () => {

    result.classList.add("hidden");

    bio.value = "";

    counter.textContent =
      "0 / 500";

    notice.textContent = "";

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });

    bio.focus();

  });


/* -----------------------------
   COPY
----------------------------- */

document.getElementById("copyBtn")
  .addEventListener("click", async () => {

    const score =
      document.getElementById("score").textContent;

    const roast =
      document.getElementById("roast").textContent;

    const translation =
      document.getElementById("translation").textContent;

    const redemption =
      document.getElementById("redemption").textContent;


    const text = `
ROAST MY BIO — ${score}/10 DAMAGE

${roast}

WHAT IT ACTUALLY SAYS:
${translation}

REDEMPTION:
${redemption}
`.trim();


    try {

      await navigator.clipboard.writeText(text);

      const button =
        document.getElementById("copyBtn");

      const old =
        button.textContent;

      button.textContent =
        "COPIED ✓";

      setTimeout(() => {
        button.textContent = old;
      }, 1500);

    } catch {

      alert(text);

    }

  });


/* -----------------------------
   DOWNLOAD CARD
----------------------------- */

document.getElementById("downloadBtn")
  .addEventListener("click", async () => {

    if (!window.html2canvas) {

      const script =
        document.createElement("script");

      script.src =
        "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";

      document.head.appendChild(script);

      await new Promise((resolve) => {
        script.onload = resolve;
      });

    }


    const card =
      document.getElementById("shareCard");


    const canvas =
      await html2canvas(card, {
        scale: 2,
        backgroundColor: "#101010"
      });


    const link =
      document.createElement("a");

    link.download =
      "gkt-roast-my-bio.png";

    link.href =
      canvas.toDataURL("image/png");

    link.click();

  });