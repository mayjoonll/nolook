// web/src/pages/Dashboard.jsx
import { useEffect, useState, useCallback, useRef } from 'react';
import VideoPreview from '../components/VideoPreview';

import TransitionSelector from '../components/TransitionSelector';
import Toast, { useToast } from '../components/Toast';
import '../styles/dashboard.css';

import { wsClient } from '../lib/wsClient';
import { setPauseFake, setForceReal, resetLock, fetchEngineState, controlAssistant } from '../lib/api';

import logoImg from '../assets/logo.png';

export default function Dashboard() {
    const { toasts, addToast, removeToast } = useToast();

    const [mode, setMode] = useState('REAL');
    const [ratio, setRatio] = useState(0);
    const [lockedFake, setLockedFake] = useState(false);
    const [pauseFake, setPauseFakeState] = useState(false);
    const [forceReal, setForceRealState] = useState(false);
    const [reasons, setReasons] = useState([]);
    const [sttData, setSttData] = useState({ history: [], current: '' });
    const [assistantEnabled, setAssistantEnabled] = useState(false);

    // ✅ session/warmup
    const [sessionActive, setSessionActive] = useState(false);
    const [warmingUp, setWarmingUp] = useState(false);
    const [warmupTotalSec, setWarmupTotalSec] = useState(30);
    const [warmupRemainingSec, setWarmupRemainingSec] = useState(0);

    const prevWarmingUpRef = useRef(false);
    const scrollRef = useRef(null);

    // Auto-scroll to bottom when sttData changes
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [sttData]);

    const mmss = (sec) => {
        const s = Math.max(0, Number(sec || 0));
        const m = String(Math.floor(s / 60)).padStart(2, '0');
        const r = String(Math.floor(s % 60)).padStart(2, '0');
        return `${m}:${r}`;
    };

    const applyState = useCallback((s) => {
        if (!s) return;

        setMode(s.mode ?? 'REAL');
        setRatio(s.ratio ?? 0);
        setLockedFake(!!s.lockedFake);
        setPauseFakeState(!!s.pauseFake);
        setForceRealState(!!s.forceReal);
        setReasons(s.reasons ?? []);
        if (s.stt) setSttData(s.stt);
        if (s.assistantEnabled !== undefined) setAssistantEnabled(!!s.assistantEnabled);

        setSessionActive(!!s.sessionActive);
        setWarmingUp(!!s.warmingUp);
        setWarmupTotalSec(s.warmupTotalSec ?? 30);
        setWarmupRemainingSec(s.warmupRemainingSec ?? 0);

        if (s.reaction) addToast(`🤖 ${s.reaction}`, 'success');
        if (s.notice) addToast(s.notice, 'success');

        const prev = prevWarmingUpRef.current;
        if (prev && !s.warmingUp) addToast('✅ 녹화 완료!', 'success');
        prevWarmingUpRef.current = !!s.warmingUp;
    }, [addToast]);

    useEffect(() => {
        fetchEngineState().then(applyState).catch(() => { });

        wsClient.onMessage = applyState;
        wsClient.connect();

        return () => {
            wsClient.disconnect();
            wsClient.onMessage = null;
        };
    }, [applyState]);

    const togglePauseFake = useCallback(async () => {
        const next = !pauseFake;
        const res = await setPauseFake(next);
        if (res.ok) addToast(`PauseFake: ${next ? 'ON' : 'OFF'}`, 'success');
    }, [pauseFake, addToast]);

    const toggleForceReal = useCallback(async () => {
        const next = !forceReal;
        const res = await setForceReal(next);
        if (res.ok) addToast(`ForceREAL: ${next ? 'ON' : 'OFF'}`, 'success');
    }, [forceReal, addToast]);

    const handleResetLock = useCallback(async () => {
        const res = await resetLock();
        if (res.ok) addToast('락 초기화 완료', 'success');
    }, [addToast]);

    const toggleAssistant = useCallback(async () => {
        const next = !assistantEnabled;
        const res = await controlAssistant(next);
        if (res.ok) addToast(`Auto Macro: ${next ? 'ON' : 'OFF'}`, 'success');
    }, [assistantEnabled, addToast]);

    const progress = warmupTotalSec > 0
        ? (warmupTotalSec - warmupRemainingSec) / warmupTotalSec
        : 0;

    const showWarmup = warmingUp || (sessionActive && warmupRemainingSec > 0);

    return (
        <div className="dashboard simple">
            {/* ✅ Warmup Overlay */}
            {showWarmup && (
                <div className="warmup-overlay">
                    <div className="warmup-card">
                        <img src={logoImg} alt="No-Look Logo" className="warmup-logo" />
                        <div className="warmup-title">녹화 중입니다</div>
                        <div className="warmup-desc">{warmupTotalSec}초 동안 가만히 있어주세요</div>
                        <div className="warmup-timer">{mmss(warmupRemainingSec)}</div>
                        <div className="warmup-bar">
                            <div
                                className="warmup-bar-fill"
                                style={{ width: `${Math.min(100, Math.max(0, progress * 100))}%` }}
                            />
                        </div>
                        <div className="warmup-sub">녹화가 끝나면 자동으로 추적을 시작해요.</div>
                    </div>
                </div>
            )}

            {/* ✅ 헤더 로고 */}
            <header className="dashboard-header">
                <img src={logoImg} alt="No-Look Logo" className="header-logo" />
            </header>

            <div className="simple-layout">
                <div className="video-section">
                    <VideoPreview mode={mode} ratio={ratio} addToast={addToast} />
                </div>

                <div className="control-bar">
                    <div className="switch-buttons">
                        <button className="btn btn-large btn-primary" onClick={togglePauseFake}>
                            {pauseFake ? 'FAKE 재생 재개' : 'FAKE 재생 일시정지'}
                        </button>

                        <button className="btn btn-large btn-secondary" onClick={toggleForceReal}>
                            {forceReal ? 'Force REAL 해제(자동복귀)' : 'Force REAL(강제복귀)'}
                        </button>

                        <button className="btn btn-large" onClick={handleResetLock}>
                            락 초기화
                        </button>

                        <button
                            className={`btn btn-large ${assistantEnabled ? 'btn-danger' : 'btn-success'}`}
                            style={{ marginLeft: 10 }}
                            onClick={toggleAssistant}
                        >
                            {assistantEnabled ? 'Auto Macro OFF' : 'Auto Macro ON'}
                        </button>
                    </div>

                    <div className="mode-display">
                        <span className={`mode-indicator ${mode.toLowerCase()}`}>
                            현재: <strong>{mode}</strong> ({Math.round(ratio * 100)}%)
                        </span>
                        <span style={{ marginLeft: 12 }}>
                            Locked: <strong>{String(lockedFake)}</strong>
                        </span>
                        {!!reasons?.length && (
                            <span style={{ marginLeft: 12 }}>
                                Reasons: <strong>{reasons.join(', ')}</strong>
                            </span>
                        )}
                    </div>
                </div>

                <div className="transition-section">
                    <TransitionSelector addToast={addToast} />
                </div>

                {/* ✅ STT Display Section */}
                <div className="stt-section" style={{
                    marginTop: '2rem',
                    padding: '1.5rem',
                    backgroundColor: 'rgba(0,0,0,0.3)',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.1)'
                }}>
                    <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', color: '#fff' }}>
                        🎙️ Live Transcript (Auto Macro)
                    </h3>
                    <div
                        className="stt-history"
                        ref={scrollRef}
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.5rem',
                            marginBottom: '1rem',
                            opacity: 0.9,
                            maxHeight: '300px',
                            overflowY: 'auto',
                            paddingRight: '8px'
                        }}
                    >
                        {sttData.history.length === 0 && !sttData.current && (
                            <div style={{ color: '#666', fontStyle: 'italic' }}>
                                대기 중... (말씀하시면 여기에 표시됩니다)
                            </div>
                        )}
                        {sttData.history.map((text, i) => (
                            <div key={i} className="stt-line" style={{ color: '#e0e0e0', lineHeight: '1.4' }}>
                                {text}
                            </div>
                        ))}
                    </div>
                    {sttData.current && (
                        <div className="stt-current" style={{
                            color: '#4caf50',
                            fontWeight: '600',
                            fontSize: '1.1rem',
                            padding: '0.5rem',
                            background: 'rgba(76, 175, 80, 0.1)',
                            borderRadius: '6px'
                        }}>
                            ▶ {sttData.current}
                        </div>
                    )}
                </div>


            </div>

            <Toast toasts={toasts} onRemove={removeToast} />
        </div>
    );
}
