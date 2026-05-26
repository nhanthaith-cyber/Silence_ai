import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "CS Agent — Chăm Sóc Khách Hàng Đa Sàn",
  description: "Hệ thống AI Agent chăm sóc khách hàng tự động cho Shopee, TikTok, Facebook, Instagram",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1e2030',
              color: '#e2e8f0',
              border: '1px solid #2d3748',
              borderRadius: '12px',
            },
          }}
        />
        {children}
      </body>
    </html>
  );
}
