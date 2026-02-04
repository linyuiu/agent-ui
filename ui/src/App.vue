<template>
  <RouterView />
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');

:global(body) {
  margin: 0;
  min-height: 100vh;
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  background: radial-gradient(70rem 70rem at -10% -10%, #fff0d9 0%, transparent 60%),
    radial-gradient(60rem 60rem at 110% -20%, #d9f3ff 0%, transparent 55%),
    linear-gradient(180deg, #f9fbf7 0%, #eef4f3 100%);
  color: #1c2a2f;
}

:global(#app) {
  min-height: 100vh;
}
</style>
