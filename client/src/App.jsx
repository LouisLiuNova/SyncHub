import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import { Copy, FileText, Upload, Download, LogOut, Bell, Layers } from 'lucide-react';
import { format } from 'date-fns';

// 配置
const API_URL = 'http://localhost:3000'; // 生产环境需修改为相对路径或环境变量
const socket = io(API_URL);

// 工具函数：格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(localStorage.getItem('user'));
  const [activeTab, setActiveTab] = useState('clips'); // 'clips' or 'files'
  const [clips, setClips] = useState([]);
  const [files, setFiles] = useState([]);
  const [notification, setNotification] = useState(null);
  
  // 登录状态
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');

  // 输入状态
  const [clipText, setClipText] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (token) {
      fetchData();
      setupSocket();
    }
  }, [token]);

  const setupSocket = () => {
    socket.on('new_clip', (clip) => {
      setClips(prev => [clip, ...prev]);
      showNotification(`新文本: ${clip.username}`);
    });
    socket.on('new_file', (file) => {
      setFiles(prev => [file, ...prev]);
      showNotification(`新文件: ${file.username}`);
    });
    return () => {
      socket.off('new_clip');
      socket.off('new_file');
    };
  };

  const showNotification = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  };

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [clipsRes, filesRes] = await Promise.all([
        axios.get(`${API_URL}/api/clips`, { headers }),
        axios.get(`${API_URL}/api/files`, { headers })
      ]);
      setClips(clipsRes.data);
      setFiles(filesRes.data);
    } catch (err) {
      if (err.response?.status === 401) logout();
    }
  };

  const login = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API_URL}/api/login`, { username: usernameInput, password: passwordInput });
      setToken(res.data.token);
      setUser(res.data.username);
      localStorage.setItem('token', res.data.token);
      localStorage.setItem('user', res.data.username);
    } catch (err) {
      alert('登录失败');
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.clear();
  };

  const submitClip = async () => {
    if (!clipText.trim()) return;
    await axios.post(`${API_URL}/api/clips`, { content: clipText, tag: 'Code' }, { headers: { Authorization: `Bearer ${token}` } });
    setClipText('');
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    await axios.post(`${API_URL}/api/files`, formData, { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' } });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showNotification('已复制到剪贴板');
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="bg-white p-8 rounded-xl shadow-lg w-96">
          <h1 className="text-2xl font-bold text-blue-600 mb-6 text-center">SyncHub Login</h1>
          <form onSubmit={login} className="space-y-4">
            <input className="w-full p-2 border rounded" placeholder="用户名" value={usernameInput} onChange={e => setUsernameInput(e.target.value)} />
            <input className="w-full p-2 border rounded" type="password" placeholder="密码" value={passwordInput} onChange={e => setPasswordInput(e.target.value)} />
            <button className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700">进入系统</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      {/* 导航栏 */}
      <nav className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-blue-600 font-bold text-xl">
            <Layers /> SyncHub
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-500">User: {user}</span>
            <button onClick={logout} className="text-slate-400 hover:text-red-500"><LogOut size={20} /></button>
          </div>
        </div>
      </nav>

      {/* 通知 */}
      {notification && (
        <div className="fixed top-20 right-4 bg-blue-600 text-white px-4 py-2 rounded shadow-lg flex items-center gap-2 animate-bounce">
          <Bell size={16} /> {notification}
        </div>
      )}

      {/* 主区域 */}
      <main className="max-w-5xl mx-auto p-4 mt-4">
        {/* 标签页切换 */}
        <div className="flex gap-4 mb-6 border-b border-slate-200">
          <button 
            onClick={() => setActiveTab('clips')}
            className={`pb-2 px-4 flex items-center gap-2 ${activeTab === 'clips' ? 'border-b-2 border-blue-600 text-blue-600 font-medium' : 'text-slate-500'}`}
          >
            <FileText size={18} /> 文本剪贴板
          </button>
          <button 
            onClick={() => setActiveTab('files')}
            className={`pb-2 px-4 flex items-center gap-2 ${activeTab === 'files' ? 'border-b-2 border-blue-600 text-blue-600 font-medium' : 'text-slate-500'}`}
          >
            <Upload size={18} /> 文件共享
          </button>
        </div>

        {/* 文本面板 */}
        {activeTab === 'clips' && (
          <div className="space-y-6">
            <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-100">
              <textarea 
                className="w-full p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
                rows="3"
                placeholder="在此粘贴或输入文本..."
                value={clipText}
                onChange={e => setClipText(e.target.value)}
              ></textarea>
              <div className="flex justify-end mt-2">
                <button onClick={submitClip} className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium">
                  发布文本
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {clips.map(clip => (
                <div key={clip.id} className="bg-white p-4 rounded-lg shadow-sm border border-slate-100 hover:border-blue-200 transition-colors group">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">{clip.tag}</span>
                      <span className="text-xs text-slate-400">{clip.username} • {format(new Date(clip.createdAt), 'MM-dd HH:mm')}</span>
                    </div>
                    <button onClick={() => copyToClipboard(clip.content)} className="text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Copy size={16} />
                    </button>
                  </div>
                  <pre className="text-sm text-slate-700 whitespace-pre-wrap font-mono bg-slate-50 p-2 rounded">{clip.content}</pre>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 文件面板 */}
        {activeTab === 'files' && (
          <div className="space-y-6">
            <div 
              className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:bg-slate-50 cursor-pointer transition-colors"
              onClick={() => fileInputRef.current.click()}
            >
              <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <Upload className="mx-auto text-blue-500 mb-2" size={32} />
              <p className="text-slate-600 font-medium">点击或拖拽文件上传</p>
              <p className="text-xs text-slate-400 mt-1">支持任意格式文件</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {files.map(file => (
                <div key={file.id} className="bg-white p-4 rounded-lg shadow-sm border border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="bg-blue-50 p-2 rounded text-blue-600">
                      <FileText size={20} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-700 truncate">{file.originalName}</p>
                      <p className="text-xs text-slate-400">{file.username} • {formatSize(file.size)} • {format(new Date(file.createdAt), 'MM-dd HH:mm')}</p>
                    </div>
                  </div>
                  <a 
                    href={`${API_URL}/uploads/${file.filename}`} 
                    download={file.originalName}
                    className="text-slate-400 hover:text-blue-600 p-2"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download size={18} />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
