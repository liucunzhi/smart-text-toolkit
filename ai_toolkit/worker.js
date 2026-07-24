// Cloudflare Worker - AI Toolkit API Proxy
// Protects DeepSeek API key, handles CORS, rate limiting
// Deploy: npx wrangler deploy (set DEEPSEEK_API_KEY as secret)

const DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions';
const ALLOWED_ORIGIN = '*';
const RATE_LIMIT = 30; // requests per minute per IP

const rateLimitMap = new Map();

const TOOLS = {
  rewrite: {
    system: 'You are a professional content rewriter. Rewrite text to be more engaging and clear while preserving meaning. Output ONLY rewritten text.',
    prompt: (t, s) => `${s==='formal'?'Use formal language.':s==='casual'?'Use casual language.':s==='creative'?'Use creative language.':'Use clear natural language.'}\n\nRewrite:\n${t}`
  },
  summarize: {
    system: 'You are a text summarizer. Output ONLY the summary.',
    prompt: (t, l) => `${l==='short'?'1-2 sentences.':l==='medium'?'3-5 sentences.':'Detailed summary.'}\n\nSummarize:\n${t}`
  },
  grammar: {
    system: 'Fix all grammar, spelling, punctuation errors. Output ONLY corrected text.',
    prompt: (t) => `Fix errors:\n${t}`
  },
  seo: {
    system: 'Generate SEO meta tags. Output JSON: {"title":"...","description":"..."}',
    prompt: (t, kw) => `Generate SEO title (50-60 chars) and description (140-160 chars). Keyword: "${kw||'general'}".\n\nContent:\n${t}`
  }
};

async function callDeepSeek(tool, text, options, apiKey) {
  const cfg = TOOLS[tool];
  const r = await fetch(DEEPSEEK_API_URL, {
    method: 'POST',
    headers: {'Content-Type':'application/json','Authorization':`Bearer ${apiKey}`},
    body: JSON.stringify({model:'deepseek-chat',messages:[
      {role:'system',content:cfg.system},
      {role:'user',content:cfg.prompt(text, options?.style||options?.length||options?.keyword)}
    ],temperature:0.7,max_tokens:2048})
  });
  if (!r.ok) throw new Error(`DeepSeek error ${r.status}: ${await r.text()}`);
  return (await r.json()).choices[0].message.content;
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {headers:{
        'Access-Control-Allow-Origin':ALLOWED_ORIGIN,
        'Access-Control-Allow-Methods':'POST,OPTIONS',
        'Access-Control-Allow-Headers':'Content-Type',
        'Access-Control-Max-Age':'86400'
      }});
    }
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({error:'POST only'}),{status:405,
        headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':ALLOWED_ORIGIN}});
    }

    const ip = request.headers.get('CF-Connecting-IP')||'unknown';
    const now = Date.now();
    let ri = rateLimitMap.get(ip);
    if (!ri || now > ri.resetAt) { ri = {count:1, resetAt:now+60000}; rateLimitMap.set(ip,ri); }
    else { ri.count++; if (now > ri.resetAt+60000) rateLimitMap.delete(ip); }
    if (ri.count > RATE_LIMIT) {
      return new Response(JSON.stringify({error:'Rate limit. Retry in '+Math.ceil((ri.resetAt-now)/1000)+'s'}),{status:429,
        headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':ALLOWED_ORIGIN}});
    }

    try {
      const {tool, text, options} = await request.json();
      if (!tool||!text) throw new Error('Missing tool/text');
      if (!TOOLS[tool]) throw new Error(`Unknown tool: ${tool}`);
      if (text.length > 10000) throw new Error('Text too long (max 10000 chars)');
      const result = await callDeepSeek(tool, text, options, env.DEEPSEEK_API_KEY);
      return new Response(JSON.stringify({success:true,result}),{
        headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':ALLOWED_ORIGIN}});
    } catch(e) {
      return new Response(JSON.stringify({error:e.message}),{status:500,
        headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':ALLOWED_ORIGIN}});
    }
  }
};
