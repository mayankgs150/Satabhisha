import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from streamlit_mic_recorder import speech_to_text

st.set_page_config(page_title="FilterTube Voice AI", page_icon="🎙️")
st.title("🎙️ FilterTube - बोलकर 100% असली फ्री वीडियो खोजें")
st.write("माइक दबाकर बोलें कि आपको क्या चाहिए। AI वीडियो के 0% से 100% अंत तक जांच करेगा और लाइव वेरिफाई करेगा।")

with st.sidebar:
    st.header("⚙️ API Keys डालें")
    yt_api_key = st.text_input("YouTube Data API Key", type="password")
    gemini_api_key = st.text_input("Gemini API Key", type="password")

st.subheader("🎤 यहाँ क्लिक करके बोलें:")
voice_text = speech_to_text(
    language='hi-IN',
    start_prompt="🔴 बोलना शुरू करें (Click to Speak)",
    stop_prompt="⏹️ रुकें (Stop)",
    just_once=True,
    key='STT'
)

if voice_text:
    st.session_state['search_query'] = voice_text

query = st.text_input(
    "आपकी डिमांड (बोलें या लिखें):",
    value=st.session_state.get('search_query', ''),
    placeholder="जैसे: मुझे ऐसा वीडियो चाहिए जिसमें बिना पैसे और बिना लिमिट के पूरा AI वीडियो बनाना सिखाया हो"
)

max_videos = st.slider("कितने वीडियो की गहराई से जांच करनी है?", 3, 10, 5)

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
        return " ".join([item['text'] for item in transcript_list])
    except Exception:
        return None

if st.button("🔍 0% से 100% जांच करें और वीडियो दिखाएं"):
    if not yt_api_key or not gemini_api_key:
        st.error("कृपया पहले बाईं तरफ दोनों API Keys डालें!")
    elif not query:
        st.warning("कृपया पहले माइक दबाकर बोलें या कुछ लिखें।")
    else:
        try:
            with st.spinner("YouTube से वीडियो निकाले जा रहे हैं और सभी की स्क्रिप्ट एक साथ जांची जा रही है..."):
                youtube = build('youtube', 'v3', developerKey=yt_api_key)
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel('gemini-3.5-flash-lite')
                
                # 1 ही रिक्वेस्ट में कीवर्ड और सर्च
                search_response = youtube.search().list(q=query, part='snippet', type='video', maxResults=max_videos).execute()
                
                videos_data = []
                batch_text = ""
                
                for idx, item in enumerate(search_response['items']):
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']
                    url = f"https://youtube.com{video_id}"
                    transcript = get_transcript(video_id)
                    if transcript:
                        videos_data.append({"id": idx, "title": title, "url": url})
                        batch_text += f"\n--- VIDEO_ID: {idx} | TITLE: {title} ---\nSCRIPT: {transcript[:8000]}\n"
                
                if not videos_data:
                    st.warning("इन वीडियो में सबटाइटल्स (CC) उपलब्ध नहीं थे, इसलिए स्क्रिप्ट पढ़ी नहीं जा सकी। दूसरा टॉपिक बोलें।")
                else:
                    prompt = f"""
                    तुम एक सख्त Fact-Checker हो। यूज़र की डिमांड यह है: "{query}"
                    नीचे कई YouTube वीडियो की पूरी स्क्रिप्ट (0% से 100% तक) दी गई है। हर वीडियो को जांचो:
                    1. क्या वीडियो 0% से 100% तक यूज़र की हर शर्त पूरी करता है?
                    2. अगर वीडियो में 'फ्री' बोलकर अंत में क्रेडिट, टोकन, डेली लिमिट या पेड प्लान की बात हो, या बताया गया टूल आज की तारीख में पेड हो गया हो, तो उसे REJECT करो।
                    3. केवल उन्हीं वीडियो की लिस्ट दो जो 100% PASS हैं, बिल्कुल इस फॉर्मेट में:
                    PASS_ID: [वीडियो का नंबर] | TOOLS: [टूल्स के नाम] | REPORT: [2 लाइन में हिंदी में सच्चाई की रिपोर्ट]
                    अगर कोई भी पास न हो, तो लिखो: NONE
                    
                    वीडियो डेटा:
                    {batch_text}
                    """
                    result = model.generate_content(prompt).text
                    
                    if "NONE" in result or "PASS_ID:" not in result:
                        st.error("❌ जांचे गए किसी भी वीडियो में 0% से 100% तक आपकी शर्तें पूरी नहीं हुईं (सबमें पेड/क्रेडिट का चक्कर था)।")
                    else:
                        for line in result.split("\n"):
                            if "PASS_ID:" in line:
                                try:
                                    vid_num = int(line.split("PASS_ID:")[1].split("|")[0].strip())
                                    tools = line.split("TOOLS:")[1].split("|")[0].strip()
                                    report = line.split("REPORT:")[1].strip()
                                    v_info = next((v for v in videos_data if v["id"] == vid_num), None)
                                    if v_info:
                                        st.success(f"✅ **100% वेरिफाइड वीडियो:** {v_info['title']}")
                                        st.write(f"🛠️ **बताए गए टूल्स:** {tools}")
                                        st.write(f"📋 **सच्चाई की रिपोर्ट:** {report}")
                                        st.markdown(f"[👉 यहाँ क्लिक करके वीडियो देखें]({v_info['url']})")
                                        st.divider()
                                except Exception:
                                    continue
        except Exception as e:
            st.error(f"कुछ तकनीकी दिक्कत आई है: {str(e)}")
