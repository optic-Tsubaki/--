# StudyPet AI

StudyPet AI is a Windows desktop companion for learning and focused work.

## V0.1-001 status

The first prototype provides a transparent, borderless, always-on-top pet window.

- Drag the pet with the left mouse button.
- Click it for a greeting.
- Double-click it for the upcoming dashboard hint.
- Right-click it to change its state, hide it, or exit.

Place optional character images in `resources/images/` as `idle.png`, `happy.png`,
`focus.png`, or `sleep.png`. A transparent PNG is recommended. Until images are
provided, StudyPet renders a small built-in starter mascot.

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```
