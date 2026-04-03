from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import datetime
import google.generativeai as genai
from scraper import scrape_product_info
from prompts import SYSTEM_PROMPT

app = FastAPI(title="텐카피 SaaS 엔진", version="2.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. 가상 데이터베이스 (실제 운영시 DB 연동)
# ==========================================
USER_DATA = {
    "test_user": {
        "email": "jeffrey@solopreneur.com",
        "coins": 99999, # 무한 코인!! 💰
        "daily_free": 99999, # 무한 무료!! 🚀
        "history": [], # 저장된 카피 히스토리
        "last_active": "2026-04-03"
    }
}

# ==========================================
# 2. API 및 모델 설정
# ==========================================
GEMINI_API_KEY = "AIzaSyArxRjHcU8sC-75I6UoD_6ng_DLY0kfqzU" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

class CopyRequest(BaseModel):
    url: str | None = None
    target_audience: str
    manual_description: str | None = None
    image_data: str | None = None # Base64
    user_id: str = "test_user"

# ==========================================
# 3. 라우팅 (페이지 및 API)
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """메인 대시보드 페이지"""
    with open(os.path.join(os.path.dirname(__file__), "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """로그인 및 회원가입 페이지"""
    with open(os.path.join(os.path.dirname(__file__), "login.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/payment", response_class=HTMLResponse)
async def payment_page():
    """결제 및 요금제 확인 페이지"""
    with open(os.path.join(os.path.dirname(__file__), "payment.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/history", response_class=HTMLResponse)
async def history_page():
    """저장된 카피 히스토리 페이지"""
    with open(os.path.join(os.path.dirname(__file__), "history.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/v1/history")
async def get_history(user_id: str = "test_user"):
    user = USER_DATA.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {"history": user["history"]}

@app.post("/api/v1/save-copy")
async def save_copy(data: dict, user_id: str = "test_user"):
    user = USER_DATA.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 중복 저장 방지 또는 스탬프 추가
    copy_entry = {
        "id": len(user["history"]) + 1,
        "angle": data.get("angle"),
        "hook": data.get("hook"),
        "body": data.get("body"),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    user["history"].insert(0, copy_entry) # 최신순 저장
    return {"status": "success", "message": "저장 완료!"}

@app.post("/api/v1/generate-copy")
async def generate_ad_copy(req: CopyRequest):
    user = USER_DATA.get(req.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # 과금 로직 체크
    if user["daily_free"] > 0:
        user["daily_free"] -= 1
    elif user["coins"] >= 10:
        user["coins"] -= 10
    else:
        raise HTTPException(status_code=402, detail="코인이 부족합니다. 충전 후 이용해 주세요!")

    # 데이터 수집 (URL, 수동 입력, 이미지)
    context_text = ""
    
    # 1. URL 스크래핑 (있는 경우만)
    if req.url:
        scraped_text = await scrape_product_info(req.url)
        if "실패" not in scraped_text:
            context_text += f"\n[URL에서 추출한 정보]\n{scraped_text}"
    
    # 2. 직접 입력 설명 추가
    if req.manual_description:
        context_text += f"\n[사용자가 직접 입력한 특징]\n{req.manual_description}"

    user_prompt = f"아래 제품 정보를 바탕으로 '{req.target_audience}'을 타겟으로 한 광고 카피 10개를 만들어줘.\n\n{context_text}"

    try:
        # 매번 다른 결과를 위해 타임스탬프 및 다양성 가이드 추가
        diversity_jitter = f"\n(참고: 현재 시각 {datetime.datetime.now().strftime('%H:%M:%S')} - 이전과 다른 새로운 앵글과 창의적인 톤으로 작성해줘)"
        prompt_parts = [f"{SYSTEM_PROMPT}\n\n[USER INPUT]\n{user_prompt}{diversity_jitter}"]
        
        if req.image_data:
            prompt_parts.append({
                "mime_type": "image/jpeg",
                "data": req.image_data
            })
            prompt_parts[0] += "\n\n(첨부된 이미지를 분석하여 디자인 요소와 제품 외관 정보를 카피에 반영해줘)"

        response = model.generate_content(
            prompt_parts,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.9, # 창의성 상향
                "top_p": 0.95,
                "top_k": 40
            }
        )
        
        raw_text = response.text.strip()
        # 마크다운 코드 블록 제거 로직 강화
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        try:
            parsed_data = json.loads(raw_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if match:
                parsed_data = json.loads(match.group())
            else:
                raise
        
        return {
            "status": "success",
            "coins_left": user["coins"],
            "free_left": user["daily_free"],
            "data": parsed_data
        }
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            # 쿼타 초과 시 사용자에게 친절하게 안내 (429 에러 코드 반환)
            raise HTTPException(status_code=429, detail="AI 엔진이 너무 열일해서 잠시 기절했습니다! 약 1분 뒤에 다시 버튼을 눌러주세요! 🫡☕️")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
