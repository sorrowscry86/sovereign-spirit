/**
 * VoidCat RDC: Sovereign Spirit - Sync Page
 * ==========================================
 * Date: 2026-01-24
 * 
 * Dedicated page for spirit synchronization controls.
 */

import React from 'react';
import SpiritSyncPanel from '../components/SpiritSyncPanel';

export default function Sync() {
    return (
        <div style={{ padding: '80px 2rem 2rem 2rem', height: '100%' }}>
            <SpiritSyncPanel />
        </div>
    );
}
