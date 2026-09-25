import os
import json
import time
import requests
import asyncio
import streamlit as st
from google import genai
from google.genai import types
import replicate
import edge_tts

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip

st.set_page_config(
    page_title="AI Cinema Studio Pro Max",
    page_icon="🎬",
    layout="wide"
)

# ----------------- وظائف الذكاء الاصطناعي والصوتيات -----------------
def ask_gemini(instruction: str, context: str, gemini_key: str) -> str:
    client = genai.Client(api_key=gemini_key)
    prompt = f"{instruction}\n\nالسياق:\n{context}"
    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            return res.text.strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
            else:
                return f"خطأ: {e}"

def generate_image(prompt: str, token: str) -> str:
    """توليد صورة فوتوغرافية ومفهوم بصري عبر Flux Schnell"""
    os.environ["REPLICATE_API_TOKEN"] = token
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={"prompt": prompt, "aspect_ratio": "16:9"}
    )
    if isinstance(output, list) and len(output) > 0:
        return str(output[0])
    return str(output)

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

# ----------------- تهيئة ذاكرة الجلسة التفاعلية ونظام الرصيد -----------------
if "credits" not in st.session_state:
    st.session_state.credits = 220000  # رصيد الاستوديو الافتراضي

if "project_title" not in st.session_state:
    st.session_state.project_title = "التحول من ضعيف إلى قاتل الشياطين"

if "treatment" not in st.session_state:
    st.session_state.treatment = ""

if "characters" not in st.session_state:
    st.session_state.characters = [
        {
            "name": "ريان",
            "role": "قاتل الشياطين",
            "visual": "شاب في أوائل العشرينيات، شعر أسود مموج، عينان عنبريتان، يحمل سيفاً فولاذياً أسود محفوراً بلهب أحمر متوهج، جروح تدريب على ذراعيه، درع كتف خفيف.",
            "image_url": ""
        }
    ]

if "locations" not in st.session_state:
    st.session_state.locations = [
        {
            "name": "القرية المحترقة",
            "setting": "أطلال قرية جبلية منكوبة تغطيها طبقات من الرماد ودخان النيران البرتقالية المشتعلة، ليل بارد مظلم.",
            "image_url": ""
        }
    ]

if "scenes" not in st.session_state:
    st.session_state.scenes = [
        {
            "location": "أطلال القرية",
            "time": "ليل / رماد ونيران",
            "camera": "Low-angle slow dolly in",
            "dialogue": "حين سلب الظلام كل ما أملك، لم يعد في هذا الجسد الضعيف مكان للخوف بل قسم محفور بالنار.",
            "voice": "ar-SA-HamedNeural",
            "prompt": "Cinematic 8k, low-angle slow dolly in, a slender young man kneeling amidst the smoldering ash of a burned fantasy village, floating glowing embers, dark blue night atmosphere contrasted with warm orange fires, tears evaporating on soot-covered face, 35mm film grain, hyper-realistic, dramatic lighting."
        }
    ]

if "lighting" not in st.session_state:
    st.session_state.lighting = "إضاءة نيران محايدة 2800K مع أضواء حافة زرقاء 5600K في الخلفية."
if "crew" not in st.session_state:
    st.session_state.crew = "مخرج، مدير تصوير، مصمم معارك، مهندس مؤثرات خاصة."
if "gear" not in st.session_state:
    st.session_state.gear = "كاميرا سينمائية عريضة، عدسات أنامورفيك، مثبت حركة Ronin."

# ----------------- الشريط الجانبي للإعدادات والرصيد -----------------
with st.sidebar:
    st.title("⚙️ استوديو الإنتاج السينمائي")
    
    # عداد الرصيد التجاري
    st.metric(label="💎 رصيد الاستوديو المتبقي:", value=f"{st.session_state.credits:,} نقطة")
    
    gemini_key = st.text_input("Gemini API Key:", type="password")
    replicate_token = st.text_input("Replicate API Token:", type="password")
    
    st.markdown("---")
    st.subheader("💾 إدارة وحفظ المشروع")
    
    # تصدير المشروع كـ JSON
    current_data = {
        "title": st.session_state.project_title,
        "treatment": st.session_state.treatment,
        "characters": st.session_state.characters,
        "locations": st.session_state.locations,
        "scenes": st.session_state.scenes,
        "lighting": st.session_state.lighting,
        "crew": st.session_state.crew,
        "gear": st.session_state.gear
    }
    st.download_button(
        "💾 تصدير المشروع (JSON)",
        data=json.dumps(current_data, ensure_ascii=False, indent=2),
        file_name="cinema_project.json",
        mime="application/json",
        use_container_width=True
    )
    
    # استرجاع المشروع المرفوع
    uploaded_file = st.file_uploader("📂 استيراد مشروع سابق:", type=["json"])
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            st.session_state.project_title = loaded_data.get("title", st.session_state.project_title)
            st.session_state.treatment = loaded_data.get("treatment", st.session_state.treatment)
            st.session_state.characters = loaded_data.get("characters", st.session_state.characters)
            st.session_state.locations = loaded_data.get("locations", st.session_state.locations)
            st.session_state.scenes = loaded_data.get("scenes", st.session_state.scenes)
            st.session_state.lighting = loaded_data.get("lighting", st.session_state.lighting)
            st.session_state.crew = loaded_data.get("crew", st.session_state.crew)
            st.session_state.gear = loaded_data.get("gear", st.session_state.gear)
            st.success("تم استيراد المشروع بنجاح!")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

st.title("🎬 استوديو الأفلام السينمائية الاحترافي (Studio Pro)")

col_title, col_ai_title = st.columns([3, 1])
with col_title:
    st.session_state.project_title = st.text_input("📽️ اسم الفيلم / المشروع:", value=st.session_state.project_title)
with col_ai_title:
    if st.button("🪄 اقتراح عنوان سينمائي"):
        if gemini_key:
            sug = ask_gemini("اقترح عنواناً سينمائياً ملحمياً ومختصراً لهذا الفيلم.", st.session_state.treatment, gemini_key)
            st.session_state.project_title = sug.replace('"', '').strip()
            st.session_state.credits -= 50
            st.rerun()

# التبويبات الأربعة الموسعة
tab1, tab2, tab3, tab4 = st.tabs([
    "✍️ كتابة وتطوير", 
    "🌍 العالم والأصول (Concept Art)", 
    "🎥 لوح وإنتاج (Sound & Render)", 
    "📋 أوراق الإنتاج (Call Sheets)"
])

# ----------------- 1. تبويب كتابة وتطوير -----------------
with tab1:
    st.subheader("📜 المعالجة الدرامية الكاملة (Treatment)")
    st.session_state.treatment = st.text_area(
        "نص المعالجة الدرامية والأحداث:",
        value=st.session_state.treatment,
        height=180
    )
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("🪄 مساعدة AI: توليد معالجة متكاملة"):
            if gemini_key:
                with st.spinner("جاري صياغة القصة..."):
                    st.session_state.treatment = ask_gemini("قم بصياغة معالجة درامية سينمائية قوية تشمل البداية، نقطة التحول، والذروة.", st.session_state.project_title, gemini_key)
                    st.session_state.credits -= 150
                    st.rerun()
    with col_w2:
        if st.button("✨ مساعدة AI: تعزيز الطابع البصري"):
            if gemini_key and st.session_state.treatment:
                with st.spinner("جاري تنقيح المعالجة..."):
                    st.session_state.treatment = ask_gemini("أعد كتابة هذه المعالجة بأسلوب إخراجي سينمائي عالي الجاذبية.", st.session_state.treatment, gemini_key)
                    st.session_state.credits -= 100
                    st.rerun()

# ----------------- 2. تبويب العالم والأصول -----------------
with tab2:
    st.subheader("👥 بطاقات الشخصيات والرؤية البصرية (Character Art)")
    for i, ch in enumerate(st.session_state.characters):
        with st.expander(f"الشخصية #{i+1}: {ch.get('name', '')}", expanded=True):
            col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
            with col_c1:
                ch["name"] = st.text_input(f"الاسم #{i+1}:", value=ch.get("name", ""), key=f"c_n_{i}")
                ch["role"] = st.text_input(f"الدور #{i+1}:", value=ch.get("role", ""), key=f"c_r_{i}")
                if st.button(f"🪄 مساعدة AI للمظهر #{i+1}", key=f"btn_c_ai_{i}"):
                    if gemini_key:
                        ch["visual"] = ask_gemini(f"اكتب وصفاً بصرياً دقيقاً بالملامح واللباس لشخصية {ch['name']} بدور {ch['role']}.", st.session_state.treatment, gemini_key)
                        st.session_state.credits -= 50
                        st.rerun()
            with col_c2:
                ch["visual"] = st.text_area(f"الوصف البصري #{i+1}:", value=ch.get("visual", ""), key=f"c_v_{i}", height=120)
                if st.button(f"🎨 توليد صورة المظهر (Concept Art) #{i+1}", key=f"btn_img_c_{i}"):
                    if replicate_token:
                        with st.spinner("جاري إنشاء صورة الشخصية عبر Flux..."):
                            prompt_img = f"Cinematic concept art portrait, {ch['visual']}, 8k, detailed character design, dramatic film lighting"
                            ch["image_url"] = generate_image(prompt_img, replicate_token)
                            st.session_state.credits -= 500
                            st.rerun()
                    else:
                        st.error("أدخل Replicate Token أولاً")
            with col_c3:
                if ch.get("image_url"):
                    st.image(ch["image_url"], caption=f"المظهر البصري لـ {ch['name']}", use_container_width=True)
                else:
                    st.info("لم يتم توليد صورة للشخصية بعد.")

    if st.button("➕ إضافة شخصية جديدة"):
        st.session_state.characters.append({"name": "شخصية جديدة", "role": "", "visual": "", "image_url": ""})
        st.rerun()

    st.markdown("---")
    st.subheader("🏛️ مواقع التصوير والبيئات (Location Art)")
    for j, loc in enumerate(st.session_state.locations):
        with st.expander(f"الموقع #{j+1}: {loc.get('name', '')}", expanded=True):
            col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
            with col_l1:
                loc["name"] = st.text_input(f"اسم الموقع #{j+1}:", value=loc.get("name", ""), key=f"l_n_{j}")
                if st.button(f"🪄 مساعدة AI للأجواء #{j+1}", key=f"btn_l_ai_{j}"):
                    if gemini_key:
                        loc["setting"] = ask_gemini(f"اكتب وصفاً بيئياً سينمائياً للديكور والإضاءة لموقع: {loc['name']}.", st.session_state.treatment, gemini_key)
                        st.session_state.credits -= 50
                        st.rerun()
            with col_l2:
                loc["setting"] = st.text_area(f"الوصف البيئي #{j+1}:", value=loc.get("setting", ""), key=f"l_s_{j}", height=120)
                if st.button(f"🎨 توليد صورة البيئة (Set Concept) #{j+1}", key=f"btn_img_l_{j}"):
                    if replicate_token:
                        with st.spinner("جاري إنشاء بيئة الموقع..."):
                            prompt_loc = f"Cinematic wide establishing shot of {loc['setting']}, 8k, photorealistic environment, masterpiece lighting"
                            loc["image_url"] = generate_image(prompt_loc, replicate_token)
                            st.session_state.credits -= 500
                            st.rerun()
                    else:
                        st.error("أدخل Replicate Token أولاً")
            with col_l3:
                if loc.get("image_url"):
                    st.image(loc["image_url"], caption=f"أجواء {loc['name']}", use_container_width=True)
                else:
                    st.info("لم يتم توليد صورة للموقع بعد.")

    if st.button("➕ إضافة موقع تصوير جديد"):
        st.session_state.locations.append({"name": "موقع جديد", "setting": "", "image_url": ""})
        st.rerun()

# ----------------- 3. تبويب لوح وإنتاج -----------------
with tab3:
    st.subheader("🎬 لوحة القصة والمشاهد (Storyboard)")
    
    voices_available = ["ar-SA-HamedNeural", "ar-SA-ShakirNeural", "ar-EG-ShakirNeural", "ar-AE-HamdanNeural"]
    
    for k, sc in enumerate(st.session_state.scenes):
        with st.container():
            st.markdown(f"### 📍 المشهد #{k+1}")
            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                sc["location"] = st.text_input(f"الموقع #{k+1}:", value=sc.get("location", ""), key=f"s_loc_{k}")
                sc["camera"] = st.text_input(f"حركة الكاميرا #{k+1}:", value=sc.get("camera", ""), key=f"s_cam_{k}")
                sc["voice"] = st.selectbox(f"🎙️ نبرة صوت المشهد #{k+1}:", voices_available, index=0, key=f"s_vc_{k}")
                sc["dialogue"] = st.text_area(f"نص الحوار أو الراوي #{k+1}:", value=sc.get("dialogue", ""), key=f"s_dia_{k}", height=80)
            with col_s2:
                sc["prompt"] = st.text_area(f"موجه تحريك الفيديو (Video Prompt) #{k+1}:", value=sc.get("prompt", ""), key=f"s_prm_{k}", height=140)
                if st.button(f"🪄 صياغة موجه الفيديو بالإنجليزية #{k+1}", key=f"btn_prm_{k}"):
                    if gemini_key:
                        sc["prompt"] = ask_gemini(f"اكتب برومبت سينمائي بالإنجليزية فائق الدقة (Hyper-realistic 8k) لكاميرا {sc['camera']} وموقع {sc['location']} وحوار: {sc['dialogue']}", st.session_state.treatment, gemini_key)
                        st.session_state.credits -= 50
                        st.rerun()
            st.markdown("---")

    col_add_sc, col_del_sc = st.columns(2)
    with col_add_sc:
        if st.button("➕ إضافة مشهد جديد"):
            st.session_state.scenes.append({"location": "", "camera": "", "voice": "ar-SA-HamedNeural", "dialogue": "", "prompt": ""})
            st.rerun()
    with col_del_sc:
        if len(st.session_state.scenes) > 1 and st.button("➖ حذف المشهد الأخير"):
            st.session_state.scenes.pop()
            st.rerun()

    st.markdown("### 🚀 استوديو الإنتاج الصوتي والتصيير النهائي")
    if st.button("🎥 بدء إنتاج الفيلم المدمج (فيديو + تعليق + مؤثرات)", type="primary", use_container_width=True):
        if not replicate_token:
            st.error("⚠️ يرجى إدخال Replicate API Token في الشريط الجانبي.")
        else:
            status = st.status("🎬 جاري تصيير المشاهد الصوتية والبصرية...", expanded=True)
            clips = []
            try:
                for idx, scene in enumerate(st.session_state.scenes):
                    status.write(f"🎥 جاري معالجة المشهد #{idx+1}...")
                    v_file = f"sc_{idx}.mp4"
                    a_file = f"au_{idx}.mp3"
                    
                    dialogue_text = scene["dialogue"].strip() if scene.get("dialogue") else "..."
                    generate_voiceover(dialogue_text, a_file, scene.get("voice", "ar-SA-HamedNeural"))
                    generate_video(scene["prompt"], v_file, replicate_token)
                    
                    v_clip = VideoFileClip(v_file)
                    a_clip = AudioFileClip(a_file)
                    
                    # التوافق الكامل مع إصدارات MoviePy الحديثة
                    if hasattr(v_clip, "with_duration"):
                        v_clip = v_clip.with_duration(a_clip.duration).with_audio(a_clip)
                    else:
                        v_clip = v_clip.set_duration(a_clip.duration).set_audio(a_clip)
                        
                    clips.append(v_clip)
                    st.session_state.credits -= 3000
                
                status.write("🎞️ دمج الشريط النهائي وتصدير الفيديو...")
                final_film = "cinema_production_pro.mp4"
                final = concatenate_videoclips(clips, method="compose")
                final.write_videofile(final_film, fps=24, codec="libx264", audio_codec="aac")
                status.update(label="✅ تم اكتمال إنتاج الفيلم بالكامل!", state="complete")
                
                st.video(final_film)
                with open(final_film, "rb") as f:
                    st.download_button("📥 تحميل الفيلم النهائي (MP4)", f, file_name=final_film, mime="video/mp4")
            except Exception as e:
                status.update(label="❌ حدث خطأ أثناء التصيير", state="error")
                st.error(f"تفاصيل الخطأ: {e}")

# ----------------- 4. تبويب أوراق الإنتاج -----------------
with tab4:
    st.subheader("📋 وثائق ومخططات الإنتاج (Call Sheets & Pitch Deck)")
    
    st.session_state.lighting = st.text_area("⚡ مخطط الإضاءة الميدانية:", value=st.session_state.lighting, height=90)
    st.session_state.crew = st.text_area("👥 قائمة الطاقم الميداني:", value=st.session_state.crew, height=90)
    st.session_state.gear = st.text_area("🎥 قائمة المعدات والكاميرات:", value=st.session_state.gear, height=90)
    
    col_ai_doc, col_down_doc = st.columns(2)
    with col_ai_doc:
        if st.button("🪄 مساعدة AI: توليد خطة العمل الميدانية"):
            if gemini_key:
                with st.spinner("جاري صياغة مستندات الإنتاج..."):
                    st.session_state.lighting = ask_gemini("اقترح توزيع إضاءة سينمائي لهذا العمل.", st.session_state.treatment, gemini_key)
                    st.session_state.crew = ask_gemini("اقترح قائمة الطاقم السينمائي المطلوب.", st.session_state.treatment, gemini_key)
                    st.session_state.gear = ask_gemini("اقترح أفضل الكاميرات والعدسات المناسبة لهذا الطابع.", st.session_state.treatment, gemini_key)
                    st.session_state.credits -= 100
                    st.rerun()
    with col_down_doc:
        # تصدير كشف الإنتاج كنص رسمي
        call_sheet_content = f"""
=====================================================
مستند الإنتاج السينمائي الرسمي (CINEMA PRODUCTION SHEET)
=====================================================
عنوان العمل: {st.session_state.project_title}
المعالجة الدرامية:
{st.session_state.treatment}

-----------------------------------------------------
1. مخطط الإضاءة وتوزيع الكشافات:
{st.session_state.lighting}

2. طاقم العمل وتوزيع المهام:
{st.session_state.crew}

3. المعدات والكاميرات المطلوبة:
{st.session_state.gear}
=====================================================
تم التوليد عبر استوديو AI Cinema Pro
        """
        st.download_button(
            "📄 تنزيل كشف الإنتاج الرسمي (Call Sheet)",
            data=call_sheet_content,
            file_name="Call_Sheet_Production.txt",
            mime="text/plain",
            use_container_width=True
        )
