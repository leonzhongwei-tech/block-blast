# Vercel Edge 缓存预热配置说明

## 概述

本配置为 Block Blast 游戏实现了三层边缘缓存优化策略，确保巴西和东南亚玩家能够就近命中本地边缘节点，实现二次进入秒开。

## 架构说明

Vercel CDN 拥有 126 个 PoP（接入点）分布在 51 个国家，其中与目标区域相关的计算节点包括：

| 区域代码 | 位置 | 覆盖范围 |
|---------|------|---------|
| gru1 | São Paulo, Brazil | 巴西及南美洲 |
| sin1 | Singapore | 东南亚（新加坡、马来西亚、泰国、越南、菲律宾、印尼） |
| hkg1 | Hong Kong | 东南亚北部及华南地区 |

## 三层优化策略

### 第一层：CDN-Cache-Control 强缓存（vercel.json）

通过 `CDN-Cache-Control` 头独立控制 Vercel CDN 层的缓存行为，与浏览器 `Cache-Control` 分离。关键配置如下：

- **静态资源**（JS/CSS/字体/图片）：`s-maxage=31536000, stale-while-revalidate=31536000` — 边缘节点缓存一年，即使过期也继续使用旧版本同时后台更新
- **HTML 入口**：`s-maxage=3600, stale-while-revalidate=86400` — 边缘缓存 1 小时，过期后 24 小时内仍可使用旧版本
- **Service Worker**：`s-maxage=60, stale-while-revalidate=300` — 边缘缓存 1 分钟，确保更新能快速传播

`stale-while-revalidate` 是关键：即使缓存过期，边缘节点也会立即返回旧内容（0ms 延迟），同时在后台异步拉取新版本。

### 第二层：HTML 预加载提示（index.html）

在 HTML `<head>` 中添加了资源预加载链：

```html
<link rel="dns-prefetch" href="https://fonts.googleapis.com">
<link rel="dns-prefetch" href="https://fonts.gstatic.com">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" href="...Orbitron..." as="style" onload="this.onload=null;this.rel='stylesheet'">
```

这确保了浏览器在解析 HTML 的同时就开始建立到字体服务器的连接，节省 100-300ms 的 DNS 查询和 TLS 握手时间。

### 第三层：GitHub Actions 定时预热（edge-cache-warmup.yml）

每 6 小时自动从 GitHub Actions 服务器请求页面资源，确保 Vercel 各区域 PoP 的缓存不会因为长时间无访问而被清除。

工作流会请求以下资源：
1. 主页面 `/`
2. Service Worker `/sw.js`
3. PWA Manifest `/manifest.json`

## 手动触发预热

在 GitHub 仓库的 Actions 页面，选择 "Edge Cache Warmup" 工作流，点击 "Run workflow" 即可手动触发。

## 验证缓存命中

```bash
# 检查响应头中的缓存状态
curl -sI https://block-blast-one-ruddy.vercel.app/ | grep -i "x-vercel-cache\|age\|cache-control"

# x-vercel-cache: HIT 表示命中边缘缓存
# age: N 表示缓存已存在 N 秒
```

## 预期效果

| 场景 | 首次访问 | 二次访问 |
|------|---------|---------|
| 巴西用户 | ~200-400ms（CDN 回源） | ~10-30ms（边缘命中） |
| 东南亚用户 | ~150-300ms（CDN 回源） | ~10-30ms（边缘命中） |
| 预热后首次 | ~10-30ms（已预热） | ~10-30ms（边缘命中） |
