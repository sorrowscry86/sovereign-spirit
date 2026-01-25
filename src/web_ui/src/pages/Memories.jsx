/**
 * VoidCat RDC: Sovereign Spirit - Memories Page
 * ==============================================
 * Date: 2026-01-24
 * 
 * Dedicated page for agent memory exploration.
 */

import React from 'react';
import MemoryViewer from '../components/MemoryViewer';

export default function Memories() {
    return (
        <div style={{ padding: '80px 2rem 2rem 2rem', height: '100%' }}>
            <MemoryViewer />
        </div>
    );
}
