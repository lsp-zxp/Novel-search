import "./globals.css";

export const metadata = {
  title: "NovelOps AI",
  description: "小说业务异常调查 Agent",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
