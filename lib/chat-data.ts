export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  biblePassages?: BibleReference[]
  alphaThemes?: string[]
  feedback?: "up" | "down" | null
  saved?: boolean
}

export interface BibleReference {
  reference: string
  summary: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

export interface ChatSettings {
  gentleTone: boolean
  showBiblePassages: boolean
  detailedAnswers: boolean
}

export const TOPIC_CHIPS = [
  "Stock Analysis",
  "ETF Strategies",
  "Portfolio Diversification",
  "Market Trends",
  "Risk Management",
] as const

export const STARTER_PROMPTS = [
  "What are the best ETFs for long-term investing?",
  "Should I invest in Apple (AAPL) right now?",
  "How do I build a diversified investment portfolio?",
  "What's the difference between SPY and VOO ETFs?",
] as const

export const TOPIC_GUIDES = [
  {
    id: "etf-strategies",
    title: "ETF Investment Strategies",
    description:
      "Learn about Exchange-Traded Funds, how to choose the right ETFs, and strategies for building a diversified portfolio with low-cost index funds.",
    icon: "trending-up" as const,
  },
  {
    id: "stock-analysis",
    title: "Stock Analysis & Research",
    description:
      "Understand fundamental and technical analysis, how to evaluate companies, and make informed investment decisions based on financial data.",
    icon: "bar-chart" as const,
  },
  {
    id: "portfolio-diversification",
    title: "Portfolio Diversification",
    description:
      "Learn how to spread risk across different asset classes, sectors, and geographic regions to build a resilient investment portfolio.",
    icon: "pie-chart" as const,
  },
  {
    id: "risk-management",
    title: "Risk Management",
    description:
      "Understand different types of investment risk, how to assess your risk tolerance, and strategies to protect your capital while growing wealth.",
    icon: "shield" as const,
  },
  {
    id: "market-trends",
    title: "Market Trends & Analysis",
    description:
      "Stay informed about current market conditions, economic indicators, and how macroeconomic trends can impact your investment decisions.",
    icon: "line-chart" as const,
  },
] as const
