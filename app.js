const bio = document.getElementById('bio');
const counter = document.getElementById('counter');
const roastBtn = document.getElementById('roastBtn');
const result = document.getElementById('result');
const notice = document.getElementById('notice');
let selectedType = 'Instagram';
let lastResult = null;

document.querySelectorAll('.type').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.type').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedType = btn.dataset.type;
}));

bio.addEventListener('input', () => { counter.textContent = `${bio.value.length} / 500`; });

const clamp = (n, a, b) => Math.max(a, Math.min(b, n));
const norm = s => s.toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, ' ').trim();
const has = (s, words) => words.some(w => s.includes(w));
const count = (s, re) => (s.match(re) || []).length;
const pick = (arr, seed) => arr[Math.abs(seed) % arr.length];
const hash = s => { let h = 2166136261; for (let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);} return h>>>0; };

function extract(text, type) {
  const s = norm(text);
  const tokens = s.split(/[^a-z0-9@+#&.-]+/).filter(Boolean);
  const emojis = (text.match(/[\u{1F300}-\u{1FAFF}]/gu) || []);
  const claims = {
    founder: has(s,['founder','co-founder','ceo','entrepreneur','startup','building']),
    hustle: has(s,['hustle','grind','grinding','success','winning','millionaire','ambitious','discipline']),
    creative: has(s,['designer','artist','creative','photographer','writer','creator','filmmaker','music','musician']),
    tech: has(s,['developer','engineer','coder','programmer','tech','ai','software','data']),
    student: has(s,['student','undergrad','bachelor','master','university','college']),
    travel: has(s,['travel','traveler','traveller','adventure','wanderlust','explore','nomad']),
    fitness: has(s,['gym','fitness','fit','workout','lifting','runner','running','athlete']),
    coffee: has(s,['coffee','chai','caffeine','espresso']),
    luxury: has(s,['luxury','rich','wealth','money','cars','rolex','designer','premium']),
    relationship: has(s,['love','lover','taken','single','wife','husband','boyfriend','girlfriend','soulmate']),
    spirituality: has(s,['god','blessed','faith','spiritual','karma','manifest','universe']),
    motivational: has(s,['dream','dreams','believe','positive','mindset','goals','level up','never give up','be yourself']),
    status: has(s,['official','public figure','influencer','celeb','celebrity','verified']),
    disclaimer: has(s,["don't judge","dont judge","not here to","no drama","don't care","dont care","haters","haters gonna"]),
    dm: has(s,['dm','dms','collab','collaboration','business inquiries','contact me']),
    location: /\b(in|from|based in|living in)\s+[a-z][a-z .'-]{2,30}/i.test(text),
    pronoun: /\b(i|i'm|im|my|me|we|our)\b/i.test(text),
  };
  const symbols = count(text, /[|•·]/g);
  const exclam = count(text, /!/g);
  const emojisN = emojis.length;
  const clicheCount = [claims.hustle, claims.motivational, claims.travel, claims.coffee, claims.spirituality, claims.fitness].filter(Boolean).length;
  const selfBrand = count(s, /\b(i am|i'm|im|my|official|ceo|founder|expert|professional|visionary|leader|creator)\b/g);
  const vague = count(s, /\b(the future|making history|changing the world|living my best life|good vibes|big things|watch this space|born to|made to|on a mission)\b/g);
  const compact = text.length < 55;
  const overloaded = text.length > 260 || symbols >= 5;
  return {s,tokens,emojis,claims,symbols,exclam,emojisN,clicheCount,selfBrand,vague,compact,overloaded,type,seed:hash(type+'|'+text)};
}

function targetProfile(x) {
  const c=x.claims;
  const candidates=[];
  const add=(key, weight, label, evidence, line)=>candidates.push({key,score:weight,label,evidence,line});
  if(c.founder) add('title',8+(c.hustle?3:0), 'the title', 'founder/CEO language', 'You put the job title in the bio like the company was supposed to arrive with it.');
  if(c.motivational && c.hustle) add('motivation',9+(x.vague*2), 'the motivational fog', 'hustle + motivational language', 'Your bio is less a personality and more a screensaver for people who discovered podcasts yesterday.');
  if(c.travel && c.coffee) add('starterpack',9, 'the starter pack', 'travel + coffee', 'You assembled the personality starter pack so perfectly it looks factory-installed.');
  if(c.travel && c.motivational) add('escape',8, 'the curated freedom', 'travel + motivational language', 'You describe freedom like it is a brand partnership, not a personality.');
  if(c.tech && c.student) add('resume',9, 'the résumé in disguise', 'student + technical title', 'This is a résumé fragment pretending it got invited to Instagram.');
  if(c.creative && c.creator) add('creator',8, 'creator branding', 'creative/creator language', 'You are branding the fact that you create things harder than you are showing what you create.');
  if(c.fitness && c.motivational) add('gym',9, 'gym philosophy', 'fitness + motivation', 'Your personality has been replaced by a protein tub with a quote printed on it.');
  if(c.luxury && c.status) add('status',10, 'status signaling', 'luxury + status language', 'You are not flexing a lifestyle; you are submitting evidence that you desperately want one noticed.');
  if(c.disclaimer) add('defensive',10, 'the defensive disclaimer', 'defensive bio language', 'The funniest thing here is that your bio is already defending you from criticism nobody had written yet.');
  if(c.dm && (c.founder||c.status||c.creator)) add('pitch',8, 'the sales pitch', 'DM/collab language', 'You turned a bio into a lead-generation form and still forgot to give anyone a reason to care.');
  if(x.emojisN>=4) add('emoji',7+x.emojisN, 'the emoji scaffolding', `${x.emojisN} emojis`, 'The emojis are carrying so much personality they deserve co-author credit.');
  if(x.vague>=1) add('vague',9+x.vague, 'the empty promise', 'generic future/mission language', 'You promised the future so vaguely even the future has no idea what you are talking about.');
  if(x.compact && x.selfBrand>=2) add('compressed',9, 'compressed ego', 'short bio with stacked self-labels', 'Six words, three titles, zero evidence. Efficient, if the goal was to advertise the ego.');
  if(x.overloaded) add('overload',8, 'the information dump', 'overstuffed bio', 'You did not write a bio; you emptied the entire Notes app into the profile field.');
  if(x.exclam>=3) add('energy',7, 'manufactured enthusiasm', `${x.exclam} exclamation marks`, 'Your punctuation is screaming because the bio itself is not convincing anyone.');
  if(c.spirituality && c.motivational) add('manifest',8, 'manifestation', 'spiritual + motivational language', 'You manifested so many good vibes you forgot to include a single concrete personality trait.');
  if(!candidates.length) add('generic',5, 'the missing angle', 'no dominant pattern', 'There is nothing obviously embarrassing here, which means the only thing left to roast is how aggressively normal you made yourself sound.');
  return candidates.sort((a,b)=>b.score-a.score)[0];
}

function precision(x,t) {
  const c=x.claims;
  const options=[];
  if(t.key==='title') options.push(
    'The title is doing the heavy lifting; the bio never cashes the credibility check.',
    'You introduced the position before introducing a reason anyone should believe it.',
    'The title sounds established. The rest of the bio sounds like it is waiting for the company to become real.'
  );
  if(t.key==='motivation') options.push(
    'Every phrase announces ambition; almost none gives evidence of it.',
    'You are selling the image of discipline instead of revealing anything uniquely you.',
    'The bio keeps saying “future” because the present apparently had nothing quotable.'
  );
  if(t.key==='starterpack') options.push(
    'Coffee + travel is not a personality anymore; it is the default character preset.',
    'Nothing here is wrong. That is exactly the problem: it is painfully interchangeable.',
    'You chose two of the internet’s safest personality traits and called it identity.'
  );
  if(t.key==='resume') options.push(
    'Your strongest descriptors are credentials, not character.',
    'A recruiter could parse this. A stranger could not remember it.',
    'You told people what you study and do, but not what makes you you.'
  );
  if(t.key==='defensive') options.push(
    'You are fighting an imaginary audience before anyone has even met you.',
    'The disclaimer reveals insecurity more clearly than the rest of the bio reveals confidence.',
    'Nothing says “unbothered” like pre-writing the argument with your haters.'
  );
  if(t.key==='pitch') options.push(
    'You made yourself sound available for business before making yourself interesting.',
    'The call-to-action arrived before the personality.',
    'You are asking for opportunities without giving the reader a memorable reason to offer one.'
  );
  if(t.key==='emoji') options.push(
    'The symbols are not decorating the personality; they are substituting for it.',
    'Remove the emojis and watch half the confidence disappear.',
    'The visual noise is louder than the actual identity.'
  );
  if(t.key==='vague') options.push(
    'The claims are huge and the details are microscopic.',
    'You keep describing what you will become because what you are is harder to market.',
    'It sounds ambitious until you ask the one question the bio avoids: “doing what, exactly?”'
  );
  if(t.key==='overload') options.push(
    'You are terrified that one personality trait will not be enough, so you brought twelve.',
    'The bio is trying to win the reader before the reader has finished the first line.',
    'More information made you less identifiable.'
  );
  if(t.key==='energy') options.push(
    'The punctuation is compensating for a lack of a sharp idea.',
    'You cannot manufacture charisma with punctuation.',
    'The exclamation marks are doing motivational speaking for you.'
  );
  if(t.key==='manifest') options.push(
    'You described the universe’s responsibilities in detail and your own in vibes.',
    'There is plenty of belief here and almost no evidence.',
    'The bio is spiritually confident and factually unemployed.'
  );
  if(t.key==='generic') options.push(
    'Nothing sticks because nothing risks being specific.',
    'You successfully avoided cringe by also avoiding identity.',
    'The bio is clean. So clean there is nothing to remember.'
  );
  return pick(options.length?options:['The bio gave away the target; the engine simply noticed it.'], x.seed>>4);
}

function killShot(x,t) {
  const c=x.claims;
  const type=x.type;
  const variants=[];
  if(t.key==='title') {
    variants.push(
      c.hustle ? 'You have more leadership vocabulary than leadership evidence.' : 'The title arrived before the personality did.',
      type==='LinkedIn' ? 'Your bio has the confidence of a Fortune 500 CEO and the evidence of a Canva template.' : 'You put “CEO” in the bio like the letters themselves were supposed to generate revenue.',
      'Your title is doing cardio trying to outrun the lack of a story.'
    );
  } else if(t.key==='motivation') {
    variants.push(
      'Your bio reads like a motivational quote got a LinkedIn account and never learned when to stop talking.',
      'You are not mysterious; you are just aggressively generic with better punctuation.',
      'You spent the whole bio proving you want success and forgot to mention what you are actually successful at.'
    );
  } else if(t.key==='starterpack') {
    variants.push(
      'Coffee, travel, adventure — congratulations on selecting the internet’s default personality preset.',
      'If “coffee + travel” is the personality, the Wi-Fi password has more character.',
      'You built a personality out of things everyone likes because apparently originality was on layover.'
    );
  } else if(t.key==='resume') {
    variants.push(
      'You wrote a résumé, removed the dates, and somehow thought Instagram would call it a personality.',
      'Your bio can explain what you do perfectly; shame it cannot explain why anyone should remember you.',
      'You have credentials. What you forgot to bring was a personality.'
    );
  } else if(t.key==='defensive') {
    variants.push(
      '“I don’t care what people think” is doing a suspicious amount of work for someone who wrote a bio about it.',
      'You built a pre-emptive defense against criticism and accidentally published the insecurity instead.',
      'The bio is not confident; it is confidence with a lawyer present.'
    );
  } else if(t.key==='pitch') {
    variants.push(
      'You turned your personality into a sales funnel and somehow still have no product.',
      'The bio says “DM for opportunities” before giving anyone an opportunity to care.',
      'You are networking so hard the personality has been placed on hold.'
    );
  } else if(t.key==='emoji') {
    variants.push(
      'Take away the emojis and your personality loses signal.',
      'Your emojis have a stronger personal brand than you do.',
      'This bio needs fewer emojis and one actual thought.'
    );
  } else if(t.key==='vague') {
    variants.push(
      'You wrote “changing the world” because “figuring out my own Tuesday” did not sound visionary enough.',
      'Your ambitions are IMAX; your actual details are a blank screen.',
      'You keep promising the future because the present apparently has no receipts.'
    );
  } else if(t.key==='overload') {
    variants.push(
      'You packed so much identity into one bio that somehow none of it survived.',
      'This is not a bio; it is a panic attack with bullet points.',
      'You are trying to be memorable by being everything, which is exactly why nothing sticks.'
    );
  } else if(t.key==='energy') {
    variants.push(
      'The exclamation marks are more convincing than the claims, and that is a terrible sign.',
      'You used punctuation to fake charisma. The punctuation is exhausted.',
      'Your bio is yelling because apparently the content did not have enough authority.'
    );
  } else if(t.key==='manifest') {
    variants.push(
      'You outsourced the entire five-year plan to the universe and called it a personality.',
      'You have absolute faith in destiny and suspiciously little detail about what you actually do.',
      'The universe has been tagged in your career plan more times than your own skill set.'
    );
  } else {
    variants.push(
      'You managed to make a bio so safe it has the personality of a terms-and-conditions checkbox.',
      'Nothing here is offensive, impressive, or memorable. That is almost an achievement.',
      'Your bio did not embarrass you; it simply forgot to introduce you.'
    );
  }
  // Platform-specific sharpening without turning the result into a paragraph.
  if(type==='Dating' && (c.relationship || c.travel || c.fitness)) variants.push(
    'You are not looking for someone special; you are looking for an audience for your personal-brand trailer.'
  );
  if(type==='LinkedIn' && (c.hustle || c.founder || c.motivational)) variants.push(
    'This bio has three promotions, two podcasts and zero measurable outcomes.'
  );
  if(type==='Portfolio' && (c.creative || c.tech)) variants.push(
    'The portfolio is supposed to prove the work. The bio is busy auditioning for it.'
  );
  return pick(variants, x.seed);
}

function reply(x,t,roast) {
  const r=[
    '“That sounded better in your head, didn’t it?”',
    '“Respectfully, your bio needs a bio.”',
    '“You had 500 characters and still chose a personality template.”',
    '“The confidence is impressive. The evidence is still buffering.”',
    '“I read the bio. The bio read like it was written by committee.”'
  ];
  if(x.claims.founder) r.push('“Founder of what? The gap between the title and the proof?”');
  if(x.claims.hustle && x.claims.motivational) r.push('“Your bio is one podcast away from becoming a personality.”');
  if(x.claims.travel && x.claims.coffee) r.push('“Ah yes, coffee and travel. The two things nobody else on Earth has discovered.”');
  if(x.claims.disclaimer) r.push('“Nobody attacked you. Why did you arrive with a rebuttal?”');
  return pick(r, x.seed>>7);
}

function redemption(x,t) {
  if(t.key==='title'||t.key==='resume') return 'Delete one title. Add one concrete thing you have actually built, solved, or obsessed over.';
  if(t.key==='motivation'||t.key==='vague') return 'Kill the slogans. Keep one specific fact nobody else could copy.';
  if(t.key==='starterpack') return 'Replace the universal interests with one weirdly specific preference.';
  if(t.key==='emoji'||t.key==='energy') return 'Use the space for a sentence that has meaning instead of volume.';
  if(t.key==='defensive') return 'Remove the disclaimer. Confidence does not need to pre-argue with strangers.';
  if(t.key==='pitch') return 'Lead with identity and proof; ask for the opportunity after you have earned curiosity.';
  if(t.key==='overload') return 'Choose one identity. Make it sharp. Let the rest live somewhere else.';
  return 'Be specific enough that another person could recognize you without seeing your username.';
}

function analyzeBio(text,type){
  const x=extract(text,type);
  const target=targetProfile(x);
  const roast=killShot(x,target);
  const score=clamp(4.0 + target.score*0.45 + x.clicheCount*0.25 + x.vague*0.35 + (x.overloaded?0.5:0) + (x.exclam>=3?0.25:0) - (target.key==='generic'?1.0:0), 2.1, 9.9);
  const fingerprint=[];
  if(x.claims.founder) fingerprint.push('TITLE');
  if(x.claims.motivational||x.claims.hustle) fingerprint.push('HUSTLE');
  if(x.claims.travel) fingerprint.push('TRAVEL');
  if(x.claims.coffee) fingerprint.push('CAFFEINE');
  if(x.claims.tech||x.claims.creative) fingerprint.push('CRAFT');
  if(x.claims.fitness) fingerprint.push('FITNESS');
  if(x.claims.disclaimer) fingerprint.push('DEFENSIVE');
  if(x.claims.dm) fingerprint.push('PITCH');
  if(!fingerprint.length) fingerprint.push('UNCLASSIFIED');
  return {score,roast,translation:precision(x,target),reply:reply(x,target,roast),redemption:redemption(x,target),target:target.label,evidence:target.evidence,fingerprint:fingerprint.slice(0,4),type};
}

function renderResult(d){
  lastResult=d;
  document.getElementById('score').textContent=d.score.toFixed(1);
  document.getElementById('shareScore').textContent=d.score.toFixed(1);
  document.getElementById('roast').textContent=d.roast;
  document.getElementById('translation').textContent=d.translation;
  document.getElementById('reply').textContent=d.reply;
  document.getElementById('redemption').textContent=d.redemption;
  document.getElementById('shareRoast').textContent=d.roast;
  document.getElementById('target').textContent=d.target.toUpperCase();
  document.getElementById('evidence').textContent=d.evidence.toUpperCase();
  document.getElementById('fingerprint').textContent=d.fingerprint.join(' / ');
  document.getElementById('shareType').textContent=d.type.toUpperCase();
  result.classList.remove('hidden');
  result.scrollIntoView({behavior:'smooth',block:'start'});
}

roastBtn.addEventListener('click',()=>{
  const text=bio.value.trim();
  if(!text){notice.textContent='GIVE ME THE BIO. I CANNOT OPERATE ON VIBES ALONE.';bio.focus();return;}
  notice.textContent=''; roastBtn.disabled=true; roastBtn.querySelector('span').textContent='CUTTING...';
  setTimeout(()=>{renderResult(analyzeBio(text,selectedType));roastBtn.disabled=false;roastBtn.querySelector('span').textContent='ROAST IT';},520);
});

document.getElementById('againBtn').addEventListener('click',()=>{
  result.classList.add('hidden'); bio.value=''; counter.textContent='0 / 500'; notice.textContent=''; window.scrollTo({top:0,behavior:'smooth'}); bio.focus();
});

document.getElementById('copyBtn').addEventListener('click',async()=>{
  if(!lastResult)return;
  const d=lastResult;
  const text=`ROAST MY BIO — ${d.score.toFixed(1)}/10 DAMAGE\n\n${d.roast}\n\nTHE CUT: ${d.translation}\n\nREPLY: ${d.reply}`;
  try{await navigator.clipboard.writeText(text);const b=document.getElementById('copyBtn');const old=b.textContent;b.textContent='COPIED ✓';setTimeout(()=>b.textContent=old,1500);}catch{alert(text);}
});

document.getElementById('downloadBtn').addEventListener('click',async()=>{
  if(!window.html2canvas){const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';document.head.appendChild(s);await new Promise((res,rej)=>{s.onload=res;s.onerror=rej;});}
  const canvas=await html2canvas(document.getElementById('shareCard'),{scale:2,backgroundColor:'#101010'});
  const a=document.createElement('a');a.download='gkt-roast-my-bio.png';a.href=canvas.toDataURL('image/png');a.click();
});
