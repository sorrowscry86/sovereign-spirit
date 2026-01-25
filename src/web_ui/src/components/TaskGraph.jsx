/**
 * VoidCat RDC: Sovereign Spirit - TaskGraph Component
 * ====================================================
 * Date: 2026-01-24
 * 
 * Interactive graph visualization of agent tasks and dependencies from Neo4j.
 * Uses react-force-graph-2d for physics-based layout.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Network, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

export default function TaskGraph() {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const graphRef = useRef();

    // Fetch graph data from backend
    useEffect(() => {
        const fetchGraph = async () => {
            try {
                setLoading(true);
                setError(null);
                const res = await fetch('/graph/tasks');
                if (!res.ok) throw new Error(`Failed to fetch graph: ${res.status}`);
                const data = await res.json();

                // Transform backend data to react-force-graph format
                const nodes = data.nodes?.map(node => ({
                    id: node.id,
                    name: node.properties?.name || node.labels?.[0] || 'Unknown',
                    type: node.labels?.[0] || 'Unknown',
                    ...node.properties
                })) || [];

                const links = data.edges?.map(edge => ({
                    source: edge.start_node,
                    target: edge.end_node,
                    type: edge.type,
                    ...edge.properties
                })) || [];

                setGraphData({ nodes, links });
                console.log(`[TaskGraph] Loaded ${nodes.length} nodes, ${links.length} edges`);
            } catch (err) {
                console.error('[TaskGraph] Failed to fetch graph:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchGraph();
    }, []);

    // Node rendering with color coding
    const paintNode = useCallback((node, ctx, globalScale) => {
        const label = node.name;
        const fontSize = 12 / globalScale;
        ctx.font = `${fontSize}px Inter, sans-serif`;

        // Color by node type
        const typeColors = {
            'Task': '#00E5FF',      // cyan
            'Agent': '#00FF87',     // green
            'Memory': '#9D50BB',    // purple
            'Skill': '#58A6FF',     // blue
        };
        const color = typeColors[node.type] || '#888888';

        // Draw circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();

        // Draw label
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, node.x, node.y + 10);
    }, []);

    // Link rendering with color coding
    const paintLink = useCallback((link, ctx) => {
        const typeColors = {
            'DEPENDS_ON': '#00E5FF',
            'ASSIGNED_TO': '#00FF87',
            'USES': '#9D50BB',
        };
        const color = typeColors[link.type] || '#444444';

        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.6;
    }, []);

    // Zoom controls
    const handleZoomIn = () => graphRef.current?.zoom(1.5, 400);
    const handleZoomOut = () => graphRef.current?.zoom(0.67, 400);
    const handleZoomFit = () => graphRef.current?.zoomToFit(400, 50);

    return (
        <div className="glass-panel" style={{ height: '600px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Network size={18} />
                    Task Dependency Graph
                </h3>

                {/* Zoom Controls */}
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                        onClick={handleZoomIn}
                        style={{
                            padding: '6px',
                            backgroundColor: 'rgba(0, 0, 0, 0.5)',
                            border: '1px solid var(--neon-cyan)',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            cursor: 'pointer'
                        }}
                        title="Zoom In"
                    >
                        <ZoomIn size={16} />
                    </button>
                    <button
                        onClick={handleZoomOut}
                        style={{
                            padding: '6px',
                            backgroundColor: 'rgba(0, 0, 0, 0.5)',
                            border: '1px solid var(--neon-cyan)',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            cursor: 'pointer'
                        }}
                        title="Zoom Out"
                    >
                        <ZoomOut size={16} />
                    </button>
                    <button
                        onClick={handleZoomFit}
                        style={{
                            padding: '6px',
                            backgroundColor: 'rgba(0, 0, 0, 0.5)',
                            border: '1px solid var(--neon-cyan)',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            cursor: 'pointer'
                        }}
                        title="Fit to View"
                    >
                        <Maximize2 size={16} />
                    </button>
                </div>
            </div>

            {/* Graph Container */}
            <div style={{ flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.4)', borderRadius: '8px', position: 'relative' }}>
                {loading && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        color: 'var(--text-secondary)',
                        zIndex: 10
                    }}>
                        Loading graph...
                    </div>
                )}

                {error && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        padding: '16px',
                        backgroundColor: 'rgba(255, 61, 113, 0.1)',
                        border: '1px solid var(--neon-error)',
                        borderRadius: '8px',
                        color: 'var(--neon-error)',
                        zIndex: 10
                    }}>
                        ⚠️ Failed to load graph: {error}
                    </div>
                )}

                {!loading && !error && graphData.nodes.length === 0 && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        color: 'var(--text-dim)',
                        zIndex: 10
                    }}>
                        No graph data available
                    </div>
                )}

                {!loading && !error && graphData.nodes.length > 0 && (
                    <ForceGraph2D
                        ref={graphRef}
                        graphData={graphData}
                        nodeLabel="name"
                        nodeCanvasObject={paintNode}
                        linkCanvasObject={paintLink}
                        linkDirectionalArrowLength={3}
                        linkDirectionalArrowRelPos={1}
                        backgroundColor="rgba(0, 0, 0, 0)"
                        linkColor={() => '#444444'}
                        nodeColor={() => '#00E5FF'}
                        width={window.innerWidth - 300}
                        height={520}
                        cooldownTicks={100}
                        onEngineStop={() => graphRef.current?.zoomToFit(400, 50)}
                    />
                )}
            </div>

            {/* Legend */}
            {!loading && !error && graphData.nodes.length > 0 && (
                <div style={{
                    marginTop: '12px',
                    padding: '8px 12px',
                    backgroundColor: 'rgba(0, 0, 0, 0.3)',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    display: 'flex',
                    gap: '16px',
                    flexWrap: 'wrap'
                }}>
                    <LegendItem color="#00E5FF" label="Task" />
                    <LegendItem color="#00FF87" label="Agent" />
                    <LegendItem color="#9D50BB" label="Memory" />
                    <LegendItem color="#58A6FF" label="Skill" />
                    <span style={{ marginLeft: 'auto', color: 'var(--text-dim)' }}>
                        {graphData.nodes.length} nodes, {graphData.links.length} edges
                    </span>
                </div>
            )}
        </div>
    );
}

const LegendItem = ({ color, label }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: color
        }} />
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
    </div>
);
