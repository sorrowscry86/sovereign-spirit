/**
 * VoidCat RDC: Sovereign Spirit - Tasks Page
 * ===========================================
 * Date: 2026-01-24
 * 
 * Dedicated page for task graph visualization.
 */

import React from 'react';
import TaskGraph from '../components/TaskGraph';

export default function Tasks() {
    return (
        <div style={{ padding: '80px 2rem 2rem 2rem', height: '100%' }}>
            <TaskGraph />
        </div>
    );
}
