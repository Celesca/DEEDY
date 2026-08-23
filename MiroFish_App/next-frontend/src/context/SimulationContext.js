'use client';
import { createContext, useContext, useState, useEffect, useRef } from 'react';

const SimulationContext = createContext();

export function SimulationProvider({ children }) {
  const [state, setState] = useState({ round: 0, population: 0, falsification: [], clusters: [], fear_index: [] });
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isAutoRunning, setIsAutoRunning] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('mirofish_feed');
      if (saved) setFeed(JSON.parse(saved));
    } catch(e) {}
  }, []);

  useEffect(() => {
    if (feed.length > 0) {
      localStorage.setItem('mirofish_feed', JSON.stringify(feed));
    } else {
      localStorage.removeItem('mirofish_feed');
    }
  }, [feed]);

  const fetchState = async () => {
    try {
      const res = await fetch('http://localhost:8000/simulate/state');
      if (res.ok) {
        const data = await res.json();
        setState(prev => ({ 
          ...prev,
          round: data.round, 
          population: data.population,
          falsification: data.falsification_gaps || [],
          clusters: data.clusters || [],
          fear_index: data.fear_index || []
        }));
      }
    } catch (e) {
      console.error('Failed to fetch state:', e);
    }
  };

  const isAutoRunningRef = useRef(isAutoRunning);
  const loadingRef = useRef(loading);
  
  useEffect(() => {
    isAutoRunningRef.current = isAutoRunning;
    loadingRef.current = loading;
  }, [isAutoRunning, loading]);

  useEffect(() => {
    fetchState();
    const interval = setInterval(() => {
      fetchState();
      if (isAutoRunningRef.current && !loadingRef.current) {
        triggerEvent("เวลาผ่านไปตามปกติ (Daily Routine)");
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const triggerEvent = async (description) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/simulate/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, channel: 'โซเชียลมีเดีย', state_threat_level: 50 })
      });
      if (res.ok) {
        const data = await res.json();
        const newFeedItems = data.reactions.map((r, i) => ({
          id: Date.now() + i,
          agent_id: r.agent_id,
          time: new Date().toLocaleTimeString(),
          text: r.public_content ? r.public_content : `(คิดในใจ: ${r.private_opinion?.text || '...'})`,
          isSilent: !r.public_content,
          actionLabel: r.action_label
        }));
        
        setFeed(prev => [...newFeedItems, ...prev].slice(0, 50));
        setState(prev => ({ 
            ...prev,
            round: data.snapshot.round, 
            population: data.snapshot.population,
            falsification: data.snapshot.falsification_gaps || [],
            clusters: data.snapshot.clusters || [],
            fear_index: data.snapshot.fear_index || []
        }));
      }
    } catch (e) {
      console.error('Failed to trigger event:', e);
    } finally {
      setLoading(false);
    }
  };

  const clearFeed = () => setFeed([]);

  const resetSimulation = async () => {
    try {
      await fetch('http://localhost:8000/simulate/reset', { method: 'POST' });
      setFeed([]);
      await fetchState();
    } catch (e) {
      console.error('Failed to reset simulation:', e);
    }
  };

  return (
    <SimulationContext.Provider value={{ state, feed, loading, isAutoRunning, setIsAutoRunning, triggerEvent, clearFeed, resetSimulation }}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  return useContext(SimulationContext);
}
