import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
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
        'src/filter-bar.css',
        'src/ratings-foundation.css',
        'src/tournaments.css',
        'src/ratings.css',
      ],
    },
  },
});
