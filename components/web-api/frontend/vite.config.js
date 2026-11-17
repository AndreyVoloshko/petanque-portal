import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: './',
  plugins: [tailwindcss()],
  build: {
    manifest: 'manifest.json',
    outDir: '../application/static/vite',
    emptyOutDir: true,
    rollupOptions: {
      input: [
        'src/shell.css',
        'src/tournament-badges.css',
        'src/athlete-card.css',
        'src/list-ui.css',
        'src/ratings-foundation.css',
        'src/tournaments.css',
        'src/ratings.css',
      ],
    },
  },
});
