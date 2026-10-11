import os
import re
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd

# 1. 갤럭시 모바일 브라우저 접속 환경 세팅
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; SM-S928N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 2. 타깃 모바일 URL 설정 (영화/엔터, 경제, 스포츠)
TARGET_CONFIG = {
    "영화/엔터": {
        "url": "https://m.entertain.naver.com/",
        "selectors": [".card_title", ".title", ".tit", "strong.tit_text"]
    },
    "비즈니스/경제": {
        "url": "https://m.news.naver.com/main?mode=LSD&sid1=101",
        "selectors": [".ranking_news_text .title", ".news_tit", ".cluster_text_headline"]
    },
    "스포츠": {
        "url": "https://m.sports.naver.com/",
        "selectors": [".tit_clip", ".news_list .title", ".main_feat_tit", ".home_news_tit"]
    }
}

# 3. 제외할 UI 시스템 문구 블랙리스트
BLACKLIST_KEYWORDS = [
    "추천 검색어", "자동완성", "동영상", "공식 채널", "네이버", 
    "더보기", "홈으로", "기사더보기", "전체보기", "재생시간"
]

def clean_title(raw_text: str) -> str:
    """언론사 말머리 및 특수 공백 제거"""
    if not raw_text:
        return ""
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", raw_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def is_valid_title(title: str) -> bool:
    """불필요한 UI 문구 필터링"""
    if len(title) < 10:
        return False
    for bad_word in BLACKLIST_KEYWORDS:
        if bad_word in title:
            return False
    return True

def save_with_deduplication(filepath: str, new_df: pd.DataFrame, subset_col: str = "제목") -> int:
    """기존 CSV가 있으면 불러와 합치고, 제목이 겹치면 중복을 제거해 영구 누적하는 함수"""
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            existing_df = pd.read_csv(filepath, encoding="utf-8-sig")
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            # 기존에 수집된 최초 일시를 보존하며 중복 행 제거
            combined_df = combined_df.drop_duplicates(subset=[subset_col], keep="first")
        except Exception:
            combined_df = new_df.drop_duplicates(subset=[subset_col], keep="first")
    else:
        combined_df = new_df.drop_duplicates(subset=[subset_col], keep="first")

    combined_df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return len(combined_df)

def crawl_curated_titles():
    collected_data = []
    
    # 깃허브 액션(서버 UTC)에서도 한국 표준시(KST)로 정확히 기록
    kst = timezone(timedelta(hours=9))
    now_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    for category, config in TARGET_CONFIG.items():
        print(f"[{category}] 수집 중...")
        try:
            res = requests.get(config["url"], headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            
            seen_in_batch = set()

            for selector in config["selectors"]:
                elements = soup.select(selector)
                for el in elements:
                    title = clean_title(el.get_text())
                    
                    if not is_valid_title(title) or title in seen_in_batch:
                        continue
                        
                    seen_in_batch.add(title)
                    char_count = len(title)
                    is_optimal = 22 <= char_count <= 30

                    collected_data.append({
                        "수집일시": now_str,
                        "카테고리": category,
                        "제목": title,
                        "글자수": char_count,
                        "22~30자_최적화": "O" if is_optimal else "X"
                    })
        except Exception as e:
            print(f"[{category}] 수집 중 오류: {e}")

    if not collected_data:
        print("수집된 데이터가 없습니다.")
        return

    new_df = pd.DataFrame(collected_data)
    new_optimal_df = new_df[new_df["22~30자_최적화"] == "O"]

    # 기존 CSV 파일과 결합하여 중복 제거 후 누적 저장
    total_all = save_with_deduplication("curated_titles_all.csv", new_df)
    total_opt = save_with_deduplication("curated_titles_optimal_22_30.csv", new_optimal_df)

    print("\n--- 수집 완료 ---")
    print(f"전체 파일(curated_titles_all.csv) 누적 건수: {total_all}개")
    print(f"22~30자 파일(curated_titles_optimal_22_30.csv) 누적 건수: {total_opt}개")

if __name__ == "__main__":
    crawl_curated_titles()
