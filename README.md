# SAS-ZA4Tool

Save file editor for SAS: Zombie Assault 4 by Ninja Kiwi, written in Python.

Discord: https://discord.gg/WMNxT2v7vw

---

## Quick Start (Recommended for Most Users)

If you just want to use the editor without installing Python:

1. Go to the Releases page.
2. Download the latest precompiled SASZA4Tool.exe.
3. Run the executable.
   Note: Your browser or Windows might flag it as unrecognized since it is an unsigned tool. You may need to click "Run anyway".

*Note on compilation: The binary releases are compiled using Nuitka. Nuitka is only required by developers to compile the project to an executable, and is not needed to run the tool.*

---

## Running from Source (For Developers)

If you prefer to run the script directly using Python:

### Prerequisites
- Python 3.10 or higher.
- Steam version of SAS: Zombie Assault 4 installed.

### Installation and Usage
1. Clone the repository:
   ```bash
   git clone https://github.com/dstvx/SAS-ZA4Tool.git
   cd SAS-ZA4Tool
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the editor:
   ```bash
   python main.py
   ```

---

## Important Notes
- Backup your save: Always keep a copy of your Profile.save before making changes.
- Steam Cloud: If Steam Cloud is active, it might overwrite your changes. It is recommended to edit while the game is closed.
- Game Launching: Launching the game through the tool only works correctly if the game is currently on the main menu screen.

---

**Made by: dstvx**
