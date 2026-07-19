import React, { useState, useEffect } from 'react';

export default function ClewMobileApp() {
  const [tasks, setTasks] = useState([]);
  const [chatLogs, setChatLogs] = useState([]);
  const [filter, setFilter] = useState('active');
  const [isMicActive, setIsMicActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [tasksRes, chatRes] = await Promise.all([
        fetch('/api/tasks'),
        fetch('/api/chat')
      ]);
      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        setTasks(tasksData);
      }
      if (chatRes.ok) {
        const chatData = await chatRes.json();
        setChatLogs(chatData);
      }
    } catch (err) {
      console.error('Error fetching Clew mobile data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (taskId, newStatus) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error('Error updating task status:', err);
    }
  };

  const handleAddTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTaskTitle, priority: 'P2', energy_level: 'medium' })
      });
      if (res.ok) {
        setNewTaskTitle('');
        setShowAddModal(false);
        fetchData();
      }
    } catch (err) {
      console.error('Error adding task:', err);
    }
  };

  const toggleVoiceNode = async () => {
    if (!isMicActive) {
      try {
        const res = await fetch('/api/livekit/token', { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          console.log('LiveKit session connected:', data);
          setIsMicActive(true);
        }
      } catch (err) {
        console.error('Failed to trigger LiveKit WebRTC session:', err);
      }
    } else {
      setIsMicActive(false);
    }
  };

  const filteredTasks = tasks.filter(t => {
    if (filter === 'active') return t.status === 'pending' || t.status === 'in_progress';
    if (filter === 'completed') return t.status === 'completed';
    return true;
  });

  return (
    <div style={styles.container}>
      {/* Mobile Header */}
      <header style={styles.header}>
        <div style={styles.headerTitle}>⚡ Clew Mobile Hub</div>
        <div style={styles.headerSubtitle}>Day-at-a-Glance & Voice Node</div>
      </header>

      {/* Task Filters */}
      <div style={styles.filterBar}>
        {['active', 'all', 'completed'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              ...styles.filterBtn,
              ...(filter === f ? styles.activeFilterBtn : {})
            }}
          >
            {f.toUpperCase()}
          </button>
        ))}
        <button onClick={() => setShowAddModal(true)} style={styles.addBtn}>
          + Task
        </button>
      </div>

      {/* Day at a Glance Task List */}
      <main style={styles.mainContent}>
        <h3 style={styles.sectionTitle}>Day-at-a-Glance Tasks</h3>
        {loading ? (
          <div style={styles.loadingText}>Syncing working state...</div>
        ) : filteredTasks.length === 0 ? (
          <div style={styles.emptyCard}>No tasks found for current view.</div>
        ) : (
          filteredTasks.map(task => (
            <div key={task.id} style={styles.taskCard}>
              <div style={styles.taskHeader}>
                <span style={styles.taskTitle}>{task.title}</span>
                <span style={styles.badge(task.priority)}>P{task.priority || 2}</span>
              </div>
              <div style={styles.taskMeta}>
                <span>⚡ Energy: {task.energy_level || 'medium'}</span>
                <span style={styles.statusLabel(task.status)}>{task.status.toUpperCase()}</span>
              </div>
              <div style={styles.actionRow}>
                {task.status !== 'completed' && (
                  <button
                    onClick={() => handleUpdateStatus(task.id, 'completed')}
                    style={styles.doneBtn}
                  >
                    ✓ Complete
                  </button>
                )}
                {task.status === 'pending' && (
                  <button
                    onClick={() => handleUpdateStatus(task.id, 'in_progress')}
                    style={styles.startBtn}
                  >
                    ▶ Start Focus
                  </button>
                )}
                {task.status !== 'completed' && (
                  <button
                    onClick={() => handleUpdateStatus(task.id, 'deferred')}
                    style={styles.deferBtn}
                  >
                    ⏸ Defer
                  </button>
                )}
              </div>
            </div>
          ))
        )}

        {/* Timeline Log Snippet */}
        <h3 style={{ ...styles.sectionTitle, marginTop: '24px' }}>Voice & Chat Activity</h3>
        <div style={styles.timelineBox}>
          {chatLogs.slice(0, 5).map((log, idx) => (
            <div key={idx} style={styles.chatEntry}>
              <span style={styles.speakerIcon}>
                {log.source === 'mobile_voice' ? '🎙️' : '💻'}
              </span>
              <span style={styles.chatText}>{log.message || log.content}</span>
            </div>
          ))}
        </div>
      </main>

      {/* Floating WebRTC Mic Activator */}
      <button
        onClick={toggleVoiceNode}
        style={{
          ...styles.micFab,
          ...(isMicActive ? styles.micFabActive : {})
        }}
        title="Trigger LiveKit Voice Node"
      >
        {isMicActive ? '🎙️ LISTENING...' : '🎙️'}
      </button>

      {/* Add Task Modal */}
      {showAddModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalCard}>
            <h4>Create Fluid Task</h4>
            <form onSubmit={handleAddTask}>
              <input
                type="text"
                placeholder="Task title..."
                value={newTaskTitle}
                onChange={e => setNewTaskTitle(e.target.value)}
                style={styles.inputField}
                autoFocus
              />
              <div style={styles.modalActions}>
                <button type="button" onClick={() => setShowAddModal(false)} style={styles.cancelBtn}>
                  Cancel
                </button>
                <button type="submit" style={styles.submitBtn}>
                  Save Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    backgroundColor: '#0d1117',
    color: '#c9d1d9',
    minHeight: '100vh',
    paddingBottom: '80px',
    boxSizing: 'border-box'
  },
  header: {
    backgroundColor: '#161b22',
    padding: '16px 20px',
    borderBottom: '1px solid rgba(255,255,255,0.1)'
  },
  headerTitle: {
    fontSize: '1.25rem',
    fontWeight: '700',
    color: '#58a6ff'
  },
  headerSubtitle: {
    fontSize: '0.8rem',
    color: '#8b949e',
    marginTop: '2px'
  },
  filterBar: {
    display: 'flex',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#0d1117',
    borderBottom: '1px solid rgba(255,255,255,0.05)'
  },
  filterBtn: {
    padding: '6px 14px',
    borderRadius: '16px',
    border: '1px solid #30363d',
    backgroundColor: '#161b22',
    color: '#8b949e',
    fontSize: '0.75rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  activeFilterBtn: {
    backgroundColor: '#1f6feb',
    color: '#ffffff',
    borderColor: '#388bfd'
  },
  addBtn: {
    marginLeft: 'auto',
    padding: '6px 14px',
    borderRadius: '16px',
    border: 'none',
    backgroundColor: '#2ea043',
    color: '#ffffff',
    fontWeight: '600',
    fontSize: '0.75rem',
    cursor: 'pointer'
  },
  mainContent: {
    padding: '16px'
  },
  sectionTitle: {
    fontSize: '1rem',
    color: '#f0f6fc',
    marginBottom: '12px'
  },
  loadingText: {
    fontSize: '0.9rem',
    color: '#8b949e'
  },
  emptyCard: {
    padding: '20px',
    textAlign: 'center',
    backgroundColor: '#161b22',
    borderRadius: '8px',
    border: '1px solid #30363d',
    color: '#8b949e'
  },
  taskCard: {
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '10px',
    padding: '14px',
    marginBottom: '12px'
  },
  taskHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  taskTitle: {
    fontWeight: '600',
    color: '#f0f6fc',
    fontSize: '0.95rem'
  },
  badge: (priority) => ({
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '0.7rem',
    fontWeight: '700',
    backgroundColor: priority === 1 ? 'rgba(248,81,73,0.2)' : 'rgba(210,153,34,0.2)',
    color: priority === 1 ? '#f85149' : '#d29922',
    border: `1px solid ${priority === 1 ? '#f85149' : '#d29922'}`
  }),
  taskMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.8rem',
    color: '#8b949e',
    marginBottom: '12px'
  },
  statusLabel: (status) => ({
    color: status === 'completed' ? '#3fb950' : status === 'in_progress' ? '#d29922' : '#58a6ff',
    fontWeight: '600'
  }),
  actionRow: {
    display: 'flex',
    gap: '8px'
  },
  doneBtn: {
    flex: 1,
    padding: '6px',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: 'rgba(46,160,67,0.2)',
    color: '#3fb950',
    border: '1px solid #2ea043',
    fontSize: '0.75rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  startBtn: {
    flex: 1,
    padding: '6px',
    borderRadius: '6px',
    border: '1px solid #d29922',
    backgroundColor: 'rgba(210,153,34,0.2)',
    color: '#d29922',
    fontSize: '0.75rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  deferBtn: {
    flex: 1,
    padding: '6px',
    borderRadius: '6px',
    border: '1px solid #30363d',
    backgroundColor: '#21262d',
    color: '#8b949e',
    fontSize: '0.75rem',
    cursor: 'pointer'
  },
  timelineBox: {
    backgroundColor: '#161b22',
    borderRadius: '8px',
    border: '1px solid #30363d',
    padding: '12px'
  },
  chatEntry: {
    display: 'flex',
    gap: '8px',
    padding: '6px 0',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    fontSize: '0.85rem'
  },
  speakerIcon: {
    fontSize: '1rem'
  },
  chatText: {
    color: '#c9d1d9'
  },
  micFab: {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    backgroundColor: '#a371f7',
    color: '#ffffff',
    border: 'none',
    boxShadow: '0 8px 24px rgba(163,113,247,0.4)',
    fontSize: '1.2rem',
    fontWeight: '700',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    zIndex: 1000,
    transition: 'transform 0.2s ease, background-color 0.2s ease'
  },
  micFabActive: {
    backgroundColor: '#f85149',
    width: 'auto',
    borderRadius: '32px',
    padding: '0 24px',
    boxShadow: '0 8px 24px rgba(248,81,73,0.5)',
    animation: 'pulse 1.5s infinite'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000
  },
  modalCard: {
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '12px',
    padding: '20px',
    width: '90%',
    maxWidth: '400px'
  },
  inputField: {
    width: '100%',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #30363d',
    backgroundColor: '#0d1117',
    color: '#f0f6fc',
    marginBottom: '16px',
    boxSizing: 'border-box'
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px'
  },
  cancelBtn: {
    padding: '8px 16px',
    borderRadius: '6px',
    border: '1px solid #30363d',
    backgroundColor: 'transparent',
    color: '#8b949e',
    cursor: 'pointer'
  },
  submitBtn: {
    padding: '8px 16px',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#1f6feb',
    color: '#ffffff',
    fontWeight: '600',
    cursor: 'pointer'
  }
};
