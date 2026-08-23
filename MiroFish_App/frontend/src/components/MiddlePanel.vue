<template>
  <div class="middle-panel">
    <h2>Live Feed</h2>
    <div class="feed-container">
      <transition-group name="list" tag="div" class="feed-list">
        <div v-for="(item, index) in store.feedItems" :key="index" class="feed-item">
          <div class="meta">
            <span class="agent-name">{{ item.agent }}</span>
            <span class="time">{{ item.time }}</span>
          </div>
          <div class="content">{{ item.content }}</div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { useSimulationStore } from '../store'
const store = useSimulationStore()
</script>

<style scoped>
.middle-panel {
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.feed-container {
  flex-grow: 1;
  overflow-y: auto;
  margin-top: 20px;
}
.feed-item {
  background: rgba(0, 0, 0, 0.2);
  padding: 15px;
  border-radius: 12px;
  margin-bottom: 15px;
  border-left: 4px solid #4fd1c5;
}
.meta { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9em; color: #a0aec0; }
.agent-name { font-weight: bold; color: #63b3ed; }
.list-enter-active, .list-leave-active { transition: all 0.5s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateY(-30px); }
</style>
