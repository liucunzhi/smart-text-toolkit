# Smart Text Toolkit API - 部署与变现指南

## 项目概述
FastAPI构建的文本处理API服务，包含10个端点：
- `POST /api/md2html` - Markdown转HTML
- `POST /api/format-json` - JSON格式化与验证
- `POST /api/code-highlight` - 代码语法高亮(Python/JS/HTML/Java/SQL)
- `POST /api/qrcode` - 二维码生成(文本/URL→Base64 PNG)
- `POST /api/csv2json` - CSV转JSON数组
- `POST /api/img2base64` - 图片上传转Base64 Data URI
- `POST /api/text-diff` - 文本差异对比(unified diff)
- `POST /api/url-shorten` - URL短链接生成
- `GET /api/health` - 健康检查
- `GET /api/languages` - 支持的语言列表

## 快速开始
```bash
cd api
pip install -r requirements.txt
python main.py
# 访问 http://127.0.0.1:8000/docs 查看Swagger文档
```

## 部署方案

### 方案1: Render (推荐，免费)
1. 将代码推送到GitHub仓库
2. 登录 render.com → New Web Service → 连接GitHub
3. Build Command: `pip install -r
...[Truncated]...
3. **基础版**: $9.99/月 (10,000次调用)
4. **专业版**: $29.99/月 (50,000次调用)

## 收入预测
- 免费用户: 吸引开发者试用
- 付费用户100人: $999/月 (Hobby)
- 付费用户30人: $899/月 (Professional)
- 月收入可达 $500-$2,000 (保守估计)

## 营销策略
1. 在RapidAPI Marketplace获取自然流量
2. 在Dev.to/Hashnode写技术文章引流
3. 在Product Hunt发布
4. 在Reddit r/programming分享
5. 提供免费API Key给技术博主评测

## 第二步：扩展数字产品线增加收入
- Excel自动化工具箱 (已完成 ✅)
- PDF处理工具包
- 网页数据抓取器
- 批量文件重命名工具
