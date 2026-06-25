// frontend/src/components/memory/LongTermMemoryApp.tsx
import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../../api/client';

const LongTermMemoryApp: React.FC = () => {
  const [files, setFiles] = useState<FileList | null>(null);
  const [progress, setProgress] = useState(0);
  const [processedFiles, setProcessedFiles] = useState(0);
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState('');
  const [newCollectionName, setNewCollectionName] = useState('');
  const [mode, setMode] = useState<'select' | 'create'>('select');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Directory ingestion state
  const [ingestDirectory, setIngestDirectory] = useState('');
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [isIngestingDir, setIsIngestingDir] = useState(false);
  const [dirIngestResult, setDirIngestResult] = useState<string>('');
  const dirInputRef = useRef<HTMLInputElement>(null);

  // LTM Storage & Backup state
  const [ltmSize, setLtmSize] = useState(0);
  const [isExportingLTM, setIsExportingLTM] = useState(false);
  const [isImportingLTM, setIsImportingLTM] = useState(false);
  const ltmFileInputRef = useRef<HTMLInputElement>(null);

  // Chunking state
  const [chunkingStatus, setChunkingStatus] = useState<'idle' | 'chunking' | 'chunked' | 'ingesting' | 'error'>('idle');
  const [chunkInfo, setChunkInfo] = useState<any>(null);
  const [showChunkOptions, setShowChunkOptions] = useState(false);

  useEffect(() => {
    apiClient.get('/api/memory/qdrant/collections')
      .then(res => {
        setCollections(res.data.collections || []);
        if (res.data.collections?.length > 0) {
          setSelectedCollection(res.data.collections[0]);
        }
      })
      .catch(err => console.error('Failed to load collections:', err));
  }, []);

  // Fetch LTM size periodically
  useEffect(() => {
    const fetchLTMSize = async () => {
      try {
        const res = await apiClient.get('/api/memory/analytics/ltm-size');
        setLtmSize(res.data.size || 0);
      } catch (err) {
        console.error('Failed to fetch LTM size:', err);
      }
    };
    
    fetchLTMSize();
    const interval = setInterval(fetchLTMSize, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFiles(e.target.files); setProgress(0); setProcessedFiles(0);
  };
  const handleBrowseClick = () => fileInputRef.current?.click();
  
  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;
    try {
      await apiClient.post('/api/memory/qdrant/collection', { name: newCollectionName.trim(), action: 'create' });
      setCollections(prev => [...prev, newCollectionName.trim()]);
      setSelectedCollection(newCollectionName.trim());
      setNewCollectionName(''); setMode('select');
    } catch (err) { console.error('Failed to create collection:', err); }
  };

  const handleUpload = async () => {
    if (!files || files.length === 0 || !selectedCollection) return;
    const documents = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i]; const text = await file.text();
      documents.push({ text, metadata: { source: file.name, size: file.size, type: file.type, uploaded_at: new Date().toISOString() } });
    }
    let count = 0; const total = documents.length; setProgress(0); setProcessedFiles(0);
    try {
      const interval = setInterval(() => { count++; setProcessedFiles(count); setProgress(Math.round((count / total) * 100)); }, 200);
      await apiClient.post('/api/memory/qdrant/ingest', { collection: selectedCollection, documents });
      clearInterval(interval); setProgress(100); setProcessedFiles(total); setFiles(null); if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) { console.error('Ingestion failed:', err); setProgress(0); }
  };

  // Handle directory browse - extract directory path from selected files
  const handleDirectoryBrowse = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // Get the first file's webkitRelativePath and extract directory
      const firstFile = files[0] as any;
      if (firstFile.webkitRelativePath) {
        const pathParts = firstFile.webkitRelativePath.split('/');
        if (pathParts.length > 1) {
          // Remove the filename to get directory path
          pathParts.pop();
          const dirPath = '~/' + pathParts.join('/');
          setIngestDirectory(dirPath);
        }
      }
    }
  };

  const handleDirectoryBrowseClick = () => {
    dirInputRef.current?.click();
  };

  const handleDirectoryIngest = async () => {
    if (!ingestDirectory.trim() || !selectedCollection) return;
    setIsIngestingDir(true);
    setDirIngestResult('');
    try {
      const response = await apiClient.post('/api/memory/qdrant/ingest-directory', {
        directory: ingestDirectory.trim(),
        collection: selectedCollection,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap
      });
      setDirIngestResult(`✅ Ingested ${response.data.total_chunks} chunks from ${response.data.files_processed} files`);
    } catch (error: any) {
      setDirIngestResult(`❌ Failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsIngestingDir(false);
    }
  };

  // Chunking handlers
  const handleChunkFiles = async () => {
    if (!selectedCollection) return;
    setChunkingStatus('chunking');
    try {
      const response = await apiClient.post('/api/memory/qdrant/chunk-files', {
        collection: selectedCollection,
        directory: ingestDirectory.trim(),
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap
      });
      setChunkInfo(response.data);
      setChunkingStatus('chunked');
      setShowChunkOptions(true);
    } catch (error: any) {
      console.error('Chunking failed:', error);
      setChunkingStatus('error');
      alert(`❌ Chunking failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleIngestChunks = async () => {
    if (!selectedCollection) return;
    setChunkingStatus('ingesting');
    try {
      const response = await apiClient.post(`/api/memory/qdrant/ingest-chunks/${selectedCollection}`);
      alert(`✅ Ingested ${response.data.documents_ingested} chunks into Qdrant`);
      setChunkingStatus('idle');
      setShowChunkOptions(false);
      setChunkInfo(null);
    } catch (error: any) {
      console.error('Ingest failed:', error);
      alert(`❌ Ingest failed: ${error.response?.data?.detail || error.message}`);
      setChunkingStatus('error');
    }
  };

  const handleCleanupChunks = async () => {
    if (!window.confirm('Delete all chunk files to free up disk space?')) return;
    try {
      const response = await apiClient.delete(`/api/memory/qdrant/cleanup-chunks/${selectedCollection}`);
      alert(`✅ ${response.data.message}`);
      setChunkingStatus('idle');
      setChunkInfo(null);
      setShowChunkOptions(false);
    } catch (error: any) {
      console.error('Cleanup failed:', error);
      alert(`❌ Cleanup failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  // LTM Backup handlers
  const handleExportLTM = async () => {
    setIsExportingLTM(true);
    try {
      const response = await apiClient.get('/api/memory/qdrant/collections');
      const collections = response.data.collections || [];
      
      const backup = {
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        type: 'qdrant',
        collections: collections.map((col: any) => ({
          name: col.name,
          points_count: col.points_count || 0,
          vectors_count: col.vectors_count || 0
        }))
      };
      
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mai-rag-ltm-backup-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      alert('✅ LTM backup exported');
    } catch (err) {
      console.error('LTM export failed:', err);
      alert('❌ Failed to export LTM');
    } finally {
      setIsExportingLTM(false);
    }
  };

  const handleImportLTM = () => {
    ltmFileInputRef.current?.click();
  };

  const handleLTMFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!window.confirm('⚠️ This will merge LTM backup data. Continue?')) {
      return;
    }
    
    setIsImportingLTM(true);
    try {
      const text = await file.text();
      const backup = JSON.parse(text);
      alert('✅ LTM backup imported (feature coming soon)');
    } catch (err) {
      console.error('LTM import failed:', err);
      alert('❌ Failed to import LTM');
    } finally {
      setIsImportingLTM(false);
      if (ltmFileInputRef.current) {
        ltmFileInputRef.current.value = '';
      }
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <section className="console reveal delay-2 file-upload-panel glow-panel"
    style={{ minHeight: 'auto', height: 'auto', display: 'flex', flexDirection: 'column', padding: '16px 24px', boxSizing: 'border-box', marginBottom: '24px' }}>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        <div 
          className="console-title" 
          style={{ 
            color: 'var(--accent)', 
            fontSize: '1.3rem', 
            fontWeight: 'bold', 
            marginBottom: '12px' 
          }}
        >
          Long-Term Memory
        </div>
        <p style={{ fontSize: '0.9rem', opacity: 0.9, margin: '0 0 12px 0' }}>Upload documents to a subject-centric knowledge base.</p>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          <button onClick={() => setMode('select')} style={{ flex: 1, padding: '6px 10px', borderRadius: '6px', border: mode === 'select' ? '1px solid var(--accent)' : '1px solid var(--line)', background: mode === 'select' ? 'rgba(124,246,211,0.1)' : 'transparent', color: 'var(--text)', cursor: 'pointer', fontSize: '0.85rem' }}>Use Existing</button>
          <button onClick={() => setMode('create')} style={{ flex: 1, padding: '6px 10px', borderRadius: '6px', border: mode === 'create' ? '1px solid var(--accent)' : '1px solid var(--line)', background: mode === 'create' ? 'rgba(124,246,211,0.1)' : 'transparent', color: 'var(--text)', cursor: 'pointer', fontSize: '0.85rem' }}>Create New</button>
        </div>
        {mode === 'select' ? (
          <select value={selectedCollection} onChange={e => setSelectedCollection(e.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: '0.9rem' }}>
            {collections.length === 0 ? <option value="">No collections</option> : collections.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        ) : (
          <div style={{ display: 'flex', gap: '8px' }}>
            <input type="text" placeholder="Collection name" value={newCollectionName} onChange={e => setNewCollectionName(e.target.value)} style={{ flex: 1, padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: '0.9rem' }} />
            <button onClick={handleCreateCollection} disabled={!newCollectionName.trim()} style={{ padding: '8px 12px', borderRadius: '6px', background: newCollectionName.trim() ? 'var(--accent)' : 'rgba(255,255,255,0.1)', color: newCollectionName.trim() ? '#000' : '#666', border: 'none', cursor: newCollectionName.trim() ? 'pointer' : 'not-allowed', fontWeight: 500, fontSize: '0.85rem' }}>Create</button>
          </div>
        )}
      </div>

      {/* File Upload Section */}
      <div style={{ paddingTop: '8px', borderTop: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>File Upload</div>
        <div style={{ position: 'relative', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: '0.85rem', height: '1.6rem', lineHeight: '1.6rem', paddingLeft: '8px', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', width: `${progress}%`, backgroundColor: 'var(--accent)', opacity: 0.3, transition: 'width 0.2s' }} />
          <div style={{ position: 'relative', zIndex: 1 }}>{progress > 0 ? `${processedFiles}/${files?.length || 0} - ${progress}%` : files ? `${files.length} selected` : 'Best For smaller files less than 1000 Characters'}</div>
        </div>
        <input type="file" multiple ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={handleBrowseClick} style={{ flex: 1, padding: '8px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.08)', color: 'var(--text)', border: '1px solid var(--line)', cursor: 'pointer', fontSize: '0.85rem' }}>Browse</button>
          <button onClick={handleUpload} disabled={!files || files.length === 0 || !selectedCollection} style={{ flex: 1, padding: '8px 10px', borderRadius: '6px', background: (!files || !selectedCollection) ? 'rgba(255,255,255,0.08)' : 'var(--accent)', color: (!files || !selectedCollection) ? '#666' : '#000', border: 'none', cursor: (!files || !selectedCollection) ? 'not-allowed' : 'pointer', fontSize: '0.85rem' }}>Load</button>
        </div>
      </div>

      {/* Directory Ingestion Section - UPDATED */}
      <div style={{ paddingTop: '12px', borderTop: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>Directory Ingestion</div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input 
            type="text" 
            value={ingestDirectory} 
            onChange={(e) => setIngestDirectory(e.target.value)} 
            placeholder="Directory path (e.g., ~/MAi-RAG/documents_storage)" 
            style={{ flex: 1, padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: '0.85rem', boxSizing: 'border-box' }} 
          />
          <button 
            onClick={handleDirectoryBrowseClick}
            style={{ 
              padding: '8px 12px', 
              borderRadius: '6px', 
              background: 'rgba(255,255,255,0.08)', 
              color: 'var(--text)', 
              border: '1px solid var(--line)', 
              cursor: 'pointer', 
              fontSize: '0.85rem',
              whiteSpace: 'nowrap'
            }}
          >
            Browse
          </button>
        </div>
        {/* Hidden file input for directory browsing */}
        <input 
          type="file" 
          ref={dirInputRef}
          onChange={handleDirectoryBrowse}
          style={{ display: 'none' }}
          {...({ webkitdirectory: '', directory: '', mozdirectory: '' } as any)}
        />
        <div style={{ display: 'flex', gap: '8px' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '0.75rem', opacity: 0.7, display: 'block', marginBottom: '2px' }}>Chunk Size</label>
            <input 
              type="number" 
              value={chunkSize} 
              onChange={(e) => setChunkSize(Number(e.target.value))} 
              min={100}
              max={10000}
              style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: '0.85rem', boxSizing: 'border-box' }} 
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '0.75rem', opacity: 0.7, display: 'block', marginBottom: '2px' }}>Overlap</label>
            <input 
              type="number" 
              value={chunkOverlap} 
              onChange={(e) => setChunkOverlap(Number(e.target.value))} 
              min={0}
              max={1000}
              style={{ width: '100%', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: '0.85rem', boxSizing: 'border-box' }} 
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={handleChunkFiles} 
            disabled={chunkingStatus === 'chunking' || !ingestDirectory.trim() || !selectedCollection} 
            style={{ 
              flex: 1,
              padding: '8px 10px', 
              borderRadius: '6px', 
              background: (chunkingStatus === 'chunking' || !ingestDirectory.trim() || !selectedCollection) ? 'rgba(255,255,255,0.08)' : 'rgba(139, 92, 246, 0.8)', 
              color: (chunkingStatus === 'chunking' || !ingestDirectory.trim() || !selectedCollection) ? '#666' : '#fff', 
              border: 'none', 
              cursor: (chunkingStatus === 'chunking' || !ingestDirectory.trim() || !selectedCollection) ? 'not-allowed' : 'pointer', 
              fontSize: '0.85rem',
              fontWeight: 500
            }}
          >
            {chunkingStatus === 'chunking' ? 'Chunking...' : 'Chunk Files'}
          </button>
          <button 
            onClick={handleDirectoryIngest} 
            disabled={isIngestingDir || !ingestDirectory.trim() || !selectedCollection} 
            style={{ 
              flex: 1,
              padding: '8px 10px', 
              borderRadius: '6px', 
              background: (isIngestingDir || !ingestDirectory.trim() || !selectedCollection) ? 'rgba(255,255,255,0.08)' : 'var(--accent)', 
              color: (isIngestingDir || !ingestDirectory.trim() || !selectedCollection) ? '#666' : '#000', 
              border: 'none', 
              cursor: (isIngestingDir || !ingestDirectory.trim() || !selectedCollection) ? 'not-allowed' : 'pointer', 
              fontSize: '0.85rem',
              fontWeight: 500
            }}
          >
            {isIngestingDir ? 'Loading...' : 'Ingest Directory'}
          </button>
        </div>
        {dirIngestResult && (
          <div style={{ fontSize: '0.8rem', padding: '6px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)' }}>
            {dirIngestResult}
          </div>
        )}
      </div>

      {/* Chunking Options - Shows after chunking is complete */}
      {showChunkOptions && chunkInfo && (
        <div style={{ 
          paddingTop: '12px', 
          borderTop: '1px solid var(--line)', 
          marginTop: '12px',
          padding: '12px',
          background: 'rgba(124, 246, 211, 0.05)',
          borderRadius: '8px'
        }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
            Chunking Complete
          </div>
          <div style={{ fontSize: '0.8rem', marginBottom: '12px' }}>
            <div>Files processed: {chunkInfo.files_processed}</div>
            <div>Total chunks: {chunkInfo.total_chunks}</div>
            <div style={{ marginTop: '4px', opacity: 0.7 }}>
              Location: ~/MAi-RAG/storage/chunks/{selectedCollection}/
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              onClick={handleIngestChunks}
              disabled={chunkingStatus === 'ingesting'}
              style={{ 
                flex: 1, 
                padding: '8px', 
                borderRadius: '6px', 
                border: 'none', 
                background: chunkingStatus === 'ingesting' ? 'rgba(255,255,255,0.1)' : 'var(--accent)', 
                color: chunkingStatus === 'ingesting' ? '#666' : '#000', 
                cursor: chunkingStatus === 'ingesting' ? 'not-allowed' : 'pointer', 
                fontWeight: 600
              }}
            >
              {chunkingStatus === 'ingesting' ? 'Ingesting...' : 'Ingest to Qdrant'}
            </button>
            <button 
              onClick={handleCleanupChunks}
              style={{ 
                flex: 1, 
                padding: '8px', 
                borderRadius: '6px', 
                border: '1px solid #ef4444', 
                background: 'transparent', 
                color: '#ef4444', 
                cursor: 'pointer', 
                fontWeight: 600
              }}
            >
              Cleanup Chunks
            </button>
          </div>
        </div>
      )}

      {/* Storage & Stats Section - 2 COLUMNS */}
      <div style={{ 
        paddingTop: '12px', 
        borderTop: '1px solid var(--line)', 
        marginTop: '12px',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '12px'
      }}>
        {/* Left Column: LTM Storage */}
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
            Long-Term Memory Storage
          </div>
          <div style={{ 
            padding: '10px', 
            borderRadius: '6px', 
            background: 'rgba(255,255,255,0.04)', 
            border: '1px solid var(--line)'
          }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent)' }}>
              {formatSize(ltmSize)}
            </div>
          </div>
        </div>
        
        {/* Right Column: Collections Count */}
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
            Number of Database Collections
          </div>
          <div style={{ 
            padding: '10px', 
            borderRadius: '6px', 
            background: 'rgba(255,255,255,0.04)', 
            border: '1px solid var(--line)'
          }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent)' }}>
              {collections.length}
            </div>
          </div>
        </div>
      </div>
        
      {/* Backup Buttons */}
      <div style={{ marginTop: '12px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
          Long-Term Memory Backup
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={handleExportLTM} 
            disabled={isExportingLTM}
            style={{ 
              flex: 1, 
              padding: '10px 12px',
              borderRadius: '6px', 
              border: 'none', 
              background: isExportingLTM ? 'rgba(255,255,255,0.1)' : 'var(--accent)', 
              color: isExportingLTM ? '#666' : '#000', 
              cursor: isExportingLTM ? 'not-allowed' : 'pointer', 
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            {isExportingLTM ? 'Exporting...' : 'Export LTM'}
          </button>
          <button 
            onClick={handleImportLTM} 
            disabled={isImportingLTM}
            style={{ 
              flex: 1, 
              padding: '10px 12px',
              borderRadius: '6px', 
              border: '1px solid var(--accent)', 
              background: 'transparent', 
              color: isImportingLTM ? '#666' : 'var(--accent)', 
              cursor: isImportingLTM ? 'not-allowed' : 'pointer', 
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            {isImportingLTM ? 'Importing...' : 'Import LTM'}
          </button>
        </div>
      </div>

      {/* Hidden file input for LTM import */}
      <input
        type="file"
        ref={ltmFileInputRef}
        onChange={handleLTMFileSelect}
        accept=".json"
        style={{ display: 'none' }}
      />
    </section>
  );
};
export default LongTermMemoryApp;
