<template>
  <div class="right-panel">
    <h2>Analytics</h2>
    <div class="chart-box">
      <h3>Falsification Gap</h3>
      <div class="mock-chart">
        <div class="bar-group" v-for="(data, i) in store.falsificationData" :key="i">
          <div class="label">{{ data.topic }}</div>
          <div class="bars">
            <div class="bar true" :style="{ width: data.trueScore + '%' }"></div>
            <div class="bar expressed" :style="{ width: data.expressedScore + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSimulationStore } from '../store'
const store = useSimulationStore()
</script>

<style scoped>
.right-panel {
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
}
.chart-box {
  background: rgba(0, 0, 0, 0.2);
  padding: 15px;
  border-radius: 12px;
  margin-top: 20px;
}
.bar-group { margin-bottom: 15px; }
.label { font-size: 0.9em; color: #cbd5e0; margin-bottom: 5px; }
.bars { display: flex; flex-direction: column; gap: 5px; }
.bar { height: 12px; border-radius: 6px; }
.bar.true { background: #4fd1c5; }
.bar.expressed { background: #fc8181; }
</style>
