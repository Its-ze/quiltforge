# QuiltForge — Barn Quilt Studio

QuiltForge is an offline Windows application that turns photographs into geometric, paintable barn quilt patterns.

## Features

- Welcome screen with recent projects and one-click project creation
- Local project library with autosave
- Blocks, triangles, and classic diamond/star geometry
- Adjustable 4×4 through 24×24 grids and 2–12 paint colors
- Click-to-repaint editing and whole-palette color replacement
- Board size, grid-line, and paint-number controls
- High-resolution PNG, editable SVG, and printable PDF build guides
- Built-in How To and About sections
- No account, cloud upload, or internet connection required

## Development

```powershell
.\.venv\Scripts\python.exe -m quiltforge
.\.venv\Scripts\python.exe -m pytest -q
```

Build the complete Windows release with:

```powershell
.\scripts\build-release.ps1
```

The build script creates `dist\QuiltForge-Setup-1.0.0.exe` and a portable ZIP. Inno Setup 6 is required for the installer.

## Privacy

Source images and projects remain on the user's computer under `%LOCALAPPDATA%\QuiltForge\Projects`.

## Credits

Made by Zach Skeens, in partnership with ITSZ Studios, and maintained by ITSolutions.Digital.

