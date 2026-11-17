import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: './',
  plugins: [tailwindcss()],
  build: {
    manifest: 'manifest.json',
    outDir: '../application/static/vite',
    emptyOutDir: true,
    rollupOptions: { input: ['src/tournaments.css', 'src/ratings.css'] },
  },
});
