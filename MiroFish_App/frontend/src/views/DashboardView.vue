<template>
  <div class="dashboard-grid">
    <LeftPanel />
    <MiddlePanel />
    <RightPanel />
  </div>
</template>

<script setup>
import LeftPanel from '../components/LeftPanel.vue'
import MiddlePanel from '../components/MiddlePanel.vue'
import RightPanel from '../components/RightPanel.vue'
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: 280px 1fr 380px;
  height: 100vh;
  background-color: #1a202c;
  color: #fff;
  overflow: hidden;
}
</style>
