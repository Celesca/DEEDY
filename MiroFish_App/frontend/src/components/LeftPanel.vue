<template>
  <div class="left-panel">
    <h2>Overview</h2>
    <div class="status">
      <p>Round: {{ store.round }}</p>
      <p>Agents: {{ store.activeAgents }}</p>
    </div>
    
    <h3>God Mode Controls</h3>
    <div class="controls">
      <button class="btn primary" @click="injectEvent">Inject Breaking News</button>
      <button class="btn danger" @click="handleStop">Stop Simulation</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useSimulationStore } from '../store'
import { stopSimulation } from '../api/simulation'

const store = useSimulationStore()

onMounted(() => {
  store.startPolling('test-sim-id')
})

onUnmounted(() => {
  store.stopPolling()
})

function injectEvent() {
  store.addFeedItem({ agent: 'GOD', time: new Date().toLocaleTimeString(), content: 'Event Injected! Breaking News.' })
}

async function handleStop() {
  if (store.simulationId) {
    try {
      await stopSimulation({ simulationId: store.simulationId })
      store.addFeedItem({ agent: 'System', time: new Date().toLocaleTimeString(), content: 'Simulation Stopped.' })
      store.stopPolling()
    } catch(e) {
      console.error(e)
    }
  }
}
</script>

<style scoped>
.left-panel {
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.status p { margin: 5px 0; color: #a0aec0; }
.btn {
  width: 100%; padding: 10px; margin-top: 10px;
  border-radius: 8px; border: none; cursor: pointer;
  font-weight: bold;
}
.btn.primary { background: #4fd1c5; color: #1a202c; }
.btn.danger { background: #e53e3e; color: #fff; }
</style>
