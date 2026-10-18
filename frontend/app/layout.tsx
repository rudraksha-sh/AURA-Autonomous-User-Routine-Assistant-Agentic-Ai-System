import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import Script from "next/script";

export const metadata: Metadata = {
  title: {
    default: "AURA | Your routine workspace",
    template: "%s | AURA",
  },
  description: "Organize your goals and make progress one step at a time.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <head>
        <Script id="aura-theme-init" strategy="beforeInteractive">{`(function(){try{var t=localStorage.getItem("aura_theme")||"system";var d=t==="dark"||(t==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);document.documentElement.style.colorScheme=t==="system"?"light dark":t}catch(_){}})()`}</Script>
      </head>
      <body className="min-h-full flex flex-col">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
