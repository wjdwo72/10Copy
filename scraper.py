import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_product_info(target_url: str) -> str:
    """URL에서 상품 정보를 고도로 분석하여 추출하는 강화된 스크래핑 엔진"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 스텔스 모드 유사 설정 (User-Agent 및 뷰포트 설정)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        try:
            print(f"[스크래퍼] 대상 URL 접속 시도: {target_url}")
            # 1. 페이지 접속 (networkidle 대신 domcontentloaded 사용으로 타임아웃 방지)
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            
            # 페이지 안정화를 위한 짧은 대기
            await asyncio.sleep(2)

            # 페이지 제목 추출
            title = await page.title()
            print(f"[스크래퍼] 페이지 제목 확인: {title}")

            # 2. 스마트스토어 등 특정 패턴 대응 (스크롤 내리기 등)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1) # 동적 로딩 대기

            # 3. 텍스트 추출 로직 (방법 1: 선택자 기반)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 불필요한 태그 제거
            for tag in soup(['nav', 'footer', 'script', 'style', 'header', 'aside', 'iframe']):
                tag.decompose()
            
            text_blocks = []
            selectors = ['h1', 'h2', 'h3', 'p', 'li', '.product_detail', '#detail_content', '.desc_area']
            
            for selector in selectors:
                elements = soup.select(selector)
                for el in elements:
                    text = el.get_text().strip()
                    if len(text) > 5: # 너무 짧은 텍스트는 제외
                        text_blocks.append(text)
            
            # 4. 텍스트 추출 로직 (방법 2: 전체 텍스트 추출 보완)
            if not text_blocks:
                print("[스크래퍼] 선택자 방식 실패, 전체 텍스트 추출 시도...")
                innerText = await page.evaluate("() => document.body.innerText")
                text_blocks.append(innerText)

            cleaned_text = " ".join(text_blocks)
            cleaned_text = " ".join(cleaned_text.split()) # 중복 공백 제거
            
            # 텍스트가 너무 짧으면 실패로 간주
            if len(cleaned_text) < 100:
                 return "데이터 추출 실패: 본문 내용이 너무 부족합니다."

            print(f"[스크래퍼] 추출 완료 (총 {len(cleaned_text)}자)")
            return f"페이지 제목: {title}\n본문 데이터: {cleaned_text[:2000]}"
            
        except Exception as e:
            print(f"[스크래퍼] 치명적 오류 발생: {str(e)}")
            return f"데이터 스크래핑 실패: {str(e)}"
        finally:
            await browser.close()
