import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { PwaRegister } from "@/components/pwa-register";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://gemahutan.site"),
  title: {
    default: "GemaHutan",
    template: "%s | GemaHutan",
  },
  description: "Unggah rekaman lapangan, GemaHutan menandai suara satwa di dalamnya dengan AI.",
  openGraph: {
    title: "GemaHutan",
    description: "Unggah rekaman lapangan, GemaHutan menandai suara satwa di dalamnya dengan AI.",
    locale: "id_ID",
    type: "website",
    siteName: "GemaHutan",
    images: [
      {
        url: "/og-image.png",
        width: 1280,
        height: 640,
        alt: "GemaHutan: pantau satwa hutan dari suaranya.",
      },
    ],
  },
  applicationName: "GemaHutan",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    title: "GemaHutan",
    statusBarStyle: "black-translucent",
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  colorScheme: "light",
  themeColor: "#FFFFFF",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className={plusJakarta.variable}>
      <body className="flex min-h-screen flex-col">
        <Providers>
          {children}
        </Providers>
        <PwaRegister />
      </body>
    </html>
  );
}
