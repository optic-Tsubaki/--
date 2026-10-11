# StudyPet AI

StudyPet AI is a Windows desktop companion for learning and focused work.

## V0.1-001 status

The first prototype provides a transparent, borderless, always-on-top pet window.

- Drag the pet with the left mouse button.
- Click it for a greeting.
- Double-click it for the upcoming dashboard hint.
- Right-click it to change its state, hide it, or exit.

Place optional character images in `resources/images/` as `idle.png`, `happy.png`,
`focus.png`, or `sleep.png`. For a loop, use ordered frames such as
`idle_01.png`, `idle_02.png`, and `idle_03.png`; the window plays them at roughly
four frames per second. Use transparent PNGs. Until images are provided, StudyPet
renders a small built-in starter mascot.

## Data and AI configuration

StudyPet keeps user-created files outside the application folder so packaging the
app does not put writable data beside the executable. On Windows the application
uses `%LOCALAPPDATA%\\StudyPet\\` for settings, the SQLite database, and logs.

AI provider metadata (provider, base URL, and model) is stored in a JSON settings
file. API keys are deliberately excluded from that file and are stored through
the operating system credential store when AI configuration is added to the UI.
The application remains usable without any AI provider configured.

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```
