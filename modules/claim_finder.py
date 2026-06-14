from openai import OpenAI
import json
import re
import time


FALLBACK_MODELS = [
    "openai/gpt-3.5-turbo",  # More reliable than free models
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "mistralai/mistral-7b-instruct:free"
]

MAX_RETRIES = 2  


def extract_claims(text: str, api_key: str) -> list[dict]:

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=15.0,
        default_headers={
            "HTTP-Referer": "https://github.com/harshitgautam020703/Fact_Check",
            "X-Title": "GEO Fact-Check Agent",
        }
    )
    
    
    truncated_text = text[:8000]
    
    prompt = f"""You are a precise fact-extraction engine. Analyze the text below and extract every verifiable factual claim.

Focus on these types of claims:
- **Statistics & percentages** (e.g., "revenue grew by 40%")
- **Dates & timelines** (e.g., "founded in 2015")
- **Financial figures** (e.g., "$2.5 billion valuation")
- **Technical specifications** (e.g., "processes 10,000 requests per second")
- **Named entity facts** (e.g., "headquartered in San Francisco")
- **Comparative claims** (e.g., "fastest growing in the category")

Rules:
1. Extract ONLY factual, verifiable claims — not opinions or subjective statements.
2. Each claim should be self-contained and understandable without the surrounding text.
3. Be thorough — extract ALL verifiable claims you can find.
4. Return ONLY a valid JSON array with no additional text, markdown, or explanation.

Return format:
[
  {{"claim": "exact factual claim text", "type": "statistic|date|financial|technical|entity|comparative"}},
  ...
]

TEXT TO ANALYZE:
{truncated_text}"""

    first_error = None
    for model_name in FALLBACK_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Trying model: {model_name} (Attempt {attempt+1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.1,
                )                
                raw = response.choices[0].message.content
                json_match = re.search(r'\[.*\]', raw, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group()) 
                return json.loads(raw)
            except Exception as e:
                if first_error is None:
                    first_error = e
                error_str = str(e)
                
                if "free-models-per-day" in error_str or "credits" in error_str.lower():
                    raise Exception(f"Account limit reached: {error_str}")
                
            
                if "429" in error_str:
                    time.sleep(5 * (attempt + 1))
                    continue
               
                elif "404" in error_str or "endpoints" in error_str.lower():
                    break
                else:
                    break 
    
   
    raise Exception(f"All models failed. Primary error: {first_error}")
