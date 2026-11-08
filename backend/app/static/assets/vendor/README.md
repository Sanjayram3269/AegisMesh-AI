# Vendored 3D renderer

- Package: `three`, version **0.187.0**.
- Source: https://www.npmjs.com/package/three / https://github.com/mrdoob/three.js
- License: MIT; see `THREE-LICENSE.txt`.
- `three.js` is the package's WebGL module bundled and minified with esbuild, with its public exports preserved. It is served locally; no CDN or external asset fetch is needed at runtime.

Rebuild from an isolated tooling directory:

```bash
npm install three@0.187.0
npx esbuild node_modules/three/build/three.module.js --bundle --minify --format=esm --outfile=three.js
```

The application-specific geometry and interaction code lives in `../agent-scene.js`. No third-party character or image assets are used.
