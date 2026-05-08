# Dreamwalk — Apocalyptic City (Three.js)

A first-person Three.js dreamscape where you can explore an apocalyptic city `.glb` model. Built with [three.js](https://threejs.org/) and [Vite](https://vitejs.dev/).

![preview](https://img.shields.io/badge/three.js-r165-orange) ![vite](https://img.shields.io/badge/vite-5.x-646CFF)

## Features

- **First-person controls** powered by `PointerLockControls` (mouse-look + WASD).
- **Walking, sprinting, jumping** with gravity and ground raycasting against the city geometry.
- **Toggle flight** (press `F`) to free-fly through the dream when you want to escape gravity.
- **Soft shadows, atmospheric fog, gradient sky, ACES tone mapping** for a moody apocalyptic feel.
- **Loading overlay** with progress bar that downloads the `.glb` before letting you in.
- **HUD** with live mode, speed, and position readout while you explore.
- Auto-centers and scales the loaded city so it always feels human-scale.

## Controls

| Key | Action |
| --- | --- |
| `W` `A` `S` `D` / Arrow keys | Move |
| `Mouse` | Look around |
| `Space` | Jump (or fly up while flying) |
| `Ctrl` | Fly down (while flying) |
| `Shift` | Sprint |
| `F` | Toggle flight mode |
| `R` | Respawn at the spawn point |
| `Esc` | Release the cursor |

## Getting Started

```bash
npm install
npm run dev
```

Then open <http://localhost:5173> and click **Begin Dream** to lock the cursor and start exploring.

### Production build

```bash
npm run build
npm run preview
```

The build is fully static and can be hosted from any static host — drop the contents of `dist/` on Netlify, Vercel, GitHub Pages, S3, etc.

### Lint

```bash
npm run lint
```

## Project Layout

```
.
├── index.html              # Entry HTML with the start overlay + HUD
├── public/
│   └── models/
│       └── apocalyptic_city.glb   # The dream city model
├── src/
│   ├── main.js             # Three.js scene, FPS controls, GLTF loader, movement & collision
│   └── style.css           # Overlay + HUD styling
├── vite.config.js
└── package.json
```

## Swapping in a Different City

Drop any `.glb` into `public/models/` and update the `CITY_URL` constant at the top of `src/main.js`. The loader auto-centers the model and rescales it to roughly human proportions if it's tiny or huge.

## Credits

- City model: provided by the project owner (`apocalyptic_city.glb`).
- Engine: [three.js](https://threejs.org/) by mrdoob & contributors.
