const MODEL = "gemini-2.5-flash-lite";

export async function onRequestPost(context) {
  const origin = context.request.headers.get("Origin");
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Vary": "Origin"
  };

  if (origin && new URL(origin).origin !== new URL(context.request.url).origin) {
    return new Response(JSON.stringify({ error: "Origin not allowed." }), { status: 403, headers });
  }

  let body;
  try {
    body = await context.request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON." }), { status: 400, headers });
  }

  const bio = typeof body.bio === "string" ? body.bio.trim() : "";
  const type = typeof body.type === "string" ? body.type : "Other";

  if (!bio || bio.length > 500) {
    return new Response(JSON.stringify({ error: "Bio must contain 1–500 characters." }), { status: 400, headers });
  }

  const apiKey = context.env.GEMINI_API_KEY;
  if (!apiKey) {
    return new Response(JSON.stringify({ error: "GEMINI_API_KEY is not configured." }), { status: 500, headers });
  }

  const prompt = `You are the writing engine behind GKT/LAB 001, a playful internet product called "Roast My Bio".

Analyze this user's ${type} bio:
"""${bio}"""

Return ONLY valid JSON with exactly these keys:
{
  "score": number,
  "roast": "string",
  "translation": "string",
  "redemption": "string"
}

Rules:
- score must be a number from 1.0 to 9.9 with one decimal.
- roast: 1–2 sentences, witty and specific to the actual bio. Tease the writing, not protected traits or sensitive personal characteristics.
- translation: 1 sentence explaining what the bio implicitly communicates.
- redemption: 1–2 sentences rewriting the bio into something genuinely better while preserving its likely intent.
- Avoid generic AI phrases, corporate filler, cruelty, harassment, sexual content, protected-class jokes, or claims about the person that cannot be inferred from the text.
- Do not mention that you are an AI.
- Keep the humor sharp, internet-native, and concise.
- No markdown.
- JSON only.`;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${encodeURIComponent(apiKey)}`;

  let aiResponse;
  try {
    aiResponse = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.95,
          maxOutputTokens: 350,
          responseMimeType: "application/json"
        }
      })
    });
  } catch {
    return new Response(JSON.stringify({ error: "AI request failed." }), { status: 502, headers });
  }

  if (!aiResponse.ok) {
    return new Response(JSON.stringify({ error: "AI provider rejected the request." }), { status: 502, headers });
  }

  const raw = await aiResponse.json();
  const text = raw?.candidates?.[0]?.content?.parts?.map(p => p.text || "").join("").trim();

  if (!text) {
    return new Response(JSON.stringify({ error: "AI returned no result." }), { status: 502, headers });
  }

  let result;
  try {
    result = JSON.parse(text);
  } catch {
    return new Response(JSON.stringify({ error: "AI returned malformed JSON." }), { status: 502, headers });
  }

  const score = Number(result.score);
  if (
    !Number.isFinite(score) ||
    score < 1 ||
    score > 9.9 ||
    typeof result.roast !== "string" ||
    typeof result.translation !== "string" ||
    typeof result.redemption !== "string"
  ) {
    return new Response(JSON.stringify({ error: "AI returned invalid fields." }), { status: 502, headers });
  }

  return new Response(JSON.stringify({
    score: Math.round(score * 10) / 10,
    roast: result.roast.slice(0, 500),
    translation: result.translation.slice(0, 500),
    redemption: result.redemption.slice(0, 600)
  }), { status: 200, headers });
}
