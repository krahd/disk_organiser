// Static copy of frontend main.js — keeping app structure but non-functional without backend
/* eslint-env browser */
/* global d3 */
document.addEventListener('DOMContentLoaded', () => {
  const main = document.getElementById('main-content');
  function setSection(title, html) {
    main.innerHTML = `<h2>${title}</h2>` + (html || '');
  }
  document.getElementById('nav-duplicates').addEventListener('click', () => {
    setSection('Duplicate Search', '<p>(Demo) This feature requires the backend API to run.</p>');
  });
  document.getElementById('nav-visualisation').addEventListener('click', () => {
    setSection('Visualisation', '<p>(Demo) Interactive visualisations need the API.</p>');
  });
  document.getElementById('nav-recycle').addEventListener('click', () => setSection('Recycle'));
  document.getElementById('nav-organise').addEventListener('click', () => setSection('Organise'));
  document.getElementById('nav-preferences').addEventListener('click', () => setSection('Preferences'));
});
