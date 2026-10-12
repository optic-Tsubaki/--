import math
import sys
from pathlib import Path

from PIL import Image
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pet.pet_controller import PetState
from pet.pet_window import PetWindow


app = QApplication([])
pet = PetWindow()
pet._apply_state(PetState.CELEBRATE)
frames: list[Image.Image] = []

for index in range(16):
    pet._idle_phase = index * math.tau / 16
    image = QImage(pet.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    pet.render(painter)
    painter.end()
    buffer = image.bits()
    buffer.setsize(image.sizeInBytes())
    frames.append(
        Image.frombytes(
            "RGBA", (image.width(), image.height()), bytes(buffer), "raw", "BGRA"
        )
    )

frames[0].save(
    "tmp/happy_celebration.gif",
    save_all=True,
    append_images=frames[1:],
    duration=70,
    loop=0,
    disposal=2,
)
print(f"gif-export-ok: {len(frames)} frames")
