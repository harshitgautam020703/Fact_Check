from openai import OpenAI
import json
import re
import time

FALLBACK_MODELS = [
    "openai/gpt-3.5-turbo",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "mistralai/mistral-7b-instruct:free"
]

MAX_RETRIES = 2


def get_verdict(claim: str, evidence: list[dict], client: OpenAI) -> dict:
    evidence_text = ""
    sources = []
    for i, e in enumerate(evidence[:4], 1):
        evidence_text += f"\n[Source {i}]: {e.get('title', 'Unknown')}\n{e.get('content', '')}\nURL: {e.get('url', '')}\n"
        if e.get('url'):
            sources.append(e['url'])
    
    prompt = f"""You are an expert fact-checker. Your job is to compare a claim against web evidence and determine its accuracy.

CLAIM: "{claim}"

WEB EVIDENCE:
{evidence_text}

Evaluate the claim and classify it as:
- **VERIFIED**: The claim is accurate and matches the web evidence.
- **INACCURATE**: The claim contains outdated information, wrong numbers, or partial errors. The core idea may be right but specific details are wrong.
- **FALSE**: No evidence supports the claim, or evidence directly contradicts it.

Also assess your confidence:
- **HIGH**: Multiple sources confirm your verdict.
- **MEDIUM**: Some evidence supports your verdict but it's not conclusive.
- **LOW**: Limited evidence available.

Return ONLY valid JSON with no markdown formatting, no code blocks, no additional text:
{{"verdict": "VERIFIED|INACCURATE|FALSE", "confidence": "HIGH|MEDIUM|LOW", "explanation": "One clear sentence explaining why", "correct_fact": "The accurate information if the claim is wrong, or null if verified"}}"""

    first_error = None
    for model_name in FALLBACK_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Verdict Engine: Trying model {model_name} (Attempt {attempt+1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.1,
                )
                
                raw = response.choices[0].message.content
                
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = json.loads(raw)
                
                result['sources'] = sources[:3]
                return result
            
            except Exception as e:
                if first_error is None:
                    first_error = e
                error_str = str(e)
                
                if "free-models-per-day" in error_str or "credits" in error_str.lower():
                    match = re.search(r"'message':\s*'([^']+)'", error_str)
                    clean_msg = match.group(1) if match else error_str
                    return {
                        "verdict": "ERROR",
                        "confidence": "LOW",
                        "explanation": f"API Error: {clean_msg}",
                        "correct_fact": None,
                        "sources": sources[:3]
                    }
                
                if "429" in error_str:
                    time.sleep(5 * (attempt + 1))
                    continue
                elif "404" in error_str or "endpoints" in error_str.lower():
                    break
                else:
                    break
    
    error_msg = str(first_error)
    match = re.search(r"'message':\s*'([^']+)'", error_msg)
    clean_msg = match.group(1) if match else error_msg
    
    return {
        "verdict": "ERROR",
        "confidence": "LOW",
        "explanation": f"API Error: {clean_msg}",
        "correct_fact": None,
        "sources": sources[:3]
    }
