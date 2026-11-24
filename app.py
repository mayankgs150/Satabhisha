import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

st.set_page_config(page_title="FilterTube", page_icon="🔍")
st.title("🔍 FilterTube - 100% Free Video Finder")
st.write("सिर्फ वही वीडियो देखें जिनमें वाकई 100% फ्री टूल्स बताए गए हैं।")

with st.sidebar:
    st.header("⚙️ API Keys डालें")
    yt_api_key = st.text_input("YouTube Data API Key", type="password")
    gemini_api_key = st.text_input("Gemini API Key", type="password")

query = st.text_input("आप क्या ढूंढ रहे हैं? (जैसे: AI video generator free)")
max_videos = st.slider("कितने वीडियो चेक करने हैं?", 3, 15, 5)

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
        return " ".join([item['text'] for item in transcript_list])
    except Exception:
        return None

def analyze_video_with_ai(transcript, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    इस YouTube वीडियो की स्क्रिप्ट पढ़ें और बताएं कि क्या इसमें बताया गया टूल या तरीका पूरी तरह मुफ़्त (100% Free & Unlimited) है?
    अगर अंत में क्रेडिट, टोकन या पेड प्लान की बात हो तो PAID लिखें।
    जवाब फॉर्मेट:
    STATUS: [FREE या PAID]
    REASON: [1 लाइन में हिंदी में कारण]
    स्क्रिप्ट: {transcript[:15000]}
    """
    response = model.generate_content(prompt)
    return response.text

if st.button("सर्च और फिल्टर करें"):
    if not yt_api_key or not gemini_api_key:
        st.error("कृपया पहले बाईं तरफ दोनों API Keys डालें!")
    elif not query:
        st.warning("कृपया सर्च करने के लिए कुछ लिखें।")
    else:
        with st.spinner("वीडियो चेक किए जा रहे हैं..."):
            youtube = build('youtube', 'v3', developerKey=yt_api_key)
            search_response = youtube.search().list(q=query, part='snippet', type='video', maxResults=max_videos).execute()
            found_free = 0
            for item in search_response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                url = f"https://youtube.com{video_id}"
                transcript = get_transcript(video_id)
                if transcript:
                    analysis = analyze_video_with_ai(transcript, gemini_api_key)
                    if "STATUS: FREE" in analysis:
                        found_free += 1
                        reason = analysis.split("REASON:").strip() if "REASON:" in analysis else ""
                        st.success(f"✅ **{title}**")
                        st.write(f"**AI रिपोर्ट:** {reason}")
                        st.markdown(f"[👉 वीडियो देखें]({url})")
                        st.divider()
            if found_free == 0:
                st.warning("कोई भी 100% फ्री वीडियो नहीं मिला। वीडियो की संख्या बढ़ाकर फिर से ट्राय करें।")

