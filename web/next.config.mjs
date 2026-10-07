/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Next.js 16 默认拦截跨源开发资源；放行本机与局域网访问用到的 origin，
  // 否则用 127.0.0.1 / 局域网 IP 打开时前端 JS 无法水合，按钮无响应。
  allowedDevOrigins: ["localhost", "127.0.0.1", "192.168.1.104"],
};

export default nextConfig;
