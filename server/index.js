const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { Sequelize, DataTypes } = require('sequelize');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');

// --- 配置 ---
const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });
const PORT = 3000;
const JWT_SECRET = 'synchub-secret-key-change-me';
const UPLOAD_DIR = path.join(__dirname, 'uploads');

if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR);

app.use(cors());
app.use(express.json());
app.use('/uploads', express.static(UPLOAD_DIR));

// --- 数据库连接 (PostgreSQL) ---
const sequelize = new Sequelize(process.env.DATABASE_URL || 'postgres://user:pass@db:5432/synchub', {
  dialect: 'postgres',
  logging: false,
});

// --- 模型定义 ---
const User = sequelize.define('User', {
  username: { type: DataTypes.STRING, unique: true, allowNull: false },
  password: { type: DataTypes.STRING, allowNull: false }
});

const Clip = sequelize.define('Clip', {
  content: { type: DataTypes.TEXT, allowNull: false },
  tag: { type: DataTypes.STRING, defaultValue: 'General' },
  username: { type: DataTypes.STRING }
});

const FileRecord = sequelize.define('FileRecord', {
  filename: { type: DataTypes.STRING, allowNull: false },
  originalName: { type: DataTypes.STRING, allowNull: false },
  size: { type: DataTypes.INTEGER },
  username: { type: DataTypes.STRING }
});

// --- 中间件 ---
const authenticate = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Unauthorized' });
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (e) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOAD_DIR),
  filename: (req, file, cb) => cb(null, Date.now() + '-' + file.originalname)
});
const upload = multer({ storage });

// --- API 路由 ---

// 1. Auth
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  let user = await User.findOne({ where: { username } });
  
  // 简单起见，如果用户不存在则自动注册
  if (!user) {
    const hashedPassword = await bcrypt.hash(password, 10);
    user = await User.create({ username, password: hashedPassword });
  } else {
    const valid = await bcrypt.compare(password, user.password);
    if (!valid) return res.status(401).json({ error: 'Invalid credentials' });
  }
  
  const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET);
  res.json({ token, username: user.username });
});

// 2. Clips
app.get('/api/clips', authenticate, async (req, res) => {
  const clips = await Clip.findAll({ order: [['createdAt', 'DESC']], limit: 50 });
  res.json(clips);
});

app.post('/api/clips', authenticate, async (req, res) => {
  const { content, tag } = req.body;
  const clip = await Clip.create({ content, tag, username: req.user.username });
  io.emit('new_clip', clip); // 实时通知
  res.json(clip);
});

// 3. Files
app.get('/api/files', authenticate, async (req, res) => {
  const files = await FileRecord.findAll({ order: [['createdAt', 'DESC']], limit: 50 });
  res.json(files);
});

app.post('/api/files', authenticate, upload.single('file'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file' });
  const fileRecord = await FileRecord.create({
    filename: req.file.filename,
    originalName: req.file.originalname,
    size: req.file.size,
    username: req.user.username
  });
  io.emit('new_file', fileRecord); // 实时通知
  res.json(fileRecord);
});

// --- 启动 ---
sequelize.sync().then(() => {
  server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
});
