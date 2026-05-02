// import type { Metadata } from "next";
// import { Header } from "@/components/layout/Header";
// import { DevmitraProvider } from "@/store/DevmitraContext";
// import { DevmitraWidget } from "@/components/devmitra/DevmitraWidget";
// import "./globals.css";

// export const metadata: Metadata = {
//   title: "AutoMerge — Autonomous Debugging Platform",
//   description:
//     "AI-powered autonomous debugging and code-fixing platform that detects broken builds, analyzes logs, proposes patches, and validates fixes.",
// };

// export default function RootLayout({
//   children,
// }: {
//   children: React.ReactNode;
// }) {
//   return (
//     <html lang="en" className="dark" suppressHydrationWarning>
//       <body className="min-h-screen antialiased flex flex-col" suppressHydrationWarning>
//         <DevmitraProvider>
//           <Header />
//           <main className="flex-1 overflow-hidden">{children}</main>
//           <DevmitraWidget />
//         </DevmitraProvider>
//       </body>
//     </html>
//   );
// }


import type { Metadata } from "next";
import "./globals.css";
import "@/styles/cyberpunk.css";

import { Header } from "@/components/layout/Header";
import { BootSequence } from "@/components/layout/BootSequence";
import { ExperienceShell } from "@/components/system/ExperienceShell/ExperienceShell";
import { DevmitraProvider } from "@/store/DevmitraContext";
import { DevmitraWidget } from "@/components/devmitra/DevmitraWidget";
import { AuthProvider } from "@/store/AuthContext";

export const metadata: Metadata = {
  title: "AutoMerge — Autonomous Debugging Platform",
  description:
    "AI-powered autonomous debugging and code-fixing platform that detects broken builds, analyzes logs, proposes patches, and validates fixes.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className="min-h-screen antialiased flex flex-col"
        suppressHydrationWarning
      >
        <AuthProvider>
          <DevmitraProvider>
            <ExperienceShell>
              <BootSequence />
              <Header />
              <main className="flex-1 overflow-hidden">{children}</main>
              <DevmitraWidget />
            </ExperienceShell>
          </DevmitraProvider>
        </AuthProvider>
      </body>
    </html>
  );
}