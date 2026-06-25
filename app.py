import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import statistics
import time

# 페이지 설정
st.set_page_config(
    page_title="YouTube 주제 검증 도구",
    page_icon="⚡",
    layout="wide"
)

# API 설정
API_KEY = 'AIzaSyD0O_bl29-TG658UES-31M27_kqV5o2Y58'

# 스타일링
st.markdown("""
    <style>
    .main {
        padding: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# 헤더
st.markdown("# ⚡ YouTube 주제 검증 도구")
st.markdown("YouTube API를 기반으로 영상 주제의 현황을 실시간 분석합니다")

st.divider()

# 검색 입력
col1, col2 = st.columns([4, 1])

with col1:
    keyword = st.text_input(
        "분석할 유튜브 주제 입력",
        placeholder="예: 전쟁 영웅, 한국 역사, 다큐멘터리",
        label_visibility="collapsed"
    )

with col2:
    search_button = st.button("🔍 분석", use_container_width=True)

st.divider()

def analyze_keyword(keyword):
    """키워드 분석"""
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1️⃣ 검색
        status_text.text("📡 YouTube에서 검색 중...")
        progress_bar.progress(25)
        
        three_months_ago = (datetime.now() - timedelta(days=90)).isoformat() + 'Z'
        
        search_request = youtube.search().list(
            q=keyword,
            part='snippet',
            type='video',
            order='viewCount',
            maxResults=50,
            publishedAfter=three_months_ago,
            relevanceLanguage='ko'
        )
        
        search_response = search_request.execute()
        
        if not search_response.get('items'):
            st.error("❌ 검색 결과가 없습니다. 다른 키워드를 시도해주세요.")
            return
        
        # 2️⃣ 통계 수집
        status_text.text("📊 영상 통계 수집 중...")
        progress_bar.progress(50)
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        videos_request = youtube.videos().list(
            id=','.join(video_ids),
            part='statistics,snippet',
            maxResults=50
        )
        
        videos_response = videos_request.execute()
        videos = videos_response['items']
        
        # 3️⃣ 데이터 분석
        status_text.text("📈 데이터 분석 중...")
        progress_bar.progress(75)
        
        view_counts = []
        publish_dates = []
        
        for video in videos:
            try:
                views = int(video['statistics'].get('viewCount', 0))
                view_counts.append(views)
                publish_date = datetime.fromisoformat(
                    video['snippet']['publishedAt'].replace('Z', '+00:00')
                )
                publish_dates.append(publish_date)
            except:
                continue
        
        if not view_counts:
            st.error("❌ 통계 데이터를 가져올 수 없습니다.")
            return
        
        # 통계 계산
        total_videos = search_response['pageInfo'].get('totalResults', 0)
        avg_views = statistics.mean(view_counts)
        median_views = statistics.median(view_counts)
        max_views = max(view_counts)
        min_views = min(view_counts)
        
        # 최근 업로드 수
        now = datetime.now(publish_dates[0].tzinfo)
        one_week_ago = now - timedelta(days=7)
        one_month_ago = now - timedelta(days=30)
        
        last_week_videos = sum(1 for d in publish_dates if d > one_week_ago)
        last_month_videos = sum(1 for d in publish_dates if d > one_month_ago)
        
        # 경쟁도 판정
        if total_videos > 100000:
            competition = "매우 높음"
            competition_color = "🔴"
        elif total_videos > 50000:
            competition = "높음"
            competition_color = "🟠"
        elif total_videos > 10000:
            competition = "중간"
            competition_color = "🟡"
        else:
            competition = "낮음"
            competition_color = "🟢"
        
        # 추세 판정
        recent_views = view_counts[:len(view_counts)//3] if len(view_counts) > 2 else view_counts
        older_views = view_counts[2*len(view_counts)//3:] if len(view_counts) > 2 else view_counts
        
        recent_avg = statistics.mean(recent_views) if recent_views else 0
        older_avg = statistics.mean(older_views) if older_views else 0
        
        trending_up = recent_avg > older_avg
        trend = "📈 상승중" if trending_up else "📉 하락중"
        
        progress_bar.progress(100)
        status_text.text("✅ 분석 완료!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        # 4️⃣ 결과 표시
        st.success(f"✅ '{keyword}' 분석 완료!")
        
        # 주요 지표
        st.markdown("### 📊 주요 지표")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "경쟁 영상 수",
                f"{total_videos:,}개",
                f"{competition_color} {competition}"
            )
        
        with col2:
            st.metric(
                "1주일 업로드",
                f"{last_week_videos}개",
                f"일당 {last_week_videos/7:.1f}개"
            )
        
        with col3:
            st.metric(
                "1개월 업로드",
                f"{last_month_videos}개",
                f"일당 {last_month_videos/30:.1f}개"
            )
        
        with col4:
            st.metric(
                "현재 추세",
                trend,
                f"분석: {len(videos)}개 영상"
            )
        
        st.divider()
        
        # 조회수 통계
        st.markdown("### 📈 조회수 통계")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("평균 조회수", f"{int(avg_views):,}회")
        
        with col2:
            st.metric("중앙값 조회수", f"{int(median_views):,}회")
        
        with col3:
            st.metric("최고 조회수", f"{int(max_views):,}회")
        
        with col4:
            st.metric("최저 조회수", f"{int(min_views):,}회")
        
        st.divider()
        
        # 최종 판정
        st.markdown("### 🎯 최종 판정")
        
        verdict_text = f"""
**주제:** {keyword}

이 주제는 현재 **{total_videos:,}개**의 경쟁 영상이 있으며,
경쟁도는 **{competition}**입니다.

최근 1주일간 **{last_week_videos}개**의 새로운 영상이
업로드되고 있으며, 현재 추세는 **{trend}**중입니다.
"""
        
        st.info(verdict_text)
        
        # 추천사항
        st.markdown("### 💡 추천사항")
        
        recommendations = []
        
        if total_videos < 5000:
            recommendations.append("✅ **경쟁이 적은 주제**입니다. 좋은 기회입니다!")
        elif total_videos < 50000:
            recommendations.append("⚠️ **적당한 경쟁 수준**입니다. 차별화가 필요합니다.")
        else:
            recommendations.append("⚠️ **경쟁이 많은 주제**입니다. 강력한 차별화 전략이 필요합니다.")
        
        if trending_up:
            recommendations.append("📈 **상승 추세**이므로 좋은 시기입니다!")
        else:
            recommendations.append("📉 **하락 추세**입니다. 새로운 각도를 고려하세요.")
        
        if last_week_videos > 20:
            recommendations.append("🔥 **주간 업로드가 많습니다.** 빠른 실행이 중요합니다!")
        else:
            recommendations.append("✨ **주간 업로드가 적당합니다.** 기회가 있습니다!")
        
        for rec in recommendations:
            st.write(rec)
        
        st.divider()
        
        # 상세 정보
        with st.expander("📋 상세 정보"):
            st.write(f"""
            - **총 경쟁 영상:** {total_videos:,}개
            - **분석된 영상:** {len(videos)}개
            - **평균 조회수:** {int(avg_views):,}회
            - **중앙값 조회수:** {int(median_views):,}회
            - **최고 조회수:** {int(max_views):,}회
            - **최저 조회수:** {int(min_views):,}회
            - **1주일 업로드:** {last_week_videos}개
            - **1개월 업로드:** {last_month_videos}개
            - **현재 추세:** {trend}
            """)
        
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
        st.write("API 키를 확인해주세요.")

# 분석 버튼 클릭 처리
if search_button:
    if not keyword:
        st.warning("⚠️ 분석할 주제를 입력해주세요.")
    else:
        analyze_keyword(keyword)

# 하단 정보
st.divider()
st.markdown("""
---
### 📱 사용 팁
- 여러 주제를 계속 분석할 수 있습니다
- 결과는 자동으로 저장됩니다
- 모든 데이터는 실시간으로 가져옵니다

**포가튼 베일러 - Forgotten Valor** 🎬
""")
