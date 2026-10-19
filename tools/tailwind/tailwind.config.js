/** Tailwind for the ColdFlow home page only.
 * Utilities are scoped under `.tw` and preflight is off, so they never touch the rest of the site.
 * Rebuild after editing the home templates:
 *   npx tailwindcss@3.4.17 -c tools/tailwind/tailwind.config.js -i tools/tailwind/input.css -o portal/static/css/home.css --minify
 */
module.exports = {
  content: ['./portal/templates/landing.html', './portal/templates/home/**/*.html'],
  important: '.tw',
  corePlugins: { preflight: false },
  theme: { extend: {} },
};
