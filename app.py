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

# ضبط واجهة الصفحة بنمط سينمائي عريض
st.set_page_config(
    page_title="AI Cinema Studio Pro",
    page_icon="🎬",
    layout="wide"
)

# ----------------- نماذج البيانات المهيكلة (Pydantic Models) -----------------
class Character(BaseModel):
    name: str
    role: str
    visual_description: str

class Location(BaseModel):
    name: str
    visual_setting: str

class SceneDetail(BaseModel):
    scene_number: int
    location: str
    time_of_day: str
    camera_movement: str
    visual_prompt: str
    narration_or_dialogue: str

class ProductionDoc(BaseModel):
    lighting_setup: str
    crew_list: list[str]
    equipment_needed: list[str]

class CinemaProject(BaseModel):
    movie_title: str
    treatment: str
    characters: list[Character]
    locations: list[Location]
    storyboard: list[SceneDetail]
    production_doc: ProductionDoc

# ----------------- دوال الاتصال بالذكاء الاصطناعي -----------------
def generate_full_production(story: str, client: genai.Client) -> CinemaProject:
    prompt = f"""
    أنت منتج تنفيذي وكاتب سينمائي عالمي. قم بتحويل الفكرة/القصة التالية إلى مشروع إنتاج سينمائي متكامل وعميق:
    1. Treatment: معالجة درامية تسرد ملخص العمل ورؤيته الإخراجية.
    2. Characters: تفاصيل الشخصيات الرئيسية والمظهر البصري الدقيق.
    3. Locations: مواقع التصوير وتفاصيل البيئة والإضاءة.
    4. Storyboard: تفصيل 3 لقطات سينمائية أساسية (مع زاوية الكاميرا ونوع الحركة، موجه فيديو مفصل بالإنجليزية، ونصوص الحوار أو الراوي بالعربية).
    5. ProductionDoc: مقترحات الإضاءة، قائمة الطاقم الأساسي، والمعدات المطلوبة.

    القصة المدخلة:
    {story}
    """
    
    # الاعتماد الحصري على النموذج المعتمد
    target_model = "gemini-3.8-flash"
    
    # محاولة الإرسال حتى 4 مرات في حال واجه السيرفر ضغطاً مؤقتاً (503)
    max_retries = 4
    for attempt in range(max_retries):
        try:
            res = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CinemaProject,
                    temperature=0.6
                ),
            )
            return CinemaProject.model_validate_json(res.text)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))  # انتظار 3 ثوانٍ ثم 6 ثم 9 لتجاوز ذروة الضغط
            else:
                raise e



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

# ----------------- الشريط الجانبي للإعدادات ومفاتيح الـ API -----------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80", use_container_width=True)
    st.title("⚙️ استوديو الإنتاج")
    gemini_key = st.text_input("Gemini API Key:", type="password")
    replicate_token = st.text_input("Replicate API Token:", type="password")
    voice_type = st.selectbox(
        "🎙️ نبرة صوت التعليق / الراوي:",
        ["ar-SA-HamedNeural", "ar-SA-ShakirNeural", "ar-EG-ShakirNeural"]
    )
    st.markdown("---")
    st.caption("✨ نظام إدارة الاستوديوهات السينمائية المستقلة (Virtual Production)")

# تهيئة مساحة التخزين في الجلسة (Session State)
if "project_data" not in st.session_state:
    st.session_state.project_data = None

st.title("🎬 أستوديو صناعة الأفلام السينمائية بالذكاء الاصطناعي")
st.markdown("منظومة إنتاج متكاملة لتوليد المعالجات الدرامية، وتصميم الشخصيات، ولوحات القصة، وإنتاج الفيديو بالكامل.")

# واجهة إدخال الفكرة الرئيسية
story_input = st.text_area(
    "💡 اكتب الفكرة أو القصة أو ملخص المشروع السينمائي:",
    placeholder="اكتب هنا الفكرة بتفاصيلها: الصراع الرئيسي، الأجواء العامة، الحقبة الزمنية...",
    height=120
)

col_run, col_clear = st.columns([4, 1])
with col_run:
    if st.button("⚡ بناء وتطوير المشروع السينمائي بالكامل", type="primary", use_container_width=True):
        if not gemini_key:
            st.error("⚠️ يرجى إدخال مفتاح Gemini API في الشريط الجانبي أولاً.")
        elif not story_input.strip():
            st.warning("⚠️ يرجى كتابة نص الفكرة أولاً.")
        else:
            with st.spinner("🧠 جاري تحضير المعالجة الدرامية، وتصميم الأصول واللوحات عبر الذكاء الاصطناعي..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    st.session_state.project_data = generate_full_production(story_input, client)
                    st.success(f"🎬 تم إعداد المشروع بنجاح: «{st.session_state.project_data.movie_title}»")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء التطوير: {e}")

with col_clear:
    if st.button("🗑️ مسح المشروع", use_container_width=True):
        st.session_state.project_data = None
        st.rerun()

st.markdown("---")

# ----------------- عرض أقسام الإنتاج عبر التبويبات (Tabs) -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "✍️ كتابة وتطوير (Writing)", 
    "🌍 العالم والأصول (Assets)", 
    "🎥 لوح وإنتاج (Storyboard & Production)", 
    "📋 إعداد الأوراق (Call Sheets & Crew)"
])

# 1. تبويب الكتابة والتطوير
with tab1:
    if st.session_state.project_data:
        data = st.session_state.project_data
        st.header(f"🎞️ {data.movie_title}")
        st.subheader("📜 المعالجة الدرامية (Treatment):")
        st.info(data.treatment)
    else:
        st.write("📌 أدخل الفكرة واضغط زر التطوير في الأعلى لظهور المعالجة الدرامية.")

# 2. تبويب العالم والأصول
with tab2:
    if st.session_state.project_data:
        data = st.session_state.project_data
        col_chars, col_locs = st.columns(2)
        
        with col_chars:
            st.subheader("👤 الشخصيات (Characters & Roles):")
            for ch in data.characters:
                with st.expander(f"🎭 {ch.name} - ({ch.role})", expanded=True):
                    st.write(f"**الوصف البصري والملامح:** {ch.visual_description}")
        
        with col_locs:
            st.subheader("📍 مواقع التصوير (Locations & Sets):")
            for loc in data.locations:
                with st.expander(f"🏛️ {loc.name}", expanded=True):
                    st.write(f"**أجواء البيئة:** {loc.visual_setting}")
    else:
        st.write("📌 سيتم بناء بطاقات الممثلين وتفاصيل الديكور هنا فور توليد المشروع.")

# 3. تبويب لوح القصة والتنفيذ البصري
with tab3:
    if st.session_state.project_data:
        data = st.session_state.project_data
        st.subheader("🎬 لوحة القصة وقائمة اللقطات (Storyboard & Shot List)")
        
        for sc in data.storyboard:
            with st.container():
                st.markdown(f"#### 📍 مشهد {sc.scene_number}: في {sc.location} ({sc.time_of_day})")
                col_info, col_prompt = st.columns([1, 1])
                with col_info:
                    st.markdown(f"**🎥 حركة الكاميرا:** `{sc.camera_movement}`")
                    st.markdown(f"**🗣️ الحوار / نص الراوي:**")
                    st.info(sc.narration_or_dialogue)
                with col_prompt:
                    st.markdown("**🪄 موجه توليد الفيديو (Prompt Engine):**")
                    st.code(sc.visual_prompt, language="text")
                st.markdown("---")
        
        st.subheader("🚀 الإنتاج السينمائي والتحريك الفعلي")
        if st.button("🎥 بدء تصيير ودمج الفيلم النهائي عبر Replicate", type="primary"):
            if not replicate_token:
                st.error("⚠️ يرجى إدخال Replicate API Token في الشريط الجانبي.")
            else:
                prod_status = st.status("🎬 جاري العمل على التوليد والتحريك...", expanded=True)
                clips = []
                total = len(data.storyboard)
                
                try:
                    for i, sc in enumerate(data.storyboard):
                        idx = sc.scene_number
                        prod_status.write(f"🎞️ توليد المشهد ({idx}/{total})...")
                        v_file = f"scene_{idx}.mp4"
                        a_file = f"audio_{idx}.mp3"
                        
                        generate_voiceover(sc.narration_or_dialogue, a_file, voice_type)
                        generate_video(sc.visual_prompt, v_file, replicate_token)
                        
                        v_clip = VideoFileClip(v_file)
                        a_clip = AudioFileClip(a_file)
                        v_clip = v_clip.set_duration(a_clip.duration).set_audio(a_clip)
                        clips.append(v_clip)
                    
                    prod_status.write("⚡ دمج المشاهد والمونتاج الصوتي...")
                    final_film = "final_movie.mp4"
                    final = concatenate_videoclips(clips, method="compose")
                    final.write_videofile(final_film, fps=24, codec="libx264", audio_codec="aac")
                    prod_status.update(label="✅ اكتمل الفيلم بنجاح!", state="complete")
                    
                    st.video(final_film)
                    with open(final_film, "rb") as f:
                        st.download_button("📥 تحميل الفيلم بالكامل (MP4)", f, file_name=final_film, mime="video/mp4")
                except Exception as ex:
                    prod_status.update(label="❌ حدث خطأ أثناء التصيير", state="error")
                    st.error(f"تفاصيل الخطأ: {ex}")
    else:
        st.write("📌 لوحة القصة وأزرار تحريك الفيديو ستظهر هنا فور إعداد المشروع.")

# 4. تبويب إعداد الأوراق وتجهيزات الإنتاج
with tab4:
    if st.session_state.project_data:
        doc = st.session_state.project_data.production_doc
        st.subheader("📋 كشف التجهيزات الميدانية والتقنية")
        
        col_light, col_crew, col_gear = st.columns(3)
        with col_light:
            st.markdown("#### ⚡ مخطط الإضاءة المقترح")
            st.write(doc.lighting_setup)
            
        with col_crew:
            st.markdown("#### 👥 قائمة الطاقم المطلوب")
            for member in doc.crew_list:
                st.write(f"- {member}")
                
        with col_gear:
            st.markdown("#### 🎥 قائمة المعدات والكاميرات")
            for gear in doc.equipment_needed:
                st.write(f"- {gear}")
    else:
        st.write("📌 تفاصيل الطاقم ومخططات الإضاءة ستظهر تلقائياً هنا مع كل فيلم.")
