import { defineStore } from 'pinia'
import { getSimulation, getSimulationConfig } from '../api/simulation'
import { getProject } from '../api/graph'

export const useSimulationStore = defineStore('simulation', {
  state: () => ({
    currentStep: 1,
    round: 0,
    activeAgents: 0,
    feedItems: [],
    falsificationData: [],
    simulationId: null,
    pollTimer: null
  }),
  actions: {
    addFeedItem(item) {
      this.feedItems.push(item)
    },
    updateMetrics(metrics) {
      this.falsificationData = metrics
    },
    async startPolling(simId) {
      this.simulationId = simId;
      if (this.pollTimer) clearInterval(this.pollTimer);
      
      this.pollTimer = setInterval(async () => {
        try {
          const simRes = await getSimulation(simId);
          if (simRes.success && simRes.data) {
             this.round = simRes.data.current_round || this.round;
             // mock new feed item
             this.addFeedItem({ agent: 'System', time: new Date().toLocaleTimeString(), content: 'Simulation heartbeat...' });
             
             // mock falsification data
             this.updateMetrics([
               { topic: 'Politics', trueScore: Math.random() * 100, expressedScore: Math.random() * 100 },
               { topic: 'Economy', trueScore: Math.random() * 100, expressedScore: Math.random() * 100 }
             ])
          }
        } catch(e) {
          console.error(e)
        }
      }, 3000)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    }
  }
})
