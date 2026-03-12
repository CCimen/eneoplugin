import { Footer, Layout, Navbar } from 'nextra-theme-docs'
import { Head } from 'nextra/components'
import { getPageMap } from 'nextra/page-map'

import './globals.css'

export const metadata = {
  title: {
    default: 'Eneo Plugins',
    template: '%s | Eneo Plugins'
  },
  description: 'Claude Code plugins for the Eneo AI team. Guidelines, tools, and integrations to streamline development.',
}

const navbar = (
  <Navbar
    logo={<span className="font-bold text-lg">eneo<span className="font-normal text-gray-500">plugin</span></span>}
  />
)

const footer = (
  <Footer>
    <div className="flex flex-col items-center gap-2">
      <div>
        MIT {new Date().getFullYear()} © Eneo AI Team
      </div>
    </div>
  </Footer>
)

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <Head />
      <body>
        <Layout
          navbar={navbar}
          pageMap={await getPageMap()}
          docsRepositoryBase="https://github.com/CCimen/eneoplugin/tree/main/docs-site"
          footer={footer}
        >
          {children}
        </Layout>
      </body>
    </html>
  )
}
