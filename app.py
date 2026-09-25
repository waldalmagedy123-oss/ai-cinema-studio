import os
import time
import requests
import asyncio
import streamlit as st
from google import genai
from google.genai import types
import replicate
import edge_tts

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

st.set_page_config(
    page_title="AI Cinema Studio Pro (Interactive)",
    page_icon="🎬",
    layout="wide"
)

# ----------------- وظائف مساعدة الذكاء الاصطناعي -----------------
def ask_gemini(instruction: str, context: str, gemini_key: str) -> str:
    client = genai.Client(api_key=gemini_key)
    prompt = f"{instruction}\n\nسياق المشروع أو الفكرة الحالية:\n{context}"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            return res.text.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                return f"خطأ في الاتصال بالنموذج: {e}"

def generate_voiceover(text: str, filename: str, voice_name: str):
    async def _runner():
        comm = edge_tts.Communicate(text, voice=voice_name)
        await comm.save(filename)
    asyncio.run(_runner())

def generate_video(prompt: str, filename: str, token: str):
    os.environ["REPLICATE_API_TOKEN"] = token
    output = replicate.run(
        "minimax/video-01",
        input={"prompt": prompt, "prompt_optimizer": True}
    )
    r = requests.get(str(output))
    with open(filename, "wb") as f:
        f.write(r.content)

# ----------------- تهيئة الذاكرة -----------------
if "project_title" not in st.session_state:
    st.session_state.project_title = "التحول من ضعيف إلى قاتل الشياطين"
if "treatment" not in st.session_state:
    st.session_state.treatment = ""
if "characters" not in st.session_state:
    st.session_state.characters = [{"name": "ريان", "role": "قاتل الشياطين", "visual": "شاب في أوائل العشرينيات، شعر أسود مموج، عينان عنبريتان، سيف فولاذي أسود بنار قرمزية."}]
if "locations" not in st.session_state:
    st.session_state.locations = [{"name": "القرية المحترقة", "setting": "قرية جبلية منكوبة تغطيها طبقات من الرماد ودخان النيران البرتقالية."}]
if "scenes" not in st.session_state:
    st.session_state.scenes = [
        {
            "location": "أطلال القرية",
            "time": "ليل / رماد ونيران",
            "camera": "Low-angle slow dolly in",
            "dialogue": "حين سلب الظلام كل ما أملك، لم يعد في هذا الجسد الضعيف مكان للخوف بل قسم محفور بالنار.",
            "prompt": "Cinematic 8k, low-angle slow dolly in, a slender young man kneeling amidst the smoldering ash of a burned fantasy village, floating glowing embers, dark blue night atmosphere contrasted with warm orange fires, tears evaporating on soot-covered face, hyper-realistic, dramatic lighting."
        }
    ]
if "lighting" not in st.session_state:
    st.session_state.lighting = "إضاءة نيران دافئة مع ظلال زرقاء خافتة."
if "crew" not in st.session_state:
    st.session_state.crew = "مخرج، مدير تصوير، مصمم معارك، مهندس مؤثرات."
if "gear" not in st.session_state:
    st.session_state.gear = "كاميرا سينمائية، عدسات أنامورفيك، مثبت حركة."

# ----------------- الشريط الجانبي -----------------
with st.sidebar:
    st.title("⚙️ استوديو الإنتاج السينمائي")
    gemini_key = st.text_input("Gemini API Key:", type="password")
    replicate_token = st.text_input("Replicate API Token:", type="password")
    voice_type = st.selectbox(
        "🎙️ نبرة صوت الراوي:",
        ["ar-SA-HamedNeural", "ar-SA-ShakirNeural", "ar-EG-ShakirNeural"]
    )
    st.markdown("---")
    st.caption("💡 تحكم كامل بالخيارات مع مساعدة الذكاء الاصطناعي.")

st.title("🎬 لوحة التحكم السينمائية التفاعلية")

col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.session_state.project_title = st.text_input("📽️ عنوان الفيلم:", value=st.session_state.project_title)
with col_t2:
    if st.button("🪄 اقتراح عنوان جذاب"):
        if gemini_key:
            suggestion = ask_gemini("اقترح عنواناً سينمائياً مشوقاً وقصيراً لهذا الفيلم.", st.session_state.treatment, gemini_key)
            st.session_state.project_title = suggestion.replace('"', '').strip()
            st.rerun()

tab1, tab2, tab3, tab4 = st.tabs([
    "✍️ كتابة وتطوير", 
    "🌍 العالم والأصول", 
    "🎥 لوح وإنتاج", 
    "📋 أوراق الإنتاج"
])

# 1. كتابة وتطوير
with tab1:
    st.subheader("📜 المعالجة الدرامية والقصة (Treatment)")
    st.session_state.treatment = st.text_area(
        "نص المعالجة الدرامية:",
        value=st.session_state.treatment,
        height=180
    )
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("🪄 مساعدة AI: توليد المعالجة"):
            if gemini_key:
                st.session_state.treatment = ask_gemini("قم بصياغة معالجة درامية سينمائية احترافية متكاملة لقصة تحول شخص ضعيف إلى قاتل شياطين ينتقم لقريته.", st.session_state.project_title, gemini_key)
                st.rerun()
    with col_w2:
        if st.button("✨ تحسين الأسلوب السينمائي"):
            if gemini_key and st.session_state.treatment:
                st.session_state.treatment = ask_gemini("أعد صياغة هذا النص ليكون أكثر تشويقاً وقوة بصرياً.", st.session_state.treatment, gemini_key)
                st.rerun()

# 2. العالم والأصول
with tab2:
    st.subheader("👥 الشخصيات")
    for i, ch in enumerate(st.session_state.characters):
        with st.expander(f"شخصية: {ch.get('name', '')}", expanded=True):
            ch["name"] = st.text_input("الاسم:", value=ch.get("name", ""), key=f"cn_{i}")
            ch["role"] = st.text_input("الدور:", value=ch.get("role", ""), key=f"cr_{i}")
            ch["visual"] = st.text_area("المظهر البصري:", value=ch.get("visual", ""), key=f"cv_{i}")
            if st.button(f"🪄 مساعدة AI للمظهر #{i+1}", key=f"b_ch_{i}"):
                if gemini_key:
                    ch["visual"] = ask_gemini(f"اكتب وصفاً بصرياً دقيقاً بالملامح والملابس لشخصية {ch['name']} بدور {ch['role']}.", st.session_state.treatment, gemini_key)
                    st.rerun()
    
    if st.button("➕ إضافة شخصية جديدة"):
        st.session_state.characters.append({"name": "شخصية جديدة", "role": "", "visual": ""})
        st.rerun()

    st.markdown("---")
    st.subheader("🏛️ الأماكن والبيئات")
    for j, loc in enumerate(st.session_state.locations):
        with st.expander(f"موقع: {loc.get('name', '')}", expanded=True):
            loc["name"] = st.text_input("اسم الموقع:", value=loc.get("name", ""), key=f"ln_{j}")
            loc["setting"] = st.text_area("أجواء البيئة والديكور:", value=loc.get("setting", ""), key=f"ls_{j}")
            if st.button(f"🪄 مساعدة AI لديكور الموقع #{j+1}", key=f"b_loc_{j}"):
                if gemini_key:
                    loc["setting"] = ask_gemini(f"اكتب وصفاً بيئياً وسينمائياً لموقع: {loc['name']}.", st.session_state.treatment, gemini_key)
                    st.rerun()
                    
    if st.button("➕ إضافة موقع جديد"):
        st.session_state.locations.append({"name": "موقع جديد", "setting": ""})
        st.rerun()

# 3. لوح وإنتاج (تصحيح خطأ دمج الفيديو هنا)
with tab3:
    st.subheader("🎬 لوحة القصة والمشاهد")
    for k, sc in enumerate(st.session_state.scenes):
        with st.container():
            st.markdown(f"### 📍 المشهد #{k+1}")
            c_s1, c_s2 = st.columns([1, 1])
            with c_s1:
                sc["location"] = st.text_input("الموقع:", value=sc.get("location", ""), key=f"sl_{k}")
                sc["camera"] = st.text_input("حركة الكاميرا:", value=sc.get("camera", ""), key=f"scam_{k}")
                sc["dialogue"] = st.text_area("نص الراوي / الحوار:", value=sc.get("dialogue", ""), key=f"sd_{k}")
            with c_s2:
                sc["prompt"] = st.text_area("موجه الفيديو بالإنجليزية (Video Prompt):", value=sc.get("prompt", ""), key=f"sp_{k}", height=130)
                if st.button(f"🪄 توليد البرومبت بالإنجليزية #{k+1}", key=f"bp_{k}"):
                    if gemini_key:
                        sc["prompt"] = ask_gemini(f"اكتب برومبت سينمائي دقيق بالإنجليزية لمشهد بكاميرا {sc['camera']} وموقع {sc['location']} وحوار: {sc['dialogue']}", st.session_state.treatment, gemini_key)
                        st.rerun()
            st.markdown("---")

    c_add, c_del = st.columns(2)
    with c_add:
        if st.button("➕ إضافة مشهد جديد"):
            st.session_state.scenes.append({"location": "", "camera": "", "dialogue": "", "prompt": ""})
            st.rerun()
    with c_del:
        if len(st.session_state.scenes) > 1 and st.button("➖ حذف آخر مشهد"):
            st.session_state.scenes.pop()
            st.rerun()

    st.markdown("### 🚀 غرفة الإنتاج النهائي (Render Studio)")
    if st.button("🎥 توليد ودمج كافة المشاهد المحددة أعلاه", type="primary", use_container_width=True):
        if not replicate_token:
            st.error("⚠️ يرجى إدخال Replicate API Token في الشريط الجانبي أولاً.")
        else:
            status = st.status("🎬 جاري العمل على توليد الفيديو والصوت...", expanded=True)
            clips = []
            try:
                for idx, scene in enumerate(st.session_state.scenes):
                    status.write(f"🎥 إنتاج المشهد #{idx+1}...")
                    v_file = f"sc_{idx}.mp4"
                    a_file = f"au_{idx}.mp3"
                    
                    dialogue_text = scene["dialogue"].strip() if scene.get("dialogue") else "..."
                    generate_voiceover(dialogue_text, a_file, voice_type)
                    generate_video(scene["prompt"], v_file, replicate_token)
                    
                    v_clip = VideoFileClip(v_file)
                    a_clip = AudioFileClip(a_file)
                    
                    # التصحيح البرمجي المتوافق مع الإصدارين
                    if hasattr(v_clip, "with_duration"):
                        v_clip = v_clip.with_duration(a_clip.duration).with_audio(a_clip)
                    else:
                        v_clip = v_clip.set_duration(a_clip.duration).set_audio(a_clip)
                        
                    clips.append(v_clip)
                
                status.write("🎞️ دمج الفيديو النهائي بصيغة MP4...")
                final_film = "cinema_movie.mp4"
                final = concatenate_videoclips(clips, method="compose")
                final.write_videofile(final_film, fps=24, codec="libx264", audio_codec="aac")
                status.update(label="✅ اكتمل إنتاج الفيلم بنجاح!", state="complete")
                
                st.video(final_film)
                with open(final_film, "rb") as f:
                    st.download_button("📥 تحميل الفيلم النهائي", f, file_name=final_film, mime="video/mp4")
            except Exception as e:
                status.update(label="❌ حدث خطأ أثناء التصيير", state="error")
                st.error(f"تفاصيل الخطأ: {e}")

# 4. أوراق الإنتاج
with tab4:
    st.subheader("📋 وثائق الإنتاج الميداني")
    st.session_state.lighting = st.text_area("⚡ مخطط الإضاءة:", value=st.session_state.lighting)
    st.session_state.crew = st.text_area("👥 طاقم العمل:", value=st.session_state.crew)
    st.session_state.gear = st.text_area("🎥 المعدات المطلوبة:", value=st.session_state.gear)
    if st.button("🪄 اقتراح خطة الإنتاج كاملة بالذكاء الاصطناعي"):
        if gemini_key:
            st.session_state.lighting = ask_gemini("اقترح توزيع إضاءة سينمائي لهذا الفيلم.", st.session_state.treatment, gemini_key)
            st.session_state.crew = ask_gemini("اقترح قائمة الطاقم الميداني المناسب.", st.session_state.treatment, gemini_key)
            st.session_state.gear = ask_gemini("اقترح أنسب الكاميرات والعدسات والمعدات.", st.session_state.treatment, gemini_key)
            st.rerun()
    else:
            with st.spinner("جاري تحليل متطلبات الإنتاج..."):
                st.session_state.lighting = ask_gemini("اقترح توزيع إضاءة احترافي مناسب لهذا الفيلم.", st.session_state.treatment, gemini_key)
                st.session_state.crew = ask_gemini("اقترح قائمة الطاقم الميداني المناسب لإنتاج هذا العمل.", st.session_state.treatment, gemini_key)
                st.session_state.gear = ask_gemini("اقترح أنسب الكاميرات والعدسات والمعدات لتحقيق الطابع البصري للفيلم.", st.session_state.treatment, gemini_key)
                st.rerun()
