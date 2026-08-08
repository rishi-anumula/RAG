import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services/documentService';
import type { Document } from '../types';
import { 
  UploadCloud, 
  FileText, 
  Trash2, 
  Play, 
  AlertCircle, 
  Edit3, 
  RefreshCw,
  Search,
  Eye
} from 'lucide-react';

export const Documents: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  
  // Upload States
  const [dragActive, setDragActive] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<{ name: string; progress: number }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Modal / Interaction States
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [renameExt, setRenameExt] = useState('.pdf');
  const [renaming, setRenaming] = useState(false);

  // Task 7: Load documents using React Query with auto-polling for processing status
  const { data: documents = [], isLoading: loading, error: queryError, refetch } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: () => documentService.list(),
    refetchInterval: (query) => {
      const docs = query.state.data;
      const hasProcessing = Array.isArray(docs) && docs.some((d) => d.status === 'processing');
      return hasProcessing ? 3000 : false;
    },
  });

  const error = queryError ? (queryError as any).message || 'Failed to load documents' : null;

  // Task 7: React Query Upload Mutation with Cache Invalidation
  const uploadMutation = useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (p: number) => void }) =>
      documentService.upload(file, onProgress),
    onSuccess: () => {
      // Automatically refresh the document list by invalidating React Query cache
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (files: File[]) => {
    const validExts = ['.pdf', '.docx', '.doc', '.txt', '.md', '.csv', '.json', '.log'];
    const validFiles = files.filter(f => {
      const name = f.name.toLowerCase();
      return validExts.some(ext => name.endsWith(ext));
    });

    if (validFiles.length === 0) {
      alert('Supported document formats are PDF, DOCX, DOC, TXT, MD, and CSV.');
      return;
    }

    for (const file of validFiles) {
      if (file.size > 1024 * 1024 * 1024) {
        alert(`File ${file.name} is too large. Maximum size is 1GB.`);
        continue;
      }

      setUploadingFiles(prev => [...prev, { name: file.name, progress: 0 }]);

      try {
        await uploadMutation.mutateAsync({
          file,
          onProgress: (progress) => {
            setUploadingFiles(prev => 
              prev.map(item => item.name === file.name ? { ...item, progress } : item)
            );
          }
        });
        
        setUploadingFiles(prev => prev.filter(item => item.name !== file.name));
      } catch (err: any) {
        setUploadingFiles(prev => prev.filter(item => item.name !== file.name));
        const status = err?.response?.status;
        let detail = err?.response?.data?.detail || err?.message;
        if (status === 413 || (detail && detail.toLowerCase().includes('large'))) {
          detail = `File "${file.name}" exceeds the server payload size limit. Please upload a smaller file or compress it.`;
        } else if (!detail) {
          detail = `Failed to upload "${file.name}". Please verify your network connection and try again.`;
        }
        alert(detail);
      }
    }
  };

  const handleProcess = async (docId: string) => {
    try {
      await documentService.process(docId);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to start indexing.');
      refetch();
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document? All vector indices and segments will be permanently removed.')) {
      return;
    }
    try {
      await documentService.delete(docId);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    } catch (err) {
      alert('Failed to delete document.');
    }
  };

  const openRenameModal = (doc: Document) => {
    const docId = doc.id || doc.document_id || '';
    const docName = doc.name || doc.filename || '';
    const match = docName.match(/(\.[^.]+)$/);
    const ext = match ? match[1] : '.pdf';
    setRenameId(docId);
    setRenameExt(ext);
    setRenameValue(docName.replace(/(\.[^.]+)$/, ''));
  };

  const handleRenameSubmit = async () => {
    if (!renameId || !renameValue.trim()) return;
    setRenaming(true);
    try {
      const fullNewName = renameValue.trim().endsWith(renameExt)
        ? renameValue.trim()
        : `${renameValue.trim()}${renameExt}`;
      await documentService.rename(renameId, fullNewName);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setRenameId(null);
    } catch (err) {
      alert('Failed to rename document.');
    } finally {
      setRenaming(false);
    }
  };


  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  // Filter list by search query
  const filteredDocuments = (Array.isArray(documents) ? documents : []).filter(doc => {
    const name = doc.name || doc.filename || '';
    return name.toLowerCase().includes(searchQuery.toLowerCase());
  });

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Documents</h1>
          <p className="text-dark-400 text-sm mt-1">Upload and manage PDFs and Word documents in your search registry</p>
        </div>
        
        {/* Search bar */}
        <div className="relative w-full md:w-64">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-dark-500">
            <Search className="h-4 w-4" />
          </span>
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-dark-900 border border-dark-800 rounded-xl py-2 pl-9 pr-4 text-white placeholder-dark-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm"
          />
        </div>
      </div>

      {/* Grid: Upload Zone and Document List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Upload Panel (1 col) */}
        <div className="space-y-6">
          <div 
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              glass rounded-2xl p-8 border-2 border-dashed text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[250px]
              ${dragActive 
                ? 'border-brand-500 bg-brand-500/5' 
                : 'border-dark-800 hover:border-brand-500/35 hover:bg-dark-900/30'
              }
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.md,.csv,.json,.log"
              onChange={handleFileInputChange}
              className="hidden"
            />
            <div className="h-14 w-14 rounded-full bg-brand-500/10 flex items-center justify-center text-brand-400 mb-4">
              <UploadCloud className="h-7 w-7" />
            </div>
            <h4 className="text-sm font-semibold text-white">Drag & drop files here</h4>
            <p className="text-xs text-dark-500 mt-1 max-w-[200px]">Supports PDF, DOCX, DOC, TXT, MD, and CSV files up to 1GB each</p>
            <button className="mt-4 px-4 py-2 bg-dark-800 border border-dark-700 hover:bg-dark-750 text-dark-100 rounded-xl text-xs font-semibold transition-colors">
              Browse Files
            </button>
          </div>

          {/* Upload Progress Section */}
          {uploadingFiles.length > 0 && (
            <div className="glass rounded-2xl p-6 space-y-4">
              <h5 className="text-xs font-bold uppercase tracking-wider text-dark-400">Uploading</h5>
              <div className="space-y-3">
                {uploadingFiles.map((file, idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-medium text-dark-300">
                      <span className="truncate pr-4">{file.name}</span>
                      <span>{file.progress}%</span>
                    </div>
                    <div className="w-full bg-dark-900 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className="bg-brand-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Document Inventory (2 cols) */}
        <div className="lg:col-span-2 glass rounded-2xl p-6 min-h-[400px] flex flex-col">
          <div className="flex items-center justify-between border-b border-dark-800 pb-4 mb-4">
            <h3 className="text-lg font-bold text-white">Document Inventory</h3>
            <button 
              onClick={() => refetch()}
              className="p-2 hover:bg-dark-800 text-dark-400 hover:text-dark-100 rounded-xl transition-colors focus:outline-none"
              title="Refresh List"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center space-x-2 text-xs text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center space-y-3 py-12">
              <svg className="animate-spin h-8 w-8 text-brand-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-dark-400 text-xs">Loading document list...</span>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-dark-600 mb-3" />
              <p className="text-sm font-semibold text-dark-300">No documents found</p>
              <p className="text-xs text-dark-500 mt-1 max-w-sm">Upload your first PDF document using the uploader panel to start querying your data base.</p>
            </div>
          ) : (
            <div className="flex-1 overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-dark-800 text-xs font-semibold tracking-wider text-dark-500 uppercase">
                    <th className="pb-3 pl-2">Name</th>
                    <th className="pb-3 hidden md:table-cell">Size</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right pr-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-800/60">
                  {filteredDocuments.map((doc) => {
                    const docId = doc.id || doc.document_id || '';
                    const docName = doc.name || doc.filename || 'Untitled';
                    const uploadDate = doc.upload_time || doc.created_at;
                    return (
                      <tr key={docId} className="group hover:bg-dark-900/20 transition-colors">
                        {/* Name & Date */}
                        <td className="py-4 pl-2 pr-4">
                          <div className="flex items-center space-x-3">
                            <FileText className={`h-5 w-5 shrink-0 ${doc.status === 'processed' ? 'text-brand-400' : 'text-dark-500'}`} />
                            <div className="min-w-0">
                              <p className="text-sm font-semibold text-dark-200 truncate max-w-[200px] md:max-w-[280px]" title={docName}>
                                {docName}
                              </p>
                              <p className="text-[10px] text-dark-500 mt-0.5">
                                Uploaded {uploadDate ? new Date(uploadDate).toLocaleDateString() : 'recently'}
                              </p>
                            </div>
                          </div>
                        </td>

                        {/* Size */}
                        <td className="py-4 text-xs font-medium text-dark-400 hidden md:table-cell">
                          {formatBytes(doc.size)}
                        </td>

                        {/* Status */}
                        <td className="py-4">
                          <div className="flex items-center space-x-1.5">
                            <span className={`
                              px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider
                              ${doc.status === 'processed' ? 'bg-green-500/10 text-green-400 border border-green-500/10' : ''}
                              ${doc.status === 'processing' ? 'bg-brand-500/10 text-brand-400 border border-brand-500/10 animate-pulse' : ''}
                              ${doc.status === 'uploaded' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/10' : ''}
                              ${doc.status === 'failed' ? 'bg-red-500/10 text-red-400 border border-red-500/10' : ''}
                            `}>
                              {doc.status}
                            </span>
                            
                            {doc.status === 'failed' && doc.error_message && (
                              <span className="text-red-400 hover:text-red-300 cursor-help" title={doc.error_message}>
                                <AlertCircle className="h-4 w-4" />
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="py-4 text-right pr-2">
                          <div className="flex items-center justify-end space-x-1">
                            
                            {/* View Output Page */}
                            <Link
                              to={`/documents/${docId}/output`}
                              className="p-2 bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 rounded-lg transition-colors border border-brand-500/15 flex items-center space-x-1 text-xs font-semibold"
                              title="View Extracted Output Page"
                            >
                              <Eye className="h-3.5 w-3.5" />
                              <span className="hidden sm:inline">View Output</span>
                            </Link>

                            {/* Process trigger */}
                            {doc.status === 'uploaded' && (
                              <button
                                onClick={() => handleProcess(docId)}
                                className="p-2 hover:bg-amber-500/10 hover:text-amber-400 text-dark-400 rounded-lg transition-colors"
                                title="Process & Index PDF"
                              >
                                <Play className="h-4 w-4" />
                              </button>
                            )}

                            {/* Rename Document */}
                            <button
                              onClick={() => openRenameModal(doc)}
                              className="p-2 hover:bg-dark-800 hover:text-dark-100 text-dark-400 rounded-lg transition-colors"
                              title="Rename"
                            >
                              <Edit3 className="h-4 w-4" />
                            </button>

                            {/* Delete Document */}
                            <button
                              onClick={() => handleDelete(docId)}
                              className="p-2 hover:bg-red-500/10 hover:text-red-400 text-dark-400 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* Rename Modal */}
      {renameId && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass max-w-md w-full rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Rename Document</h3>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-dark-400">New filename</label>
              <div className="flex items-center bg-dark-900 border border-dark-800 rounded-xl pr-3 overflow-hidden">
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  className="w-full bg-transparent border-none py-2.5 px-4 text-white focus:outline-none text-sm"
                  autoFocus
                />
                <span className="text-dark-500 text-sm font-semibold select-none">{renameExt}</span>
              </div>
            </div>
            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setRenameId(null)}
                className="px-4 py-2 hover:bg-dark-800 text-dark-300 rounded-xl text-xs font-semibold border border-dark-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRenameSubmit}
                disabled={renaming || !renameValue.trim()}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors"
              >
                {renaming ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default Documents;
