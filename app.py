import os
import time
import requests
import asyncio
import streamlit as st
from pydantic import BaseModel
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

# ----------------- وظائف مساعدة الذكاء الاصطناعي (AI Helpers) -----------------
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

# ----------------- تهيئة ذاكرة الجلسة التفاعلية -----------------
if "project_title" not in st.session_state:
    st.session_state.project_title = "مشروع فيلم بدون عنوان"
if "treatment" not in st.session_state:
    st.session_state.treatment = ""
if "characters" not in st.session_state:
    st.session_state.characters = [{"name": "البطل", "role": "مستكشف", "visual": "رجل في الثلاثينات، يرتدي معطف جلد قديماً، ملامح جادة ومغبرة."}]
if "locations" not in st.session_state:
    st.session_state.locations = [{"name": "الكهف الأثري", "setting": "كهف مظلم وممتد، إضاءة مشاعل خافتة تنعكس على جدران حجرية رطبة ونقوش قديمة."}]
if "scenes" not in st.session_state:
    st.session_state.scenes = [
        {
            "location": "الكهف الأثري",
            "time": "ليل / داخلي",
            "camera": "Slow cinematic dolly in, low angle",
            "dialogue": "هنا يرقد سر لم يكشفه بشر منذ آلاف السنين.",
            "prompt": "Cinematic 8k, low angle slow dolly in, an ancient explorer walking with a torch inside a misty ancient tomb, hyper-realistic, 35mm film style."
        }
    ]
if "lighting" not in st.session_state:
    st.session_state.lighting = "إضاءة مشاعل خافتة ودافئة (Warm Key light) مع ظلال قوية وضوء خلفي بارد (Cold Rim light)."
if "crew" not in st.session_state:
    st.session_state.crew = "مخرج، مدير تصوير (DP)، مهندس إضاءة، مهندس صوت، فني مؤثرات بصرية."
if "gear" not in st.session_state:
    st.session_state.gear = "كاميرا ARRI Alexa Mini، عدسات Anamorphic 35mm، مثبت Gimbal، أجهزة توليد ضباب."

# ----------------- الشريط الجانبي للإعدادات -----------------
with st.sidebar:
    st.title("⚙️ استوديو الإنتاج السينمائي")
    gemini_key = st.text_input("Gemini API Key:", type="password")
    replicate_token = st.text_input("Replicate API Token:", type="password")
    voice_type = st.selectbox(
        "🎙️ نبرة صوت الراوي:",
        ["ar-SA-HamedNeural", "ar-SA-ShakirNeural", "ar-EG-ShakirNeural"]
    )
    st.markdown("---")
    st.caption("💡 تحكم يدوي كامل مع ميزات التوليد الذكي لكل عنصر.")

st.title("🎬 لوحة التحكم السينمائية التفاعلية (Micro-SaaS)")
st.markdown("يمكنك كتابة وتعديل كل عنصر يدوياً، أو الاستعانة بمساعد الذكاء الاصطناعي بجانب كل خانة لاقتراح الأفكار.")

# عنوان الفيلم والفكرة العامة
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.session_state.project_title = st.text_input("📽️ عنوان الفيلم:", value=st.session_state.project_title)
with col_t2:
    if st.button("🪄 اقتراح عنوان سينمائي جذاب"):
        if not gemini_key:
            st.error("أدخل مفتاح Gemini أولاً")
        else:
            suggestion = ask_gemini("اقترح عنواناً سينمائياً مشوقاً وقصيراً لهذا الفيلم بناءً على ملخصه الحالي أو المعالجة.", st.session_state.treatment, gemini_key)
            st.session_state.project_title = suggestion.replace('"', '').strip()
            st.rerun()

# التبويبات الرئيسية
tab1, tab2, tab3, tab4 = st.tabs([
    "✍️ كتابة وتطوير", 
    "🌍 العالم والأصول", 
    "🎥 لوح وإنتاج", 
    "📋 أوراق الإنتاج"
])

# ----------------- 1. تبويب كتابة وتطوير -----------------
with tab1:
    st.subheader("📜 المعالجة الدرامية والقصة (Treatment)")
    st.session_state.treatment = st.text_area(
        "نص المعالجة الدرامية وتفاصيل القصة:",
        value=st.session_state.treatment,
        height=180,
        placeholder="اكتب المعالجة الدرامية هنا بنفسك، أو اكتب فكرة موجزة واضغط زر المساعد بالأسفل لصياغتها..."
    )
    
    col_ai_write, col_ai_improve = st.columns(2)
    with col_ai_write:
        if st.button("🪄 مساعدة AI: توليد وتوسيع المعالجة من الفكرة"):
            if not gemini_key:
                st.error("يرجى إدخال مفتاح Gemini")
            else:
                with st.spinner("جاري صياغة المعالجة الدرامية..."):
                    res = ask_gemini("قم بصياغة معالجة درامية سينمائية احترافية (Treatment) تشمل الصراع والبداية والذروة بأسلوب مشوق.", st.session_state.treatment or st.session_state.project_title, gemini_key)
                    st.session_state.treatment = res
                    st.rerun()
                    
    with col_ai_improve:
        if st.button("✨ مساعدة AI: تحسين وتدقيق الأسلوب السينمائي"):
            if not gemini_key or not st.session_state.treatment.strip():
                st.warning("يرجى التأكد من وجود نص المعالجة ومفتاح الـ API")
            else:
                with st.spinner("جاري تنقيح الأسلوب..."):
                    res = ask_gemini("أعد كتابة المعالجة التالية لتكون أكثر قوة من الناحية البصرية والتشويق السينمائي.", st.session_state.treatment, gemini_key)
                    st.session_state.treatment = res
                    st.rerun()

# ----------------- 2. تبويب العالم والأصول -----------------
with tab2:
    st.subheader("👥 إدارة الشخصيات (Characters)")
    for i, ch in enumerate(st.session_state.characters):
        with st.expander(f"الشخصية #{i+1}: {ch.get('name', '')}", expanded=True):
            c1, c2 = st.columns([1, 1])
            with c1:
                ch["name"] = st.text_input(f"اسم الشخصية #{i+1}:", value=ch.get("name", ""), key=f"ch_name_{i}")
                ch["role"] = st.text_input(f"دور الشخصية (Role) #{i+1}:", value=ch.get("role", ""), key=f"ch_role_{i}")
            with c2:
                ch["visual"] = st.text_area(f"الوصف البصري والملامح #{i+1}:", value=ch.get("visual", ""), key=f"ch_vis_{i}", height=110)
            
            if st.button(f"🪄 مساعدة AI: توليد ملامح بصرية للشخصية #{i+1}", key=f"btn_ai_ch_{i}"):
                if gemini_key:
                    ch["visual"] = ask_gemini(f"اكتب وصفاً بصرياً دقيقاً بالملامح والملابس لشخصية اسمها {ch['name']} بدور {ch['role']} لتوجيهه لنماذج توليد الصور.", st.session_state.treatment, gemini_key)
                    st.rerun()
    
    col_add_ch, col_del_ch = st.columns(2)
    with col_add_ch:
        if st.button("➕ إضافة شخصية جديدة يدوياً"):
            st.session_state.characters.append({"name": "شخصية جديدة", "role": "دور ثانوي", "visual": ""})
            st.rerun()
    with col_del_ch:
        if len(st.session_state.characters) > 1 and st.button("➖ حذف آخر شخصية"):
            st.session_state.characters.pop()
            st.rerun()

    st.markdown("---")
    st.subheader("🏛️ مواقع التصوير والبيئات (Locations)")
    for j, loc in enumerate(st.session_state.locations):
        with st.expander(f"الموقع #{j+1}: {loc.get('name', '')}", expanded=True):
            loc["name"] = st.text_input(f"اسم الموقع #{j+1}:", value=loc.get("name", ""), key=f"loc_name_{j}")
            loc["setting"] = st.text_area(f"أجواء الموقع والديكور #{j+1}:", value=loc.get("setting", ""), key=f"loc_set_{j}")
            if st.button(f"🪄 مساعدة AI: اقتراح تفاصيل ديكور وإضاءة للموقع #{j+1}", key=f"btn_ai_loc_{j}"):
                if gemini_key:
                    loc["setting"] = ask_gemini(f"اكتب وصفاً بيئياً سينمائياً للديكور والإضاءة لموقع: {loc['name']}.", st.session_state.treatment, gemini_key)
                    st.rerun()

    if st.button("➕ إضافة موقع تصوير جديد يدوياً"):
        st.session_state.locations.append({"name": "موقع جديد", "setting": ""})
        st.rerun()

# ----------------- 3. تبويب لوح وإنتاج (Storyboard & Video) -----------------
with tab3:
    st.subheader("🎬 لوحة القصة والمشاهد (Storyboard)")
    
    for k, sc in enumerate(st.session_state.scenes):
        with st.container():
            st.markdown(f"### 📍 المشهد #{k+1}")
            col_sc1, col_sc2 = st.columns([1, 1])
            with col_sc1:
                sc["location"] = st.text_input(f"الموقع #{k+1}:", value=sc.get("location", ""), key=f"sc_loc_{k}")
                sc["time"] = st.text_input(f"التوقيت / الأجواء #{k+1}:", value=sc.get("time", ""), key=f"sc_time_{k}")
                sc["camera"] = st.text_input(f"حركة وزاوية الكاميرا #{k+1}:", value=sc.get("camera", ""), key=f"sc_cam_{k}")
                sc["dialogue"] = st.text_area(f"نص الراوي أو الحوار #{k+1}:", value=sc.get("dialogue", ""), key=f"sc_dia_{k}", height=90)
            
            with col_sc2:
                sc["prompt"] = st.text_area(f"موجه الذكاء الاصطناعي بالإنجليزية (Video Prompt) #{k+1}:", value=sc.get("prompt", ""), key=f"sc_prm_{k}", height=160)
                if st.button(f"🪄 مساعدة AI: صياغة موجه الفيديو (Prompt Engine) #{k+1}", key=f"btn_ai_prm_{k}"):
                    if gemini_key:
                        sc["prompt"] = ask_gemini(
                            f"قم بصياغة موجه فيديو سينمائي بالإنجليزية (Hyper-realistic cinematic video prompt) للكاميرا {sc['camera']} والموقع {sc['location']} والحوار: {sc['dialogue']}.", 
                            st.session_state.treatment, 
                            gemini_key
                        )
                        st.rerun()
            st.markdown("---")

    col_add_sc, col_del_sc = st.columns(2)
    with col_add_sc:
        if st.button("➕ إضافة مشهد جديد يدوياً"):
            st.session_state.scenes.append({"location": "", "time": "", "camera": "", "dialogue": "", "prompt": ""})
            st.rerun()
    with col_del_sc:
        if len(st.session_state.scenes) > 1 and st.button("➖ حذف آخر مشهد"):
            st.session_state.scenes.pop()
            st.rerun()

    st.markdown("### 🚀 غرفة الإنتاج النهائي (Render Studio)")
    if st.button("🎥 توليد ودمج كافة المشاهد المحددة أعلاه", type="primary", use_container_width=True):
        if not replicate_token:
            st.error("⚠️ يرجى إدخال Replicate API Token في الشريط الجانبي لتوليد الفيديو.")
        else:
            status = st.status("🎬 جاري تحريك المشاهد وإنتاج الصوت...", expanded=True)
            clips = []
            try:
                for idx, scene in enumerate(st.session_state.scenes):
                    status.write(f"🎥 جاري معالجة المشهد #{idx+1}...")
                    v_file = f"render_scene_{idx}.mp4"
                    a_file = f"render_audio_{idx}.mp3"
                    
                    if scene["dialogue"].strip():
                        generate_voiceover(scene["dialogue"], a_file, voice_type)
                    else:
                        generate_voiceover("...", a_file, voice_type)
                        
                    generate_video(scene["prompt"], v_file, replicate_token)
                    
                    v_clip = VideoFileClip(v_file)
                    a_clip = AudioFileClip(a_file)
                    v_clip = v_clip.set_duration(a_clip.duration).set_audio(a_clip)
                    clips.append(v_clip)
                
                status.write("🎞️ دمج الشريط النهائي...")
                final_film = "cinema_production.mp4"
                final = concatenate_videoclips(clips, method="compose")
                final.write_videofile(final_film, fps=24, codec="libx264", audio_codec="aac")
                status.update(label="✅ اكتمل إنتاج الفيلم بنجاح!", state="complete")
                
                st.video(final_film)
                with open(final_film, "rb") as f:
                    st.download_button("📥 تحميل الفيلم النهائي", f, file_name=final_film, mime="video/mp4")
            except Exception as e:
                status.update(label="❌ حدث خطأ أثناء التصيير", state="error")
                st.error(f"تفاصيل الخطأ: {e}")

# ----------------- 4. تبويب أوراق الإنتاج (Call Sheets & Crew) -----------------
with tab4:
    st.subheader("📋 وثائق ومخططات الإنتاج الميداني")
    
    st.session_state.lighting = st.text_area("⚡ مخطط الإضاءة وتوزيع الكشافات:", value=st.session_state.lighting, height=100)
    st.session_state.crew = st.text_area("👥 قائمة طاقم العمل وتوزيع الأدوار:", value=st.session_state.crew, height=100)
    st.session_state.gear = st.text_area("🎥 قائمة الكاميرات والعدسات والمعدات:", value=st.session_state.gear, height=100)
    
    if st.button("🪄 مساعدة AI: اقتراح خطة إنتاج ومعدات متوافقة مع الفيلم"):
        if not gemini_key:
            st.error("أدخل مفتاح Gemini أولاً")
        else:
            with st.spinner("جاري تحليل متطلبات الإنتاج..."):
                st.session_state.lighting = ask_gemini("اقترح توزيع إضاءة احترافي مناسب لهذا الفيلم.", st.session_state.treatment, gemini_key)
                st.session_state.crew = ask_gemini("اقترح قائمة الطاقم الميداني المناسب لإنتاج هذا العمل.", st.session_state.treatment, gemini_key)
                st.session_state.gear = ask_gemini("اقترح أنسب الكاميرات والعدسات والمعدات لتحقيق الطابع البصري للفيلم.", st.session_state.treatment, gemini_key)
                st.rerun()
