import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import statistics
import time
from textblob import TextBlob
from langdetect import detect, LangDetectException
from collections import Counter

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
    </style>
    """, unsafe_allow_html=True)

# 헤더
st.markdown("# ⚡ YouTube 주제 검증 도구")
st.markdown("YouTube API를 기반으로 영상 주제와 댓글을 실시간 분석합니다")

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

def analyze_sentiment(text):
    """감정 분석 (한글/영어 혼합)"""
    positive_words = ['좋아', '최고', '훌륭', '멋져', '감동', '추천', '짱', '대박', '완벽', '좋다', '아름다', '놀라워', '신기해', '대단', '훌륭한']
    negative_words = ['싫어', '재미없', '형편없', '싫', '나쁘', '최악', '화나', '거슬려', '불만', '답답', '짜증', '역겹', '못생겼', '자극적']
    
    text_lower = text.lower()
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "긍정"
    elif negative_count > positive_count:
        return "부정"
    else:
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            if polarity > 0.1:
                return "긍정"
            elif polarity < -0.1:
                return "부정"
        except:
            pass
        return "중립"

def analyze_comments(youtube, video_ids, progress_bar):
    """댓글 분석"""
    comments_data = {
        'total_comments': 0,
        'avg_per_video': 0,
        'top_comments': [],
        'languages': Counter(),
        'sentiments': Counter(),
        'main_language': '한글',
        'dominant_sentiment': '중립',
        'positive_pct': 0,
        'neutral_pct': 0,
        'negative_pct': 0
    }
    
    all_comments = []
    
    try:
        for i, video_id in enumerate(video_ids):
            progress = 60 + (i / max(len(video_ids), 1)) * 30
            progress_bar.progress(int(progress))
            
            try:
                comments_request = youtube.commentThreads().list(
                    videoId=video_id,
                    part='snippet',
                    maxResults=20,
                    textFormat='plainText',
                    order='relevance'
                )
                
                comments_response = comments_request.execute()
                
                for item in comments_response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    comment_text = comment['textDisplay'].strip()
                    
                    if len(comment_text) > 5:
                        all_comments.append({
                            'text': comment_text,
                            'likes': comment['likeCount'],
                            'author': comment['authorDisplayName']
                        })
                        comments_data['total_comments'] += 1
            except:
                continue
        
        if all_comments:
            # 감정 분석 및 언어 감지
            for comment in all_comments:
                text = comment['text']
                
                # 언어 감지
                try:
                    lang = detect(text)
                    if lang == 'ko':
                        comments_data['languages']['한글'] += 1
                    elif lang == 'en':
                        comments_data['languages']['영어'] += 1
                    else:
                        comments_data['languages'][lang] += 1
                except:
                    comments_data['languages']['기타'] += 1
                
                # 감정 분석
                sentiment = analyze_sentiment(text)
                comment['sentiment'] = sentiment
                
                if sentiment == "긍정":
                    comments_data['sentiments']['긍정'] += 1
                elif sentiment == "부정":
                    comments_data['sentiments']['부정'] += 1
                else:
                    comments_data['sentiments']['중립'] += 1
            
            # 상위 댓글 (좋아요 순)
            all_comments.sort(key=lambda x: x['likes'], reverse=True)
            comments_data['top_comments'] = all_comments[:10]
            
            # 통계 계산
            comments_data['avg_per_video'] = comments_data['total_comments'] / len(video_ids) if video_ids else 0
            
            # 주요 언어
            if comments_data['languages']:
                comments_data['main_language'] = comments_data['languages'].most_common(1)[0][0]
            
            # 감정 비율
            total = sum(comments_data['sentiments'].values())
            if total > 0:
                comments_data['positive_pct'] = (comments_data['sentiments']['긍정'] / total) * 100
                comments_data['neutral_pct'] = (comments_data['sentiments']['중립'] / total) * 100
                comments_data['negative_pct'] = (comments_data['sentiments']['부정'] / total) * 100
                
                dominant = comments_data['sentiments'].most_common(1)[0][0]
                comments_data['dominant_sentiment'] = dominant
    
    except Exception as e:
        st.warning(f"⚠️ 댓글 분석 중 오류: {str(e)}")
    
    return comments_data

def get_period_stats(videos, period_name):
    """기간별 통계 계산"""
    if not videos:
        return None
    
    view_counts = []
    for video in videos:
        try:
            views = int(video['statistics'].get('viewCount', 0))
            view_counts.append(views)
        except:
            continue
    
    if not view_counts:
        return None
    
    avg_views = statistics.mean(view_counts)
    median_views = statistics.median(view_counts)
    max_views = max(view_counts)
    min_views = min(view_counts)
    
    return {
        'period': period_name,
        'count': len(videos),
        'avg_views': avg_views,
        'median_views': median_views,
        'max_views': max_views,
        'min_views': min_views
    }

def display_period_stats(stats):
    """기간별 통계 표시"""
    if stats is None:
        st.info("해당 기간의 영상이 없습니다.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("업로드 영상", f"{stats['count']}개")
    
    with col2:
        st.metric("평균 조회수", f"{int(stats['avg_views']):,}회")
    
    with col3:
        st.metric("중앙값 조회수", f"{int(stats['median_views']):,}회")
    
    with col4:
        st.metric("최고 조회수", f"{int(stats['max_views']):,}회")

def analyze_keyword(keyword):
    """키워드 분석"""
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1️⃣ 검색
        status_text.text("📡 YouTube에서 검색 중...")
        progress_bar.progress(15)
        
        # 3개월 데이터 전부 가져오기
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        three_months_ago = (now_utc - timedelta(days=90)).isoformat()
        
        search_request = youtube.search().list(
            q=keyword,
            part='snippet',
            type='video',
            order='date',  # 최신순으로 정렬
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
        progress_bar.progress(30)
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        videos_request = youtube.videos().list(
            id=','.join(video_ids),
            part='statistics,snippet',
            maxResults=50
        )
        
        videos_response = videos_request.execute()
        videos = videos_response['items']
        
        # 3️⃣ 기간별 분류
        status_text.text("📈 기간별 분석 중...")
        progress_bar.progress(45)
        
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        one_week_ago = now_utc - timedelta(days=7)
        one_month_ago = now_utc - timedelta(days=30)
        
        videos_last_week = []
        videos_last_month = []
        videos_all = []
        
        for video in videos:
            try:
                publish_date_str = video['snippet']['publishedAt']
                publish_date = datetime.fromisoformat(
                    publish_date_str.replace('Z', '+00:00')
                )
                
                videos_all.append(video)
                
                if publish_date > one_week_ago:
                    videos_last_week.append(video)
                
                if publish_date > one_month_ago:
                    videos_last_month.append(video)
            except:
                continue
        
        # 통계 계산
        total_videos = search_response['pageInfo'].get('totalResults', 0)
        
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
        
        progress_bar.progress(60)
        status_text.text("💬 댓글 분석 중...")
        
        # 4️⃣ 댓글 분석 (상위 5개 영상)
        comments_data = analyze_comments(youtube, video_ids[:5], progress_bar)
        
        progress_bar.progress(100)
        status_text.text("✅ 분석 완료!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        # 5️⃣ 결과 표시
        st.success(f"✅ '{keyword}' 분석 완료!")
        
        st.divider()
        
        # 📊 1주일 분석
        st.markdown("### 📊 최근 1주일 영상 분석")
        stats_week = get_period_stats(videos_last_week, "1주일")
        display_period_stats(stats_week)
        
        st.divider()
        
        # 📊 1개월 분석
        st.markdown("### 📊 최근 1개월 영상 분석")
        stats_month = get_period_stats(videos_last_month, "1개월")
        display_period_stats(stats_month)
        
        st.divider()
        
        # 📊 전체 분석
        st.markdown("### 📊 전체 분석 (최근 3개월)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "경쟁 영상 수",
                f"{total_videos:,}개",
                f"{competition_color} {competition}"
            )
        
        with col2:
            st.metric(
                "분석된 영상",
                f"{len(videos)}개"
            )
        
        with col3:
            view_counts = []
            for video in videos:
                try:
                    views = int(video['statistics'].get('viewCount', 0))
                    view_counts.append(views)
                except:
                    continue
            
            if view_counts:
                avg_views = statistics.mean(view_counts)
                st.metric("평균 조회수", f"{int(avg_views):,}회")
        
        with col4:
            if view_counts:
                max_views = max(view_counts)
                st.metric("최고 조회수", f"{int(max_views):,}회")
        
        st.divider()
        
        # 💬 댓글 분석 결과
        if comments_data['total_comments'] > 0:
            st.markdown("### 💬 댓글 분석")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("총 댓글 수", f"{comments_data['total_comments']:,}개")
            
            with col2:
                st.metric("평균 댓글/영상", f"{comments_data['avg_per_video']:.0f}개")
            
            with col3:
                sentiment = comments_data['dominant_sentiment']
                emoji = "😊" if sentiment == "긍정" else "😢" if sentiment == "부정" else "😐"
                st.metric("주요 감정", f"{emoji} {sentiment}")
            
            with col4:
                st.metric("주요 언어", comments_data['main_language'])
            
            st.divider()
            
            # 감정 분포
            st.markdown("### 📊 감정 분포")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"😊 **긍정**: {comments_data['positive_pct']:.1f}%")
                st.write(f"😐 **중립**: {comments_data['neutral_pct']:.1f}%")
                st.write(f"😢 **부정**: {comments_data['negative_pct']:.1f}%")
            
            with col2:
                st.progress(comments_data['positive_pct']/100, text=f"긍정 {comments_data['positive_pct']:.1f}%")
                st.progress(comments_data['neutral_pct']/100, text=f"중립 {comments_data['neutral_pct']:.1f}%")
                st.progress(comments_data['negative_pct']/100, text=f"부정 {comments_data['negative_pct']:.1f}%")
            
            st.divider()
            
            # 상위 댓글
            if comments_data['top_comments']:
                st.markdown("### 🌟 인기 댓글")
                for i, comment in enumerate(comments_data['top_comments'][:5], 1):
                    with st.expander(f"{i}. {comment['text'][:50]}..."):
                        st.write(f"**댓글:** {comment['text']}")
                        st.write(f"**좋아요:** {comment['likes']:,}개")
                        st.write(f"**감정:** {comment['sentiment']}")
        
        st.divider()
        
        # 최종 판정
        st.markdown("### 🎯 최종 판정")
        
        verdict_text = f"""
**주제:** {keyword}

이 주제는 현재 **{total_videos:,}개**의 경쟁 영상이 있으며,
경쟁도는 **{competition}**입니다.

- **최근 1주일:** {len(videos_last_week)}개 영상 업로드
- **최근 1개월:** {len(videos_last_month)}개 영상 업로드
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
        
        if len(videos_last_week) > 20:
            recommendations.append("🔥 **주간 업로드가 많습니다.** 빠른 실행이 중요합니다!")
        else:
            recommendations.append("✨ **주간 업로드가 적당합니다.** 기회가 있습니다!")
        
        if comments_data['total_comments'] > 0:
            if comments_data['positive_pct'] > 60:
                recommendations.append("😊 **댓글 반응이 긍정적입니다!** 관객 만족도가 높습니다.")
            elif comments_data['negative_pct'] > 40:
                recommendations.append("⚠️ **부정적 댓글이 많습니다.** 콘텐츠 개선이 필요할 수 있습니다.")
        
        for rec in recommendations:
            st.write(rec)
        
        st.divider()
        
        # 상세 비교
        with st.expander("📋 1주일 vs 1개월 vs 전체 비교"):
            comparison_data = {
                '1주일': stats_week,
                '1개월': stats_month,
                '전체': get_period_stats(videos, "전체")
            }
            
            for period_name, period_stats in comparison_data.items():
                if period_stats:
                    st.write(f"""
**{period_name}:**
- 영상 수: {period_stats['count']}개
- 평균 조회수: {int(period_stats['avg_views']):,}회
- 중앙값 조회수: {int(period_stats['median_views']):,}회
- 최고 조회수: {int(period_stats['max_views']):,}회
- 최저 조회수: {int(period_stats['min_views']):,}회
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
- 1주일/1개월/전체 데이터를 따로 분석합니다
- 댓글 감정 분석으로 시청자 반응 확인
- 모든 데이터는 실시간으로 가져옵니다

**포가튼 베일러 - Forgotten Valor** 🎬
""")
