import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from streamlit_mic_recorder import speech_to_text

st.set_page_config(page_title="FilterTube Voice AI", page_icon="🎙️")
st.title("🎙️ FilterTube - बोलकर 100% असली फ्री वीडियो खोजें")
st.write("माइक दबाकर बोलें कि आपको क्या चाहिए। AI वीडियो की पूरी स्क्रिप्ट और डिस्क्रिप्शन के 0% से 100% अंत तक जांच करेगा।")

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

def get_any_transcript(video_id):
    try:
        # किसी भी उपलब्ध भाषा (Auto-generated सहित) के सबटाइटल्स निकालना
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            data = transcript.fetch()
            return " ".join([item['text'] for item in data])
    except Exception:
        return None

if st.button("🔍 0% से 100% जांच करें और वीडियो दिखाएं"):
    if not yt_api_key or not gemini_api_key:
        st.error("कृपया पहले बाईं तरफ दोनों API Keys डालें!")
    elif not query:
        st.warning("कृपया पहले माइक दबाकर बोलें या कुछ लिखें।")
    else:
        try:
            with st.spinner("YouTube से वीडियो, उनकी स्क्रिप्ट और पूरा डिस्क्रिप्शन निकालकर 0% से 100% जांच की जा रही है..."):
                youtube = build('youtube', 'v3', developerKey=yt_api_key)
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel('gemini-3.5-flash-lite')
                
                # यूज़र की हिंदी बात को YouTube के लिए सटीक सर्च कीवर्ड में बदलना
                kw_prompt = f"Convert this user request into a short 4-5 word YouTube search query (in English or Hinglish for best YouTube results): {query}"
                search_kw = model.generate_content(kw_prompt).text.strip()
                
                search_response = youtube.search().list(q=search_kw, part='snippet', type='video', maxResults=max_videos).execute()
                video_ids = [item['id']['videoId'] for item in search_response['items']]
                
                if not video_ids:
                    st.warning("YouTube पर इस टॉपिक से जुड़ा कोई वीडियो नहीं मिला।")
                else:
                    # वीडियो का पूरा डिस्क्रिप्शन भी निकालना (ताकि बिना CC वाले वीडियो भी चेक हो सकें)
                    details_response = youtube.videos().list(part='snippet', id=','.join(video_ids)).execute()
                    
                    videos_data = []
                    batch_text = ""
                    
                    for idx, item in enumerate(details_response['items']):
                        video_id = item['id']
                        title = item['snippet']['title']
                        desc = item['snippet']['description']
                        url = f"https://youtube.com{video_id}"
                        
                        transcript = get_any_transcript(video_id)
                        source_type = "पूरी स्क्रिप्ट (CC)" if transcript else "पूरा डिस्क्रिप्शन और डिटेल्स"
                        content_to_check = transcript[:8000] if transcript else desc[:4000]
                        
                        videos_data.append({"id": idx, "title": title, "url": url, "source": source_type})
                        batch_text += f"\n--- VIDEO_ID: {idx} | TITLE: {title} | SOURCE: {source_type} ---\nCONTENT: {content_to_check}\n"
                    
                    prompt = f"""
                    तुम एक सख्त Fact-Checker हो। यूज़र की डिमांड यह है: "{query}"
                    नीचे कई YouTube वीडियो की स्क्रिप्ट या डिस्क्रिप्शन दिया गया है। हर वीडियो को 0% से 100% तक जांचो:
                    1. क्या यह वीडियो यूज़र की डिमांड का सही और पूरा समाधान देता है?
                    2. अगर वीडियो में 'फ्री' बोलकर अंत में क्रेडिट, टोकन, डेली लिमिट, फ्री ट्रायल या पेड प्लान की बात हो, या बताया गया टूल आज की तारीख में पेड हो गया हो, तो उसे तुरंत REJECT कर दो।
                    3. केवल उन्हीं वीडियो की लिस्ट दो जो 100% PASS हैं, बिल्कुल इस फॉर्मेट में:
                    PASS_ID: [वीडियो का नंबर] | TOOLS: [टूल्स के नाम] | REPORT: [2 लाइन में हिंदी में सच्चाई की रिपोर्ट]
                    अगर कोई भी पास न हो, तो लिखो: NONE
                    
                    वीडियो डेटा:
                    {batch_text}
                    """
                    result = model.generate_content(prompt).text
                    
                    if "NONE" in result or "PASS_ID:" not in result:
                        st.error("❌ जांचे गए किसी भी वीडियो में 0% से 100% तक आपकी शर्तें पूरी नहीं हुईं (सबमें पेड/क्रेडिट का चक्कर था या सही समाधान नहीं था)। स्लाइडर से वीडियो की संख्या बढ़ाकर फिर से जांचें।")
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
                                        st.caption(f"🔎 जांच का आधार: {v_info['source']}")
                                        st.write(f"🛠️ **बताए गए टूल्स:** {tools}")
                                        st.write(f"📋 **सच्चाई की रिपोर्ट:** {report}")
                                        st.markdown(f"[👉 यहाँ क्लिक करके वीडियो देखें]({v_info['url']})")
                                        st.divider()
                                except Exception:
                                    continue
        except Exception as e:
            st.error(f"कुछ तकनीकी दिक्कत आई है: {str(e)}")
