import os
import time
import requests
import asyncio
import nest_asyncio
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


nest_asyncio.apply()

# ------------------------------------------------------------------------------
# إعدادات مظهر الواجهة (UI Layout)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Cinema Studio",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 أستوديو الأفلام السينمائية بالذكاء الاصطناعي")
st.markdown("حوّل أفكارك وقصصك المكتوبة إلى أفلام وثائقية وسينمائية متحركة بالكامل بضغطة زر واحدة.")

# الشريط الجانبي للإعدادات ومفاتيح المستخدم (Bring Your Own Key أو مفاتيح الأدمن)
with st.sidebar:
    st.header("⚙️ إعدادات الحساب والتشغيل")
    gemini_key = st.text_input("Gemini API Key:", type="password")
    replicate_token = st.text_input("Replicate API Token:", type="password")
    voice_type = st.selectbox(
        "نبرة صوت الراوي:",
        ["ar-SA-HamedNeural", "ar-SA-ShakirNeural", "ar-EG-ShakirNeural"]
    )
    st.markdown("---")
    st.caption("🔒 يتم استخدام المفاتيح لمعالجة طلبك فقط دون تخزينها.")

# ------------------------------------------------------------------------------
# نماذج وهيكلة البيانات
# ------------------------------------------------------------------------------
class Scene(BaseModel):
    scene_number: int
    video_prompt: str
    narration_text: str

class MovieScript(BaseModel):
    title: str
    scenes: list[Scene]

# ------------------------------------------------------------------------------
# الدوال البرمجية الأساسية
# ------------------------------------------------------------------------------
def generate_script(story: str, client: genai.Client) -> MovieScript:
    prompt = f"""
    حول القصة إلى سيناريو فيلم سينمائي من مشهدين متحركين فقط.
    لكل مشهد:
    1. نص الراوي بالعربية الفصحى في narration_text.
    2. وصف فيديو متحرك عالي التفاصيل بالإنجليزية في video_prompt (حدد حركة الكاميرا، العناصر، والإضاءة بدقة).

    القصة:
    {story}
    """
    res = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MovieScript,
            temperature=0.5
        ),
    )
    return MovieScript.model_validate_json(res.text)

async def _async_voice(text: str, filename: str, voice_name: str):
    comm = edge_tts.Communicate(text, voice=voice_name)
    await comm.save(filename)

def generate_voiceover(text: str, filename: str, voice_name: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_async_voice(text, filename, voice_name))

def generate_video(prompt: str, filename: str, token: str):
    os.environ["REPLICATE_API_TOKEN"] = token
    output = replicate.run(
        "minimax/video-01",
        input={"prompt": prompt, "prompt_optimizer": True}
    )
    r = requests.get(str(output))
    with open(filename, "wb") as f:
        f.write(r.content)

# ------------------------------------------------------------------------------
# واجهة إدخال القصة وزر التشغيل
# ------------------------------------------------------------------------------
story_text = st.text_area(
    "اكتب قصتك هنا بالتفصيل:",
    placeholder="في ليلة عاصفة فوق قمة جبلية منعزلة...",
    height=160
)

if st.button("🚀 بدء إنتاج الفيلم الآن", type="primary", use_container_width=True):
    # التحقق من المدخلات
    if not gemini_key or not replicate_token:
        st.error("⚠️ يرجى إدخال مفاتيح الـ API في القائمة الجانبية أولاً.")
    elif not story_text.strip():
        st.warning("⚠️ يرجى كتابة نص القصة قبل بدء الإنتاج.")
    else:
        status = st.status("🎬 جاري العمل على إنتاج الفيلم...", expanded=True)
        progress_bar = st.progress(0)
        
        try:
            # 1. صياغة السيناريو
            status.write("🧠 صياغة السيناريو وتقسيم المشاهد عبر Gemini...")
            client = genai.Client(api_key=gemini_key)
            script = generate_script(story_text, client)
            st.success(f"تم اعتماد الفيلم: «{script.title}»")
            progress_bar.progress(20)

            # 2. توليد المشاهد
            clips = []
            total_scenes = len(script.scenes)
            for i, scene in enumerate(script.scenes):
                idx = scene.scene_number
                status.write(f"🎥 جاري إنتاج لقطات الفيديو والصوت للمشهد ({idx}/{total_scenes})...")
                
                v_file = f"temp_video_{idx}.mp4"
                a_file = f"temp_audio_{idx}.mp3"
                
                generate_voiceover(scene.narration_text, a_file, voice_type)
                generate_video(scene.video_prompt, v_file, replicate_token)
                
                v_clip = VideoFileClip(v_file)
                a_clip = AudioFileClip(a_file)
                v_clip = v_clip.set_duration(a_clip.duration).set_audio(a_clip)
                clips.append(v_clip)
                
                progress_bar.progress(20 + int(60 * ((i + 1) / total_scenes)))

            # 3. المونتاج النهائي
            status.write("🎞️ جاري معالجة ودمج المقطع النهائي...")
            final_output = "generated_cinema.mp4"
            final = concatenate_videoclips(clips, method="compose")
            final.write_videofile(final_output, fps=24, codec="libx264", audio_codec="aac")
            progress_bar.progress(100)
            status.update(label="✅ اكتمل إنتاج الفيلم بنجاح!", state="complete")

            # 4. عرض الفيديو وتوفير زر التنزيل
            st.video(final_output)
            with open(final_output, "rb") as file:
                st.download_button(
                    label="📥 تنزيل الفيلم بجودة عالية",
                    data=file,
                    file_name=final_output,
                    mime="video/mp4",
                    use_container_width=True
                )

        except Exception as e:
            status.update(label="❌ حدث خطأ أثناء الإنتاج", state="error")
            st.error(f"تفاصيل الخطأ: {e}")
            
