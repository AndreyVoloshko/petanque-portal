import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  css: {
    preprocessorOptions: {
      scss: {
        quietDeps: true,
        silenceDeprecations: ['import'],
      },
    },
  },
  build: {
    manifest: 'manifest.json',
    outDir: '../application/static/vite',
    emptyOutDir: true,
    rollupOptions: {
      input: [
        'src/bootstrap-theme.scss',
        'src/shell.css',
        'src/tournament-badges.css',
        'src/athlete-card.css',
        'src/list-ui.css',
        'src/filter-bar.css',
        'src/ratings-foundation.css',
        'src/tournaments.css',
        'src/ratings.css',
        'src/clubs.css',
        'src/home.css',
        'src/directories.css',
        'src/documents.css',
        'src/club-profile.css',
        'src/player-profile.css',
        'src/tournament-detail.css',
      ],
    },
  },
});
