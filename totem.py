from flask import Flask, request, send_file, jsonify
from PIL import Image
import requests
from io import BytesIO
import os

app = Flask(__name__)


# ----------------------------- helpers ----------------------------- #
def fetch_skin(username: str) -> Image.Image:
    url = f"https://mc-heads.net/skin/{username}"
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception("Failed to fetch skin")
    return Image.open(BytesIO(r.content)).convert("RGBA")


def extract_face(skin: Image.Image) -> Image.Image:
    return skin.crop((8, 8, 16, 16)).resize((8, 8), Image.NEAREST)


def extract_torso_pattern(skin: Image.Image) -> Image.Image:
    torso      = skin.crop((20, 20, 28, 32))
    right_arm  = skin.crop((44, 20, 48, 32))
    left_arm   = skin.crop((36, 52, 40, 64))
    right_leg  = skin.crop((4, 20, 8, 32))
    left_leg   = skin.crop((20, 52, 24, 64))

    if all(px[3] == 0 for px in left_arm.getdata()):
        left_arm = right_arm.transpose(Image.FLIP_LEFT_RIGHT)
    if all(px[3] == 0 for px in left_leg.getdata()):
        left_leg = right_leg.transpose(Image.FLIP_LEFT_RIGHT)

    out = Image.new("RGBA", (16, 9), (0, 0, 0, 0))

    for row in range(9):
        if row <= 2:
            torso_row = torso.crop((0, row, 8, row + 1))
            arm_y = 0 if row == 0 else (10 if row == 1 else 11)
            l_arm_px = left_arm.crop((0, arm_y, 4, arm_y + 1)).resize((3, 1), Image.NEAREST)
            r_arm_px = right_arm.crop((0, arm_y, 4, arm_y + 1)).resize((3, 1), Image.NEAREST)
            strip = Image.new("RGBA", (14, 1))
            strip.paste(l_arm_px,  (0, 0))
            strip.paste(torso_row, (3, 0))
            strip.paste(r_arm_px, (11, 0))
            out.paste(strip, (1, row))

        elif row == 3:
            torso_row = torso.crop((0, row, 8, row + 1))
            l_arm_px = left_arm.crop((2, 11, 4, 12)).resize((2, 1), Image.NEAREST)
            r_arm_px = right_arm.crop((0, 11, 2, 12)).resize((2, 1), Image.NEAREST)
            strip = Image.new("RGBA", (12, 1))
            strip.paste(l_arm_px,  (0, 0))
            strip.paste(torso_row, (2, 0))
            strip.paste(r_arm_px, (10, 0))
            out.paste(strip, (2, row))

        elif row == 4:
            torso_row = torso.crop((0, row, 8, row + 1))
            out.paste(torso_row, (4, row))

        elif row in (5, 6):
            leg_row = row - 5
            l_px = left_leg.crop((1, leg_row, 4, leg_row + 1))
            r_px = right_leg.crop((0, leg_row, 3, leg_row + 1))
            strip = Image.new("RGBA", (6, 1))
            strip.paste(l_px, (0, 0))
            strip.paste(r_px, (3, 0))
            out.paste(strip, (5, row))

        elif row == 7:
            leg_row = 10
            l_px = left_leg.crop((1, leg_row, 4, leg_row + 1))
            r_px = right_leg.crop((0, leg_row, 3, leg_row + 1))
            strip = Image.new("RGBA", (6, 1))
            strip.paste(l_px, (0, 0))
            strip.paste(r_px, (3, 0))
            out.paste(strip, (5, row))

        else:
            leg_row = 11
            l_px = left_leg.crop((2, leg_row, 4, leg_row + 1))
            r_px = right_leg.crop((0, leg_row, 2, leg_row + 1))
            strip = Image.new("RGBA", (4, 1))
            strip.paste(l_px, (0, 0))
            strip.paste(r_px, (2, 0))
            out.paste(strip, (6, row))

    return out


def generate_totem(username: str) -> BytesIO:
    skin  = fetch_skin(username)
    face  = extract_face(skin)
    torso = extract_torso_pattern(skin)

    canvas = Image.new("RGBA", (32, 40), (0, 0, 0, 0))
    canvas.paste(torso, (8, 21), torso)
    canvas.paste(face,  (12, 14), face)

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf


# --------------------------- Flask Route --------------------------- #
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify({"error": "Missing 'username' field"}), 400

    try:
        img_bytes = generate_totem(data["username"])
        return send_file(img_bytes, mimetype="image/png", as_attachment=True,
                         download_name=f"totem_{data['username']}.png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------- Run Server ---------------------------- #
if __name__ == "__main__":
    app.run(debug=True)
