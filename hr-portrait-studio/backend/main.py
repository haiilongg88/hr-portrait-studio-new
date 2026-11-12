import base64, io, os
from pathlib import Path
from typing import Literal
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_BYTES = MAX_MB * 1024 * 1024
MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
PASSWORD = os.getenv("APP_ACCESS_PASSWORD", "")

app = FastAPI(title="HR Portrait Studio", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-App-Password"])

OUTFITS = {
    "thaco": "Dress the person in a neat pale cream/light-yellow THACO-style uniform shirt: traditional pointed collar, subtle blue inner-collar trim, and one small blue lowercase 'i' emblem on the wearer's left chest. Keep it pressed and understated. Do not add large text, extra logos, badges, tie, or jacket.",
    "white": "Dress the person in a plain crisp pure-white long-sleeved button-up shirt, traditional pointed collar slightly open at the neck, and white buttons. No logo, emblem, text, tie, vest, or jacket. Keep it professional and pressed."
}
BASE_PROMPT = """Perform a careful photorealistic professional portrait-photo edit using the uploaded photograph as the sole identity reference.

IDENTITY PRESERVATION IS THE HIGHEST PRIORITY:
- Keep the exact same person and recognizable identity. Preserve facial geometry, eyes, eyebrows, nose, lips, ears, jawline, cheeks, skin tone, age, hairstyle, hairline, glasses if present, facial hair if present, and expression.
- Do not beautify, de-age, slim the face, change facial proportions, remove glasses, add makeup, or smooth skin unnaturally.
- Do not replace the person with a lookalike. Keep the original head angle and natural body proportions as closely as possible.

EDIT ONLY CLOTHING, BACKDROP, AND PROFESSIONAL PHOTO FRAMING:
{outfit}

PHOTO REQUIREMENTS:
- One person only, centered and facing the camera.
- Professional Vietnamese ID/profile portrait, head and shoulders with upper chest visible.
- Pure clean white background (#FFFFFF), evenly lit, no texture, objects, text, watermark, or decorative elements.
- Soft even natural studio lighting and realistic skin texture.
- Keep the entire top of the hair visible with modest space above the head; both shoulders visible.
- Portrait aspect ratio 3:4. Real studio photograph, not illustration or AI art.
- Do not add props or a second person. If the original already has a white background or suitable lighting, preserve it.
""".format


def require_password(value):
    if PASSWORD and value != PASSWORD:
        raise HTTPException(status_code=401, detail="Mật khẩu truy cập không đúng.")


def normalize_image(raw):
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
        if im.width < 160 or im.height < 160:
            raise HTTPException(400, "Ảnh quá nhỏ. Vui lòng chọn ảnh rõ hơn.")
        im.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
        im = im.convert("RGB")
        out = io.BytesIO(); im.save(out, "PNG", optimize=True)
        return out.getvalue()
    except UnidentifiedImageError:
        raise HTTPException(400, "Tệp không phải ảnh JPG, PNG hoặc WEBP hợp lệ.")


def normalize_3x4(raw_png):
    im = Image.open(io.BytesIO(raw_png)).convert("RGB")
    im = ImageOps.fit(im, (354, 472), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    out = io.BytesIO(); im.save(out, "PNG", dpi=(300, 300), optimize=True)
    return out.getvalue()


async def edit_image(image_png, outfit):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Website chưa được cấu hình OPENAI_API_KEY. Hãy thêm API key ở phần Secrets/Environment.")
    prompt = BASE_PROMPT(outfit=OUTFITS[outfit])
    files = [("image[]", ("portrait.png", image_png, "image/png"))]
    data = {"model": MODEL, "prompt": prompt, "size": "1152x1536", "quality": "high", "output_format": "png", "n": "1"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(240.0, connect=30.0)) as client:
            res = await client.post("https://api.openai.com/v1/images/edits", headers={"Authorization": f"Bearer {key}"}, data=data, files=files)
        if res.status_code >= 400:
            try: msg = res.json().get("error", {}).get("message", "OpenAI Image API trả về lỗi.")
            except Exception: msg = "OpenAI Image API trả về lỗi."
            raise HTTPException(502, msg[:700])
        b64 = res.json().get("data", [{}])[0].get("b64_json")
        if not b64: raise HTTPException(502, "API không trả về ảnh kết quả.")
        return base64.b64decode(b64)
    except httpx.TimeoutException:
        raise HTTPException(504, "Xử lý ảnh quá thời gian chờ. Vui lòng thử lại.")
    except httpx.HTTPError:
        raise HTTPException(502, "Không thể kết nối dịch vụ xử lý ảnh.")


@app.get("/api/health")
async def health(): return {"status": "ok"}

@app.get("/api/config")
async def config(): return {"auth_required": bool(PASSWORD), "max_upload_mb": MAX_MB}

@app.post("/api/process")
async def process(image: UploadFile = File(...), outfit: Literal["thaco", "white"] = Form(...), x_app_password: str | None = Header(default=None)):
    require_password(x_app_password)
    if (image.content_type or "").lower() not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.")
    raw = await image.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES: raise HTTPException(413, f"Mỗi ảnh tối đa {MAX_MB} MB.")
    if not raw: raise HTTPException(400, "Tệp ảnh đang trống.")
    normalized = normalize_image(raw)
    edited = await edit_image(normalized, outfit)
    final = normalize_3x4(edited)
    return Response(final, media_type="image/png", headers={"Content-Disposition": 'inline; filename="portrait_3x4.png"'})

app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
