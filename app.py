import os
import io
import textwrap
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/dejavu/DejaVuSans.ttf"
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def arabic_text(text):
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def wrap_text(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word
        width = draw.textbbox((0, 0), arabic_text(test), font=fnt)[2]

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def create_tweet(text):
    W, H = 1200, 700

    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    black = (15, 20, 25)
    gray = (83, 100, 113)
    light = (180, 190, 200)

    # X logo
    draw.line((1080, 55, 1125, 100), fill=black, width=8)
    draw.line((1125, 55, 1080, 100), fill=black, width=8)

    # Avatar
    draw.ellipse((60, 45, 140, 125), fill=(35, 45, 55))
    draw.text((100, 85), "A", fill="white",
              font=font(38, True), anchor="mm")

    # Name and username
    draw.text((165, 55), "Ahmed", fill=black, font=font(30, True))
    draw.text((165, 93), "@ahmed", fill=gray, font=font(23))

    # Tweet text
    tweet_font = font(38)
    lines = wrap_text(draw, text, tweet_font, 1060)

    y = 165

    for line in lines[:8]:
        shown = arabic_text(line)

        # Right aligned so Arabic looks natural
        draw.text(
            (1140, y),
            shown,
            fill=black,
            font=tweet_font,
            anchor="ra"
        )

        y += 55

    # Divider
    draw.line((60, 555, 1140, 555), fill=(225, 230, 235), width=2)

    # Tweet actions
    actions = [
        ("♡", 120),
        ("↻", 390),
        ("♡", 660),
        ("↗", 930)
    ]

    for symbol, x in actions:
        draw.text(
            (x, 600),
            symbol,
            fill=gray,
            font=font(32),
            anchor="mm"
        )

    # Mock label
    draw.text(
        (600, 665),
        "Ahmed Tweet Style • Mock",
        fill=light,
        font=font(18),
        anchor="mm"
    )

    output = io.BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return output


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text
        },
        timeout=20
    )


def send_photo(chat_id, image):
    requests.post(
        f"{TELEGRAM_API}/sendPhoto",
        data={
            "chat_id": chat_id,
            "caption": "تم إنشاء التغريدة ✨"
        },
        files={
            "photo": ("tweet.png", image, "image/png")
        },
        timeout=30
    )


@app.route("/", methods=["GET"])
def home():
    return "Ahmed Tweet Style is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return "OK"

    text = message.get("text", "").strip()

    if text.startswith("/start"):
        send_message(
            chat_id,
            "هلا بيك 👋\n\n"
            "أرسل نص التغريدة وأنا أحولها إلى صورة بأسلوب X/Twitter 🐦\n\n"
            "مثال:\n"
            "الهندسة مو بس دراسة، الهندسة حلم."
        )
        return "OK"

    if text.startswith("/help"):
        send_message(
            chat_id,
            "أرسل أي نص هنا وأنا أسويلك منه صورة تغريدة."
        )
        return "OK"

    if text:
        try:
            image = create_tweet(text)
            send_photo(chat_id, image)
        except Exception as e:
            send_message(
                chat_id,
                "صار خطأ أثناء إنشاء الصورة، حاول مرة ثانية."
            )

    return "OK"


def setup_webhook():
    base_url = os.environ.get("RENDER_EXTERNAL_URL")

    if base_url:
        webhook_url = base_url.rstrip("/") + "/webhook"

        try:
            requests.get(
                f"{TELEGRAM_API}/setWebhook",
                params={"url": webhook_url},
                timeout=20
            )
        except Exception:
            pass


setup_webhook()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
