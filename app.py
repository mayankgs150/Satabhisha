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

# बोलकर सर्च करने का सेक्शन
st.subheader("🎤 यहाँ क्लिक करके बोलें:")
voice_text = speech_to_text(
    language='hi-IN',
    start_prompt="🔴 बोलना शुरू करें (Click to Speak)",
    stop_prompt="⏹️ रुकें (Stop)",
    just_once=True,
    key='STT'
)

# अगर यूज़र ने बोला है तो बॉक्स में अपने आप लिखा आ जाएगा
if voice_text:
    st.session_state['search_query'] = voice_text

query = st.text_input(
    "आपकी डिमांड (बोलें या लिखें):",
    value=st.session_state.get('search_query', ''),
    placeholder="जैसे: मुझे ऐसा वीडियो चाहिए जिसमें बिना पैसे और बिना लिमिट के पूरा AI वीडियो बनाना सिखाया हो"
)

max_videos = st.slider("कितने वीडियो की गहराई से जांच करनी है?", 3, 15, 5)

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
        return " ".join([item['text'] for item in transcript_list])
    except Exception:
        return None

def strict_verify_video(user_demand, transcript, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    तुम एक सख्त Fact-Checker हो। यूज़र की डिमांड यह है: "{user_demand}"
    
    नीचे एक YouTube वीडियो की पूरी स्क्रिप्ट (0% शुरू से 100% अंत तक) दी गई है। इसे ध्यान से जांचो:
    1. क्या यह वीडियो 0% से 100% तक यूज़र की हर शर्त को पूरा करता है?
    2. अगर वीडियो में 'फ्री' बोलकर अंत में क्रेडिट, टोकन, डेली लिमिट, फ्री ट्रायल या पेड प्लान की बात की गई है, तो इसे तुरंत REJECT कर दो।
    3. अपने ताज़ा ज्ञान से यह भी वेरिफाई करो कि वीडियो में जिस टूल/वेबसाइट का नाम लिया गया है, क्या वह आज की तारीख में वाकई वैसा ही फ्री है जैसा यूट्यूबर दावा कर रहा है? अगर यूट्यूबर झूठ बोल रहा है या टूल अब पेड हो गया है, तो REJECT कर दो।
    
    जवाब बिल्कुल इसी फॉर्मेट में दो:
    RESULT: [PASS या REJECT]
    TOOLS: [वीडियो में बताए गए टूल्स के नाम]
    REPORT: [2 लाइन में हिंदी में बताओ कि यह वीडियो क्यों पास हुआ और क्या वाकई 100% सही है]
    
    पूरी स्क्रिप्ट:
    {transcript[:25000]}
    """
    response = model.generate_content(prompt)
    return response.text

if st.button("🔍 0% से 100% जांच करें और वीडियो दिखाएं"):
    if not yt_api_key or not gemini_api_key:
        st.error("कृपया पहले बाईं तरफ दोनों API Keys डालें!")
    elif not query:
        st.warning("कृपया पहले माइक दबाकर बोलें या कुछ लिखें।")
    else:
        with st.spinner("YouTube से वीडियो निकालकर 0% से 100% तक पूरी स्क्रिप्ट और टूल्स की सच्चाई जांची जा रही है..."):
            youtube = build('youtube', 'v3', developerKey=yt_api_key)
            # AI से बेहतर यूट्यूब सर्च कीवर्ड बनवाना
            genai.configure(api_key=gemini_api_key)
            kw_model = genai.GenerativeModel('gemini-2.5-flash')
            search_kw = kw_model.generate_content(f"Convert this user request into a short 4-5 word YouTube search query in English: {query}").text.strip()
            
            search_response = youtube.search().list(q=search_kw, part='snippet', type='video', maxResults=max_videos).execute()
            passed_count = 0
            
            for item in search_response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                url = f"https://youtube.com{video_id}"
                
                transcript = get_transcript(video_id)
                if transcript:
                    check = strict_verify_video(query, transcript, gemini_api_key)
                    if "RESULT: PASS" in check:
                        passed_count += 1
                        tools = check.split("TOOLS:")[1].split("REPORT:")[0].strip() if "TOOLS:" in check else ""
                        report = check.split("REPORT:")[1].strip() if "REPORT:" in check else ""
                        
                        st.success(f"✅ **100% वेरिफाइड वीडियो:** {title}")
                        st.write(f"🛠️ **बताए गए टूल्स:** {tools}")
                        st.write(f"📋 **सच्चाई की रिपोर्ट:** {report}")
                        st.markdown(f"[👉 यहाँ क्लिक करके वीडियो देखें]({url})")
                        st.divider()
                        
            if passed_count == 0:
                st.error("❌ जांचे गए किसी भी वीडियो में 0% से 100% तक आपकी शर्तें पूरी नहीं हुईं (सबमें या तो अंत में पेड/क्रेडिट का चक्कर था या यूट्यूबर गलत जानकारी दे रहा था)। ऊपर स्लाइडर से वीडियो की संख्या बढ़ाकर फिर से जांचें।")
