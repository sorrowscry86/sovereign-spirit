import React, { createContext, useContext, useEffect, useState, useRef } from 'react';

const SocketContext = createContext(null);

const WEBSOCKET_URL = "ws://localhost:8000/ws";

export const SocketProvider = ({ children }) => {
    const [socketStatus, setSocketStatus] = useState('disconnected');
    const [lastMessage, setLastMessage] = useState(null);
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const connect = () => {
        // Prevent multiple connections
        if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
            return;
        }

        console.log("⚡ Nervous System: Initiating Link...");
        const ws = new WebSocket(WEBSOCKET_URL);

        ws.onopen = () => {
            console.log("⚡ Nervous System: Online");
            setSocketStatus('connected');
            // Clear any pending reconnects if we succeed
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        };

        ws.onclose = () => {
            console.log("⚡ Nervous System: Severed");
            setSocketStatus('disconnected');
            wsRef.current = null;

            // Auto-reconnect mechanism (FEAT-003)
            reconnectTimeoutRef.current = setTimeout(() => {
                console.log("⚡ Nervous System: Attempting Re-link...");
                connect();
            }, 3000);
        };

        ws.onError = (err) => {
            console.error("⚡ Nervous System: Error", err);
            ws.close(); // Force close to trigger onclose logic
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                setLastMessage(msg);
            } catch (e) {
                console.error("⚡ Invalid Nerve Impulse:", event.data);
            }
        };

        wsRef.current = ws;
    };

    useEffect(() => {
        connect();
        return () => {
            if (wsRef.current) wsRef.current.close();
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        };
    }, []);

    const sendMessage = (msg) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(msg));
        } else {
            console.warn("⚡ Cannot send impulse: Network severed.");
        }
    };

    return (
        <SocketContext.Provider value={{ socketStatus, lastMessage, sendMessage }}>
            {children}
        </SocketContext.Provider>
    );
};

export const useSocket = () => useContext(SocketContext);
